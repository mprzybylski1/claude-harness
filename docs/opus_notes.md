# Opus Review — S12 2026-05-26

Scope: closed T057 (telemetry workspace-aware session stamping), reverted hook commands from `$CLAUDE_PROJECT_DIR` to absolute paths after diagnosing empty-env-var bug, three impl-review hardening fixes on `log_tool_usage.py`. ~225 insertions / 50 deletions across 6 files. Touched the file that's been carrying the unbounded `_log_error` carry-forward for 4 sessions — but did not address it.

## Invariant Violations

None. Static analysis is clean. Invariant 5 (workspace isolation) is *strengthened* by T057 — telemetry now records which workspace each tool call touched, giving the boundary check a forensic trail it lacked. `_detect_workspace` reads only cfg from `_list_workspaces()` and calls `is_within_workspace(Path(path), cfg)`; never reaches into a foreign workspace's files. The per-call sessions.md read uses cfg-derived paths only, no cross-workspace leakage.

## Architectural Concerns

1. **`scripts/hooks/log_tool_usage.py` — `_detect_workspace` inner `except Exception: continue` silently masks workspace-matching errors.** [Fail-closed violation in spirit] Malformed cfg that raises causes the loop to skip; if all raise, the tool call is stamped harness-root with no error trail. Fix: log the exception (rate-limited per #5) so cfg corruption surfaces.

2. **`scripts/hooks/log_tool_usage.py` — Bash `=` value extractor mishandles chained `=`.** [Concrete bug, low impact] For `KEY=val=/path`, LHS-strip yields `val=/path` which fails the `startswith("/")` check and gets dropped. The heuristic is loose and untested.

3. **`scripts/hooks/log_tool_usage.py` — `~/` paths in Bash commands never match workspaces.** [Concrete bug — REGRESSION introduced S12] `_candidate_paths` accepts tokens starting with `/` or `~/`, but `Path("~/foo")` does NOT expand `~`. Workspaces declare absolute paths, so `cat ~/PycharmProjects/scrabble-score/foo.md` is stamped as harness-root, not the workspace. Fix: `Path(path).expanduser()` before `is_within_workspace`.

4. **`scripts/hooks/log_tool_usage.py` — `workspace_config` imported twice in `_detect_workspace`.** [Minor] Redundant but harmless. Pass `_wc` from `_list_workspaces` or hoist to module scope.

5. **`scripts/hooks/log_tool_usage.py` — bootstrap-failure rate-limit STILL not addressed; S12 added MORE `_log_error` call sites.** [Carry-forward from S8 #4 / S9 #8 / S10 #8 / S11 #9 — 4 sessions unaddressed; aggravated by S12] Went from ~1-2 error sites pre-S12 to ~6 post-S12. Ticket overdue.

6. **`scripts/hooks/log_tool_usage.py` — `ws_dir` resolution branch is asymmetric with `_session_for_workspace`'s cfg-first policy.** [Concern, minor] `main()` only computes `ws_dir` when `not ws_cfg.get("docs_path")`. A future change adding a docs_path edge case using ws_dir would silently break. Move ws_dir computation into `_session_for_workspace`.

7. **Hook path revert is correct but silent-failure root cause not fixed.** [Architectural] CLAUDE.md documents that `$CLAUDE_PROJECT_DIR` is empty in the hook subshell; absolute paths work around this, but the "hook fails silently when bash can't find the script" mode persists for any future misconfiguration. Consider a startup self-test or trap-based marker.

8. **Test gap: `_candidate_paths` `=`-stripping branch is uncovered.** Add tests for `--sessions=/path/file`, `KEY=val`, `KEY=val=/path` (Concern #2's ambiguous case).

9. **Test gap: `_detect_workspace` inner-except branch is uncovered.** A regression that throws on cfg lookup wouldn't be caught.

10. **Test gap: end-to-end `test_record_includes_workspace_field` does not cover the harness-root path.** Asserts workspace match only; no e2e counterpart for harness-root + empty workspace string.

11. **`scripts/tools/extract_carry_forwards.py` — S9 #6 warning swallowed in brief.** [Carry-forward S9 #6 / S10 #4 / S11 #8 — 3 sessions, T055 still open]

12. **`scripts/tools/surface_stale_tickets.py` — `*(none)*` literal duplicated.** [Carry-forward S10 #11 / S11 #10 — 2 sessions, T056 still open]

13. **`scripts/hooks/regenerate_ticket_index.py:_get_docs_path_map` cache never invalidated.** [Carry-forward S10 #6 / S11 #11 — 2 sessions, no ticket]

14. **`scripts/tools/close_ticket.py:189` — `ticket_path.unlink()` BOTH-locations failure mode.** [Carry-forward S10 #1 / S11 #1 — 2 sessions, no ticket]

15. **`scripts/tools/close_ticket.py:34` — `_ws_internal_dir` unused import.** [Carry-forward S11 #4 — 1 session]

16. **`scripts/tools/close_ticket.py` — re.sub injection fix and permissive-fallback content-preservation lack tests.** [Carry-forward S11 #5 / #6 — 1 session]

## Suggested Next Session Focus

- **Open and close a ticket for `log_tool_usage.py` `_log_error` rate-limit (S8 #4 et al, 4 sessions).** S12 added new error-emit sites; smallest scope: module-level counter + 60-second window, max ~10 errors per window. ~15 LoC + 2 tests.
- **Tighten `_detect_workspace` silent-continue and `~/` expansion (Concerns #1 and #3).** Two small fixes in the file just touched. Bundles cleanly with the rate-limit ticket.
- **Close T055 (carry-forward warning in brief) — 3 sessions unaddressed.** Was suggested #2 in both S10 and S11. Continued deferral is a pattern; either close it or close-by-policy.

Opus carry-forwards (>= 2 sessions):
S8 #4 / S9 #8 / S10 #8 / S11 #9: log_tool_usage.py `_log_error` rate-limit (4 sessions; aggravated by S12)
S9 #6 / S10 #4 / S11 #8: extract_carry_forwards warning swallowed in brief — T055 (3 sessions)
S10 #1 / S11 #1: close_ticket.py BOTH-locations on unlink failure (2 sessions, no ticket)
S10 #11 / S11 #10: surface_stale_tickets *(none)* duplicated literal — T056 (2 sessions)
S10 #6 / S11 #11: regenerate_ticket_index `_get_docs_path_map` cache invalidation (2 sessions, no ticket)

---

# Opus Review S14

Scope: 8 tickets closed (T064–T071) — cleared the entire S13 workflow-review backlog. Two impl-review fixes (PID-unique tmp filename, clarified git-staging warning) and three S13-post-review fixes (revert _detect_workspace return→continue, hook errors rstrip, check_utcnow skip meta-tests) landed mid-session via b79a37f and 9566ff2. ~520 insertions / ~80 deletions across 8 files. Backlog cleared, but a real regression introduced in `close_ticket.py` for workspace tickets — see Bug #1 below.

## Invariant Violations

None. Invariant 4 (fail-closed) is strengthened in close_ticket.py: `_git_stage` exits with code 2 when git operations fail rather than silently leaving things half-done. Invariant 5 (workspace isolation) unchanged — telemetry boundary intact, no cross-workspace reads in S14 diff.

## Architectural Concerns

1. **`scripts/tools/close_ticket.py:218-224` — `_git_stage` is broken for workspace tickets with external `docs_path`.** [Concrete bug, high impact — REGRESSION introduced S14] When `internal is not None` and the workspace's `docs_path` points outside the harness git tree (e.g. scrabble-score's `/Users/mprzybylski/Documents/Projects/ScrabbleScore/.harness`), `_git_stage` calls `git -C $ROOT add /Users/...` which fails with `fatal: '<path>' is outside repository at '<ROOT>'`. The archive has already been moved; the tool then `sys.exit(2)` with the "stage manually" warning. So every workspace ticket closure now exits non-zero in production, even when everything else succeeded. Fix: if `internal` is not None and not under `ROOT`, either skip `_git_stage` entirely (the user manages that repo separately) or detect the correct git repo for `ticket_path` (`git -C str(ticket_path.parent)` with rev-parse to find the toplevel). Tests don't catch this because `test_workspace_flag_disambiguates` uses a tmp_path-internal workspace which IS inside the same git repo. The Scrabble Score workspace cfg in the live repo would exercise the bug.

2. **`scripts/hooks/log_tool_usage.py:179-209` — cross-process state file has a TOCTOU race that can overrun the rate-limit substantially.** The new flow is: read state → check window → increment → atomic-rename write. With concurrent hook processes (which happen when batch tool calls fire), both processes can read count=N at the same time, both write count=N+1, both append errors. The atomic rename only guarantees the *final state file* isn't half-written; it does NOT prevent lost-update increments. T071's cross-process test is sequential (one subprocess at a time), so it cannot detect this. With ~10 concurrent hooks (realistic during a multi-Edit operation), the effective per-window cap could be ~20+ errors. Fix options: (a) `fcntl.flock` on the state file; (b) accept the looseness and document explicitly that the cap is approximate; (c) bound errors via log-file truncation instead of a counter.

3. **`scripts/tools/close_ticket.py:175-197` — `_atomic_move` + `_git_stage` ordering means the index ends up in an inconsistent state if `_git_stage` exits.** Sequence: (1) `_atomic_move` moves ticket to archive and unlinks open/ (commit-pending). (2) `_regenerate_index` updates INDEX.md (commit-pending). (3) `_git_stage` fails — exits 2 with warning. Result: filesystem is correct, but nothing is staged. Then the user runs `git status` and may not realize the workspace ticket was actually closed (the warning IS printed, but the exit code is misleading — most CI/scripts treat nonzero as "the operation failed"). Either swap the order so staging happens FIRST (in dry-run mode, then commit only after move) — complex — or change the warning to "close succeeded; manual staging needed" and exit 0 with a distinct status indicator. The current behavior conflates "filesystem moved + not staged" with "operation failed".

4. **`scripts/hooks/log_tool_usage.py:189` — window-expiry check uses `>` not `>=`.** If `_ERR_WINDOW_SECS = 60` exactly and now - window_start == 60.0, the condition `60.0 > 60` is false and the count is NOT reset. Edge case, but: combined with the file-state JSON having float precision, a borderline case can extend the window by one tick. Use `>=`.

5. **Carry-forward from S12: `_ws_internal_dir` unused import in `close_ticket.py:34` — STILL NOT ADDRESSED.** Now 3 sessions unaddressed (S11 #4, S12 #15, S13 carry-forward, S14). Trivial fix; pattern is to leave it forever.

6. **Carry-forward from S12: `close_ticket.py` re.sub injection fix and permissive-fallback content-preservation lack tests — STILL NOT ADDRESSED.** Now 3 sessions unaddressed.

7. **Carry-forward from S12: `_candidate_paths` `=`-chain and `~/`-expansion tests — `~/` expansion still not fixed.** S12 #3 noted that `Path("~/foo")` is not expanded before `is_within_workspace`; S13 noted it again; S14 didn't touch it. The bash token extractor accepts `~/...` (line 85, 87) but never calls `.expanduser()` at the workspace-match site. Trivial fix.

## Architectural Concerns — Test Gaps

1. **`_git_stage` workspace path (Concern #1) is entirely untested for the real configuration.** Tests live in a tmp_path that's all one git repo. A test that mocks an `internal` path outside `ROOT` would have caught this before S14 close.

2. **`_log_error` cross-process race (Concern #2) is not tested.** The new test `test_rate_limit_cross_process` runs 100 subprocesses *sequentially* (line 753 of test_telemetry.py: `for _ in range(100): subprocess.run(...)`). A concurrent test (e.g. `concurrent.futures.ProcessPoolExecutor` firing N processes in parallel) would detect the overshoot.

3. **`close_ticket.py --force` overwrite path is not tested for the case where the existing archive has been edited.** `test_force_bypasses_archive_exists_check` writes "stale archive content" but doesn't check that, e.g., a manually-edited archive's content is properly replaced (not appended). The `_atomic_move` should overwrite via `os.replace`, but if `--force` ever changes the write semantics this would silently regress.

4. **`_log_error` boundary at count==11 marker line is still untested.** Carried over from S13. The marker string "[rate-limit engaged — further errors suppressed]" appears in code at line 205 but no test asserts it appears exactly once at count 11.

## Suggested Next Session Focus

1. **Open and close a ticket for `_git_stage` workspace path (Concern #1).** This is a regression S14 introduced that breaks workspace ticket closure in production (scrabble-score). ~20 LoC + 1 test. Highest priority — actual functional regression.

2. **Open and close a ticket for `_log_error` cross-process race (Concern #2) OR document T071's resolution as "approximate cap, race-prone under concurrency".** T071's resolution claims the cross-process problem is solved; the sequential test doesn't prove it. Either add `fcntl.flock` or amend the closed ticket to honestly state the limitation.

3. **Clear the perennial carry-forwards: `_ws_internal_dir` unused import (3 sessions), close_ticket.py re.sub injection tests (3 sessions), `~/` expansion in `_candidate_paths` (3 sessions).** Each is ≤ 10 LoC. Three sessions of deferral on trivial items is a process smell — close them as a sweep or close-by-policy with rationale.

## Carry-forwards (issues unresolved ≥ 2 sessions)

- S11 #4 / S12 #15 / S13 carry: `_ws_internal_dir` unused import — 3 sessions, no ticket
- S11 #5 / S11 #6 / S12 #16 / S13 carry: close_ticket re.sub + permissive-fallback test gaps — 3 sessions, no ticket
- S12 #3 / S13 carry: `~/` expansion in `_candidate_paths` — 2 sessions, no ticket

---

# Opus Review S15

Scope: closed T072 (workspace `_git_stage` regression from S14) and T050 (opus archive splitting — closed as already-implemented + tests). ~226 insertions / 31 deletions across 3 source/test files. S15 fixed the highest-priority finding from S14 (the actual production regression for workspace ticket close) and addressed the T050 deferral by writing tests against existing behavior rather than new code. Backlog dropped to 0 open tickets — but several S12/S14 carry-forwards are still untouched.

## Invariant Violations

None. `_git_root_for` strengthens Invariant 5 (workspace isolation) by routing `git add`/`rm --cached` to the correct repo per workspace, instead of leaking workspace ticket archive paths into the harness repo's index. Invariant 4 (fail-closed) is preserved: when the workspace's docs_path is in a non-git directory, the script exits 2 with a clear stderr WARNING and a manual-staging command (verified by new `test_non_git_workspace_warns_and_exits_nonzero`).

## Architectural Concerns

1. **`scripts/hooks/log_tool_usage.py:179-209` — `_log_error` cross-process race is STILL UNADDRESSED.** [Carry-forward S14 #2 — 1 session] The read→check→increment→write flow has no `fcntl.flock`; two concurrent hook processes can both read count=N, both write count=N+1, both append errors. S14 closed T071 claiming this was solved, but the test (`test_rate_limit_cross_process`) runs subprocesses sequentially. S14 review explicitly called this out as a #2 priority for S15; S15 ignored it. Fix: either add `fcntl.flock` on `_ERR_STATE_PATH` for the duration of the read-modify-write, or honestly amend T071's closed resolution to state the cap is "approximate under concurrency." Continuing to ship code that claims a guarantee its test cannot verify is a process smell.

2. **`scripts/hooks/log_tool_usage.py:189` — window-expiry check still uses `>` not `>=`.** [Carry-forward S14 #4 — 1 session] Trivial fix (`now - window_start > _ERR_WINDOW_SECS` → `>=`). Edge case at exact 60.0s boundary; will rarely fire in practice but a one-character fix that S14 flagged.

3. **`scripts/hooks/log_tool_usage.py:108` — `Path(path)` without `.expanduser()` at workspace match site.** [Carry-forward S12 #3 / S13 / S14 — 3 sessions] `_candidate_paths` accepts `~/...` tokens at lines 85/87, but the workspace-match call at line 108 passes `Path(path)` directly to `is_within_workspace`. Result: Bash `cat ~/PycharmProjects/scrabble-score/foo.md` is stamped as harness-root, not the workspace. Two-character fix: `Path(path).expanduser()`. Three sessions of deferral on a one-token change is the same process pattern S14 called out — close it.

4. **`scripts/tools/close_ticket.py:210-221` — `_git_root_for` swallows non-zero git exit codes silently.** [Fail-closed concern, minor] When `git rev-parse --show-toplevel` exits non-zero (e.g. "fatal: not a git repository", or "fatal: this operation must be run in a work tree" for bare repos), the function discards both stdout and stderr (captured but never inspected) and returns None. The caller then prints the same "git staging failed — stage manually" warning for ALL failure modes: not-a-repo, bare-repo, corrupted repo, permission denied. The user cannot distinguish "this is intentionally not a git repo" from "your repo is broken." Fix: include `result.stderr.strip()` in the WARNING text so the user sees git's actual error message.

5. **`scripts/tools/close_ticket.py:_git_root_for` uses `path.parent` rather than `path`.** [Minor / docstring mismatch] The docstring says "git worktree root that owns path" but the call is `git -C str(path.parent) rev-parse`. For files this is equivalent (since the parent contains the file), but if a future caller passes a directory path, the behavior shifts (resolves the parent of the directory, not the directory itself). Either pass `str(path if path.is_dir() else path.parent)`, or update the docstring to say "the git worktree root that owns path.parent".

6. **`scripts/tools/close_ticket.py:34` — `_ws_internal_dir` unused import IS NOW REMOVED.** [Carry-forward resolved] Verified by grep: no remaining references. S15 cleared this implicitly (likely a side-effect of T072 work). No action.

## Architectural Concerns — Test Gaps

1. **`_git_root_for` is tested only at the integration level via `close_ticket.py` end-to-end.** No unit test directly invokes `_git_root_for(some_path)` with: (a) a bare git repo, (b) a path that doesn't exist, (c) a path inside a submodule, (d) a worktree (vs. main checkout). The integration tests cover the happy path (external project repo) and the non-git failure path, which is acceptable — but the docstring/behavior mismatch (Concern #5) wouldn't surface.

2. **No test asserts `_git_stage` does NOT leak workspace ticket paths into the harness repo's `git rm --cached` operation.** The existing `test_external_docs_path_workspace_stages_in_project_repo` checks that "T999" doesn't appear in `harness_status`, but a leaky `git rm --cached` (e.g. one that ran against ROOT before being switched to git_root) would only mutate the harness *index*, not the working tree — `git status --porcelain` might not show it depending on git version and prior state. Stronger check: `git -C harness diff --cached --name-only` must be empty.

3. **`_log_error` rate-limit concurrent test still missing.** [Carry-forward S14 Test Gap #2 — 1 session] Same as Concern #1 above; documenting it under tests too.

4. **`_log_error` count==11 boundary marker test still missing.** [Carry-forward S13 / S14 Test Gap #4 — 1 session]

## Suggested Next Session Focus

1. **Close out the `log_tool_usage.py` triad (Concerns #1, #2, #3).** All three are file-local, each ≤ 5 LoC, all flagged in S14, and one has been carrying for 3 sessions. Bundle into a single ticket: add `fcntl.flock` on `_ERR_STATE_PATH`, change `>` to `>=`, add `.expanduser()` at line 108. Add one concurrent test (`ProcessPoolExecutor` with N=20) and one test asserting `~/foo` paths match a workspace. ~25 LoC + 2 tests. Highest priority — three sessions of deferral on flagged one-line fixes is the exact pattern S14 told us to stop.

2. **Improve `_git_root_for` error transparency (Concern #4).** Include git's stderr in the failure WARNING so users can distinguish "not a git repo (expected)" from "git is broken." ~5 LoC.

3. **Audit T071's closed resolution.** It claims cross-process rate limiting is solved; the test is sequential. Either fix the underlying race (Concern #1) or reopen/amend the ticket to honestly document the limitation. Closing tickets with overclaimed resolutions makes future audits fragile.

## Carry-forwards (issues unresolved ≥ 2 sessions)

- S12 #3 / S13 carry / S14 #7: `~/` expansion in `_candidate_paths` — 3 sessions, no ticket
- S14 #2: `_log_error` cross-process race (T071 closed but unverified by test) — 1 session, no ticket but T071 is misleadingly closed
- S14 #4: window-expiry `>` vs `>=` — 1 session, no ticket
- S13 / S14 Test Gap #4: `_log_error` count==11 marker test — 2 sessions, no ticket
