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

---

# Opus Review — S18

Scope: closed T086–T090 (5 tickets) addressing the entire S17 review-concern set + workflow-review opens T089–T090. Net: ~280 LoC across 4 production files + 4 new/expanded test files (1 new integration test file, 1 new tool `create_ticket.py`). All three S17 priority concerns (#1 workspace bypass, #2 `git -C` parsing, #3 warn-unstaged false-positive) addressed; integration test added (S17 Test Gap #4). Clean follow-through. Three new concerns surface, none invariant-violating.

## Invariant Violations

None. T086 *restores* Invariant 5 alignment at the hook layer that S17 flagged as weakened: `_staged_code_files` now accepts `git_cwd` and routes `git -C <root> diff --cached` to the workspace's actual repo. Invariant 4 unchanged.

## Architectural Concerns

1. **`scripts/hooks/check_fix_commit_has_code.py:74-79` — `--work-tree` and `--git-dir` are recognised as two-token flags but their values are discarded; `--flag=value` form is not handled at all.** [Concrete bug, low impact] The walk loop captures `git_cwd` only for `-C`; for `--work-tree` and `--git-dir` it advances `i += 2` (consuming the value) but never assigns. Worse, `git --git-dir=/path commit` arrives as a single token starting with `-`, which falls into the generic `if tok.startswith("-"): i += 1` branch and is silently skipped — so `git_cwd` stays `None`, the hook queries the harness repo, and the workspace bypass S17 Concern #1 partially re-emerges for `--git-dir=` and `--work-tree=` invocations. close_ticket.py uses space-separated `-C` today so this is latent, but any future automation using `=` form (or `--git-dir`) defeats the fix. Fix: either drop `--git-dir`/`--work-tree` from the recognized list (they're not used) or actually capture them and handle the `=` form via `tok.startswith("--git-dir=")`/`tok.startswith("-C=")` checks.

2. **`scripts/tools/create_ticket.py:38, 175 — `_TEMPLATE` hardcodes `layer: tooling`, but the documented enum is `backend | frontend | fullstack | infra | process`.** [Schema violation] `architecture_invariants.md` (ticket template in opus context line 968) lists `layer:` values explicitly; `tooling` is not among them. The new script emits malformed frontmatter that other tooling (`generate_ticket_index.py`, classifier) may or may not parse. Inspection of recent in-flight tickets in the diff shows the value `layer: tooling` is in fact what other scripts emit (T086–T090 archive files all show `tooling`), so the doc is stale relative to actual usage rather than the script being wrong — but the divergence is real, and Opus's own review template comes from the doc. Pick one: update the invariants-doc enum to include `tooling`, or change the template to a valid value. Either way, `--layer` should probably be a CLI arg with validation.

3. **`scripts/tools/create_ticket.py:144-193` — no `repo:` frontmatter emitted for workspace tickets.** [Schema gap, low impact] The template explicitly calls for `repo: <name from workspace.yaml repos list>` when a workspace ticket spans a specific repo. `create_ticket.py --workspace <slug>` writes a workspace-located ticket but omits `repo:` entirely (commented-out line in `_TEMPLATE`). Workspace tickets that legitimately span multiple repos are fine to omit, but the script gives no `--repo` flag to set it when relevant. Add `--repo SLUG` and emit `repo: <slug>` in the frontmatter when provided; otherwise leave commented as today.

4. **`scripts/tools/create_ticket.py:104-128` — concurrent `create_ticket.py` invocations race on `_next_id`.** [Concrete bug, low likelihood] Two parallel calls scan the same directories, both compute `T091`, both attempt `dest.write_text`. The second wins (clobber, since `dest.exists()` check happens before write but Python's `open(... "w")` will overwrite without `x` mode). Diff suggests `_TEMPLATE` write at line 184 uses `write_text` not `open("x")` — verify by reading the file if it matters. The CLAUDE.md ban on `Agent` worktrees with shared paths makes this mostly theoretical, but the script is documented as workspace-aware and a `/loop` or background-agent could trigger it. Fix: open with `O_CREAT|O_EXCL` (Python: `open(dest, "x")`); on collision, increment and retry up to N times.

5. **`scripts/tools/close_ticket.py:303-321` — `_warn_unstaged_code` no longer compares against `--files`; warning fires even when the user passed `--files` *and* a separate file was modified.** [False positive, moderate noise] The fix solves S17 Concern #3 (already-staged false positive: `git diff --name-only` skips staged paths). But the docstring still says "if there are unstaged or untracked code files **not passed via --files**" while the implementation never receives the `--files` list. If `--files myfix.py` is passed and the user has also edited `unrelated.py` (unstaged), the warning fires and recommends re-running with `--files`. That's not strictly wrong, but it conflates "you forgot to stage code" with "you have unrelated dirty code". Either (a) accept the `extra_files` list and subtract those paths from the warn set, or (b) update the docstring/message to "WARNING: unstaged code in repo (not necessarily related)".

6. **`scripts/tools/analyze_tool_log.py:88-93` — `_retry_sequences` now skips any record where `cur_path` is empty, which silently drops a class of retries.** [Telemetry gap, low impact] The new `if not prev_tool or not cur_tool or not cur_path: continue` filter requires the *current* record to have a non-empty `path`. For tools where the log writer may emit an empty `path` (e.g., a Bash call whose payload didn't include the command, a TaskCreate, a hook-internal record), retries become invisible. The S17 retry-noise problem this addresses came from Bash-vs-Bash false positives — fine — but the cure is broader than the disease. Safer filter: also require `prev_path` to be non-empty for the same comparison (already implicit through equality), and document that the section now reports only path-bearing retries. Test coverage in the diff is one negative test; positive cases for Bash same-command retries aren't shown in the visible diff.

7. **`tests/test_check_fix_commit_has_code.py:test_workspace_archive_at_any_depth_excluded` — does not actually test "any depth"; it stages only the archive file, so the test passes for *both* "filename regex" and "directory prefix" implementations.** [Test gap, low confidence] The test name implies coverage of the directory-name change (from `docs/archive/` prefix to filename regex). To prove the regex behavior, the test should also stage a code file (e.g. `scripts/foo.py`) alongside the archive ticket and assert the commit is allowed — verifying that the archive file is excluded *and* the code file is counted. As written, the test only proves "archive-only commit blocks", which the old implementation also did for `docs/archive/`.

## Architectural Concerns — Test Gaps

1. **`_parse_fix_commit` is untested for `--git-dir=<path>` and `--work-tree=<path>` (`=` form).** Concern #1 above is uncovered.

2. **`create_ticket.py` is untested for concurrent invocations.** Concern #4. A pytest with two `subprocess.Popen` + barrier would catch the clobber.

3. **`_warn_unstaged_code` is untested for the `--files passed AND unrelated dirty file` case.** Concern #5. Add: stage via `--files foo.py`, modify `unrelated.py` unstaged, run close_ticket, assert warning fires (current behavior) or does NOT fire (desired behavior, depending on the fix chosen).

## Suggested Next Session Focus

1. **Tighten `_parse_fix_commit` flag handling (Concern #1) + add the `--git-dir=` test (Test Gap #1).** ~10 LoC + 2 tests. The S17 fix is good but incomplete; `=` form is the realistic future bypass.

2. **Resolve the `layer:` enum mismatch (Concern #2).** Either update `docs/architecture_invariants.md` to include `tooling` or change emitted layer values across `create_ticket.py` and any other emitters. ~2 LoC + doc edit.

3. **Race-protect `create_ticket.py:_next_id` via `O_CREAT|O_EXCL` (Concern #4).** ~5 LoC. Cheap, eliminates a footgun before `/loop` or background agents grow.

## Carry-forwards (issues unresolved ≥ 2 sessions)

None. All S17 priority concerns addressed in T086–T088. The remaining items are S18-original.
