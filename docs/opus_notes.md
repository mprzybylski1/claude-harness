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

# Opus Review — S19

Scope: closed T091–T102 (12 tickets) addressing all 6 S18 architectural concerns + 5 S19 workflow-review opens. Net: substantial work in `close_ticket.py` (`_check_gitignored`, `_stage_extra_files` extracted, scoped `_check_acs`/`_tick_acs`, `--tick-acs` flag mutually exclusive with `--force`), new `check_test_imports` in `repo_hygiene.py`, `create_ticket.py` gained `--layer`/`--repo`/`O_EXCL` retry. 16 close-ticket tests + 3 repo_hygiene tests + 5 create_ticket tests. Strong follow-through on every S18 priority. Three small concerns surface; none invariant-violating.

## Invariant Violations

None confirmed. The harness-level invariants 1–2 are placeholders ("[Name]") and invariant 3 is conditional. Invariant 4 (fail-closed) is *strengthened* by T098: `_check_gitignored` exits 2 on subprocess failure and on git returncode >= 128, rather than treating unknown rc as "not ignored". Invariant 5 (workspace isolation) is unaffected — `_check_gitignored` correctly groups paths by their actual git root via `_git_root_for(p)` so checks run against the correct repo.

The S18 carry-forward "`layer: tooling` schema mismatch" is addressed at the create-ticket-script layer (T092 adds `--layer` enum including `tooling`) but the `docs/architecture_invariants.md` placeholder enum was NOT updated to include `tooling` (still says `backend | frontend | fullstack | infra | process` per the template embedded in opus_review_context.md). The session-close notes acknowledge this as "1 deferred (architecture_invariants.md placeholder stubs)". Not an invariant violation because the doc enum is the placeholder, but the schema-of-record drift remains and should be reconciled.

## Architectural Concerns

1. **`scripts/tools/close_ticket.py:284-294` — `_tick_acs` silently no-ops when `## Acceptance Criteria` header is missing, while `_check_acs` falls back to whole-content scan. Asymmetric.** [Concrete bug, low impact] If a ticket lacks the literal header (e.g. typo "Acceptance criteria" lowercase, or missing entirely), `_check_acs` walks the whole file and finds unchecked boxes everywhere, but `_tick_acs` returns content unchanged. Result with `--tick-acs`: the gate still fires (unchecked ACs found via fallback) and close fails with a confusing message — user passed `--tick-acs` expecting it to tick boxes, sees the gate fail anyway. Fix: either (a) make `_tick_acs` symmetric (rewrite all `- [ ]` in the whole file when header missing), or (b) print a clearer error like "`--tick-acs` requires a `## Acceptance Criteria` section". The test `test_tick_acs_scoped_to_ac_section_only` only exercises the happy path where the header exists.

2. **`scripts/tools/repo_hygiene.py:185-244` — `check_test_imports` reports "missing pytest" as a `test-import-error` WARN via the generic fallback, contradicting the docstring "Best-effort: if pytest is unavailable...returns []".** [Concrete bug, moderate noise] The exception handler at line 199 only catches `FileNotFoundError, subprocess.TimeoutExpired, OSError`. When pytest is not installed but Python is, `python -m pytest` exits with returncode 1 and stderr `No module named pytest`. That falls through to the parsing logic; the "ModuleNotFoundError"-grep branch (line 219) matches and emits a WARN naming pytest itself, not a user test file. The AC was explicit: "Check is best-effort: missing pytest does not fail the script" — it doesn't fail, but it lies. Fix: pre-check `importlib.util.find_spec("pytest")` and return `[]` if missing. The test `test_missing_pytest_does_not_crash` mocks `subprocess.run` with `FileNotFoundError`, which does not exercise the real "pytest not installed but Python is" path — so this gap is uncovered.

3. **`scripts/tools/repo_hygiene.py:230-242` — generic fallback WARN truncates `combined` to 200 chars without indicating truncation, hiding the actual error.** [Display bug, low impact] When pytest exits non-zero but neither "ERROR collecting" nor "ImportError" patterns match, the fallback emits `f"pytest --collect-only failed (exit {result.returncode}): {snippet}"` where snippet is silently sliced. A long traceback gets chopped mid-line. Fix: append `...` when truncated, or write the full output to a temp file and reference it.

4. **`scripts/tools/close_ticket.py:259-264` — `_check_gitignored` silently skips paths whose `_git_root_for` returns None.** [Coverage gap, low impact] The comment says "Path is not inside any git repo — cannot check; proceed (staging will catch it)". That's true today because `_stage_extra_files` runs next and exits 2 for the same path, so the user sees an error. But the two checks are coupled by control flow only — if a future refactor reorders or wraps `_stage_extra_files` in a try/except, the gitignore check would silently no-op. Defense-in-depth: also exit 2 here with a clear "path not in any git repo" message rather than relying on the next stage.

5. **`scripts/tools/repo_hygiene.py:335-339` — manual `sys.argv` walk for `--tests-dir` does not coexist with `--warn-only` if a user combines them as `--warn-only --tests-dir foo`.** [Diff suggests; low confidence — minor] The arg detection works for either flag in any position but neither uses argparse, so `--tests-dir=foo` (=-form) would not parse. Trivial today, but if more flags accrue this pattern will collapse. Convert to `argparse.ArgumentParser` next time anything is added.

6. **`scripts/tools/close_ticket.py:316-325` — `_stage_extra_files` failure message advises `git reset HEAD` but only if there were multiple roots; the message is unconditional.** [Display lie, low impact] "Some paths from earlier repos may already be staged" appears even when there's only one git root and no partial state can exist. Fix: check `len(by_root) > 1` before printing the "earlier repos" line, or rephrase to "any earlier paths from this run may already be staged".

## Architectural Concerns — Test Gaps

1. **`_tick_acs` has no test for the missing-header case (Concern #1).** Add a ticket with no `## Acceptance Criteria` header and assert close behavior — currently it would fail confusingly.

2. **`check_test_imports` has no test for the real "pytest not installed" path (Concern #2).** The existing test mocks `FileNotFoundError`, which is the wrong failure mode. Add a test using a subprocess in a venv without pytest, or mock `subprocess.run` to return `CompletedProcess(returncode=1, stderr="No module named pytest")` and assert the result is `[]`.

3. **`_check_gitignored` has no test for the not-in-any-git-repo path (Concern #4).** Add a test passing a `/tmp/file.py` (outside any git repo) and assert the failure mode (today: silently skipped, then staging fails; after fix: gitignore check fails first with clear message).

4. **`_check_gitignored` has no test for the `git check-ignore` rc >= 128 fail-closed path.** The new fail-closed branch (lines 287-294) is exercised only by code review. Add a test: mock `subprocess.run` to return rc=128 with a stderr message and assert `SystemExit(2)`.

5. **No test verifies `_check_gitignored` works when --files spans multiple git roots.** Per-root grouping is the whole point of the change vs. the simpler single-call implementation, but the test suite has only single-root cases. A workspace ticket with `--files harness/foo.py /external/proj/bar.py` would exercise the grouping logic.

## Suggested Next Session Focus

1. **Fix the "missing pytest" misreport in `check_test_imports` (Concern #2, Test Gap #2).** ~5 LoC + 1 test. Add `importlib.util.find_spec("pytest")` early-return. Without this fix, every machine that runs `repo_hygiene.py --warn-only` without pytest installed gets a spurious WARN — the check becomes self-defeating noise.

2. **Reconcile the `architecture_invariants.md` placeholder vs. actual ticket schema (deferred from S19).** Either fill in invariants 1–2 with real rules and align the layer enum to include `tooling`, or remove the placeholder template entirely and point Opus to `docs/tickets/TEMPLATE.md` as the schema of record. The "deferred to next session" note is real technical debt — Opus sees the placeholder enum in every review context.

3. **Tighten `_tick_acs` symmetry with `_check_acs` (Concern #1, Test Gap #1).** ~5 LoC + 1 test. Cheap, prevents a confusing user experience for the first ticket that lacks the standard header.

## Carry-forwards (issues unresolved ≥ 2 sessions)

- **`architecture_invariants.md` is a placeholder file.** Now 2+ sessions of acknowledgment without action. The S18 review noted the `layer: tooling` enum mismatch (Concern #2); S19 implemented `--layer` in create_ticket.py but explicitly deferred updating the invariants doc. Until the doc has real invariants, every Opus review's "Invariant Violations" section is structurally weak — there's nothing concrete to check against.
