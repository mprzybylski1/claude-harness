# Opus Review — S16

Scope: closed T073 (log_tool_usage triad: flock, >=, expanduser) from prior carry-forwards. Single committed diff (a5a1ab9) plus uncommitted docs/sessions/INDEX updates reflecting T074–T077 closures and T078–T082 opens from scrabble-score handoff and workflow-review. The actual code change is small (~30 LoC in `scripts/hooks/log_tool_usage.py` + 50 LoC of tests). Cleared all three S15 carry-forwards in one ticket — good discipline. New concerns are mostly minor, but one fail-closed gap deserves attention.

## Invariant Violations

None. `fcntl.flock(LOCK_EX)` on `_ERR_STATE_PATH` strengthens Invariant 4 (fail-closed) for the rate-limit accounting: concurrent processes can no longer lose-update the counter. `.expanduser()` at the workspace-match site strengthens Invariant 5 (workspace isolation) — Bash `~/...` tokens now correctly resolve to declared workspace paths instead of being silently stamped as harness-root.

## Architectural Concerns

1. **`scripts/hooks/log_tool_usage.py:208-209` — outer `except Exception: pass` swallows flock/IO failures and lets the function fall through to write the error without rate limiting.** [Fail-closed concern] If `open(_ERR_STATE_PATH, "a+")` raises (disk full, permission denied) or `flock` fails (lock table exhausted), the bare `except` discards the error and execution continues to lines 210-213, which open `_ERR_PATH` directly and write — bypassing the entire counter. Under a sustained bootstrap-path failure this can flood the error log. T081 ("bootstrap-path errors bypass rate-limit") appears to track exactly this; verify T081's acceptance criteria cover the `_log_error`-internal failure modes, not just bootstrap.

2. **`scripts/hooks/log_tool_usage.py:189` — `open(path, "a+")` on Linux opens for append; `fd.seek(0); fd.read()` works, but `fd.seek(0); fd.truncate(); fd.write(...)` interacts with append-mode semantics.** [Concrete bug, low likelihood] In append mode (`a+`), writes are forced to EOF regardless of seek position on POSIX. The seek(0)+truncate(0) sequence will truncate to zero, then write at position 0 (because EOF is now 0). This *happens* to produce the right result, but it's fragile — if the JSON ever grows mid-write, append semantics could surprise. Use `r+` (with create-if-missing wrapper) or write to a tmp file + `os.replace` while still holding the flock.

3. **`tests/test_telemetry.py:test_rate_limit_window_resets_at_exact_boundary` — `mock.patch("log_tool_usage.time")` replaces the entire module, but `time.strftime`/`time.gmtime` side_effects pass through.** [Test fragility] If a future change to `_log_error` adds a `time.monotonic()` or `time.perf_counter()` call, the mock will return a `MagicMock` object that doesn't satisfy arithmetic operators, producing a confusing test failure. Patch only `time.time` via `mock.patch.object(ltu.time, "time", return_value=boundary)`.

4. **`tests/test_telemetry.py:test_rate_limit_cross_process_concurrent` — 30 processes started sequentially via `Popen` in a list comprehension is "more concurrent than `subprocess.run`" but not truly simultaneous.** [Test gap, partial] Process creation can take 10-50ms each on Linux; by the time process 30 starts, process 1 may have finished. A `ProcessPoolExecutor.map` with a `multiprocessing.Barrier` would force all 30 into the critical section at the same instant. Current test would still pass without flock if processes serialize naturally on a slow runner.

5. **`scripts/tools/close_ticket.py` — workspace INDEX vs harness INDEX dual-write path (T075 fix) untouched by static analysis.** [Verification gap] The S16 diff only contains the T073 code change; T075's `_regenerate_index()` `--tickets-dir` + `--output` flag plumbing is in the uncommitted area per sessions.md but not in the committed diff Opus sees. If T075 was committed as part of a separate flow before the review snapshot, fine — but verify the commit landed on the branch under review. The static analysis cannot confirm what isn't in the diff.

## Suggested Next Session Focus

1. **Verify T081's acceptance criteria explicitly cover `_log_error`-internal IO/flock failures (Concern #1).** The most likely flood scenario is `_log_error` itself failing, not the bootstrap path. If T081 only addresses module-import errors, file a follow-up or expand T081 before closing.

2. **Switch `_log_error` to `r+` mode (or `os.open` with O_RDWR|O_CREAT) to avoid append-mode write surprises (Concern #2).** ~5 LoC. Eliminates the latent fragility before it bites a future contributor.

3. **Strengthen the concurrent test with `multiprocessing.Barrier` (Concern #4).** Ensures the test actually proves what its name claims. ~10 LoC.

## Carry-forwards (issues unresolved ≥ 2 sessions)

- S15 carry-forwards (`flock`, `>=`, `.expanduser()`): RESOLVED in T073. Clean close.
- S13 / S14 / S15 Test Gap: `_log_error` count==11 marker test — STILL MISSING. New tests cover boundary reset and cross-process concurrency but the marker-line assertion at count==11 (single emission, exact text) remains untested. 3 sessions.

---

# Opus Review — S17

Scope: closed T078–T085 (8 tickets) clearing the S16 workflow-review backlog. Net changes: new PreToolUse hook `check_fix_commit_has_code.py` (~128 LoC + 10 tests), `close_ticket.py` grew `--files`/`--path-only` flags, staged-files summary, `_git_root_for` tuple return; `log_tool_usage.py:_log_error` bootstrap guard + `state_ok` sentinel; SKILL/CLAUDE.md doc updates. ~1234 insertions / 81 deletions across 20 files. Backlog at 0 open tickets, but the new commit-hook and the `_warn_unstaged_code` helper introduce real false-positive / false-negative paths.

## Invariant Violations

None directly. Invariant 4 (fail-closed) is *strengthened* in `_log_error`: the new `state_ok` sentinel prevents the prior bypass where a state-file I/O failure fell through to write `_ERR_PATH` unbounded — a fail-closed gap S16 #1 explicitly flagged. The bootstrap guard at `_ERR_STATE_PATH.parent.exists()` correctly returns early with one stderr emit. Both fixes are right-shaped.

Invariant 5 (workspace isolation) is *weakened* — but only at the hook layer, not at the data-read layer. See Concern #1: the new fix-commit hook does not detect a workspace's actual git repo, so its policy is enforced inconsistently between harness-root and workspace commits.

## Architectural Concerns

1. **`scripts/hooks/check_fix_commit_has_code.py:70-90` — `_staged_code_files` runs `git diff --cached` in the hook's cwd, which means workspace `fix(TXXX):` commits get inconsistent enforcement.** [Concrete bug, REGRESSION risk] The hook is documented to block `fix(TXXX):` commits with no code staged; it runs `git diff --cached --name-only` with no `-C` argument, so cwd determines which repo is queried. For a workspace ticket close where the user (or a future automation) runs `git -C /external/project commit -m "fix(T999): ..."`, the hook fires in Claude's cwd (harness root), queries the harness repo's index, finds nothing staged there, and BLOCKS the commit — even when the external project repo has code staged correctly. Conversely, the *archive-only* exclusion list (`docs/archive/`, `docs/tickets/`) covers harness paths but NOT workspace archive layouts (`workspaces/<slug>/internal/archive/` or external `<proj>/.harness/archive/`), so a workspace fix-commit with only the archive move staged is silently ALLOWED. Two opposite failure modes from the same root cause: the hook is not workspace-aware. Fix: derive git root from the commit command (parse `-C <path>` if present, else use cwd), pass it to `git -C <root> diff --cached`, and broaden the exclusion to any `*/archive/T*.md` and `*/tickets/T*.md` path.

2. **`scripts/hooks/check_fix_commit_has_code.py:42-47` — `git -C <path> commit` is silently ignored.** [Concrete bug, low impact, related to #1] `_parse_fix_commit` requires `tokens[git_idx + 1] == "commit"`. For `git -C /path commit -m "fix(T001): x"`, the token after "git" is "-C", so the function returns None and the hook bypasses. The bash-wrapped form `bash -c 'git commit -m "fix(T001): x"'` also bypasses (no token equals "git" at top level because shlex unwraps the outer `bash -c`'s arg into one token). Neither is exotic — close_ticket.py itself uses `git -C <root>` for staging, and any agent-issued composite command could land in the bash-c form. Fix: scan all tokens for the first one equal to `git`, then walk forward past any options (`-C`, `--git-dir`, `--work-tree`) until "commit".

3. **`scripts/tools/close_ticket.py:340-353` — `_warn_unstaged_code` produces false positives.** [Concrete bug, moderate noise] The helper runs `git diff HEAD --name-only`, which lists everything different from HEAD — **staged + unstaged combined**, per git semantics. After `_git_stage` has just staged the archive move and INDEX.md, those would be in the diff but get filtered by `endswith(".md")`. The hole is any pre-existing `.py` file already `git add`-ed before close_ticket runs (e.g. from earlier in the same session, or from another active branch): it appears in `git diff HEAD --name-only`, fails the `.md` filter, and triggers the WARNING "no code files staged — pass --files explicitly" — *even though the user already staged them*. The test suite covers only the truly-unstaged-modified case (`test_no_files_warns_when_unstaged_code_exists`) and the no-change case; the false-positive-on-already-staged case is uncovered. Fix: use `git diff --name-only` (working tree vs index, unstaged only) AND `git diff --cached --name-only` (index vs HEAD, staged only) separately; warn only when there are unstaged code changes that look like they belong with the ticket.

4. **`scripts/tools/close_ticket.py:441-447` — staged-files summary omits the deleted source ticket.** [Display lie, low impact] `staged_paths = [dest, index_path] + (extra_files or [])` — but `_git_stage` also stages the *deletion* of `ticket_path` from `open/`. The user sees "staged: docs/archive/T999-x.md, docs/tickets/INDEX.md" but not "staged: docs/tickets/open/T999-x.md (deleted)". For someone reviewing what's about to be committed, this is misleading. Fix: add `ticket_path` to `staged_paths` with a "(deleted)" annotation, or list all three paths consistently.

5. **`scripts/hooks/check_fix_commit_has_code.py:70-81` — `_staged_code_files` swallows non-zero git exit silently → wrong error message.** [Fail-closed concern, minor] When `git diff --cached` exits non-zero (not in a repo, corrupted index), the function returns `[]`. The caller then BLOCKS with "no code files staged" — but the real problem is git itself. User sees a misleading message and a `--files` suggestion that won't help. Fix: distinguish "git unavailable" from "git ran, returned no code files"; for the former, exit 0 (the regular pre-commit will surface the real error) or print a different stderr.

6. **`scripts/hooks/check_fix_commit_has_code.py:31-36` — `_code_paths` silently falls back to defaults when `harness_config` import fails.** [Fail-closed concern, minor] Any exception (broken yaml, missing dependency, harness_config refactor) reverts to `("scripts/", "src/", "lib/", "tests/")` without logging. A workspace whose `code_paths` includes e.g. `app/`, `MyApp/` would be misclassified — `app/foo.swift` is NOT in defaults, so a fix-commit with only Swift code staged would be BLOCKED. Either log the fallback to stderr (one-shot) or just exit 0 when config is unreadable (the existing close_ticket.py already protects via `--files`).

7. **`scripts/hooks/log_tool_usage.py:189` — bootstrap-guard `_BOOTSTRAP_STDERR_LOGGED` is per-process, not per-invocation.** [Minor / by-design] Once set in a long-lived process (which Claude Code hooks are NOT — each hook call is a fresh subprocess), further bootstrap errors are silent. This is correct for hooks (each spawn re-imports the module), but the test `test_state_io_failure_does_not_bypass_rate_limit` explicitly resets it (`ltu._BOOTSTRAP_STDERR_LOGGED = False`) — which is a tell that the in-process semantics are subtle. Not a bug; flag as something to document in the docstring so future test authors don't blame stale module state.

## Architectural Concerns — Test Gaps

1. **`check_fix_commit_has_code.py` is untested for `git -C <path> commit` and `bash -c '…'` forms.** Both bypass the hook today (Concern #2). The current 10 tests all use the bare `git commit` form.

2. **`check_fix_commit_has_code.py` is untested for the workspace-cwd scenario.** No test runs the hook from a harness cwd while the staged changes are in an external project repo (the case that S15 T072 fixed for `_git_stage`, but the new hook re-introduces).

3. **`_warn_unstaged_code` false-positive-on-already-staged case (Concern #3) is untested.** Add a test: stage `foo.py` BEFORE running close_ticket, then assert the warning is NOT emitted.

4. **No e2e test verifies the new hook plays well with `close_ticket.py`'s recommended workflow.** `close_ticket.py` prints `git commit -m "fix(T999): ..."` as the suggested next command, but no test runs that exact command through the hook + verifies it succeeds when `--files` was used at close time. A 20-line integration test would catch Concerns #1 and #5 simultaneously.

5. **Carry-forward S16 Test Gap #3: `count==11` marker line still untested.** Now 4 sessions unaddressed. New `test_rate_limit_caps_at_ten_plus_marker` exists and asserts `"rate-limit" in lines[-1]` — that IS the marker test. **RESOLVED implicitly** by S17 (good). Withdraw this carry-forward.

## Suggested Next Session Focus

1. **Fix the workspace bypass/false-block in `check_fix_commit_has_code.py` (Concerns #1, #2).** Highest priority — the hook's value proposition is enforcing the "fix(TXXX) commits must have code" rule, but workspace commits today either bypass it entirely (wrong archive prefix) or get blocked when correct (wrong git repo queried). Parse `-C <path>` from the commit command, run `git -C <root> diff --cached`, broaden the archive-exclusion to any `*/archive/*` and `*/tickets/*` path. Add 2 tests for the two failure modes. ~30 LoC + 2 tests.

2. **Fix the `_warn_unstaged_code` false-positive (Concern #3).** Replace `git diff HEAD --name-only` with separate `git diff` (unstaged) and `git diff --cached` (staged) queries; warn only on unstaged code. ~10 LoC + 1 test. Without this fix, the warning becomes background noise users learn to ignore — defeating its purpose.

3. **Add the missing integration test (Test Gap #4).** Drive `close_ticket.py --files foo.py` end-to-end, then run the recommended `git commit` through the hook, assert success. Catches regressions across the close-ticket + commit-hook seam. ~25 LoC.

## Carry-forwards (issues unresolved ≥ 2 sessions)

- None. The S16 carry-forward (count==11 marker test) is resolved by the new `test_rate_limit_caps_at_ten_plus_marker` test in S17. Clean slate going into S18.
