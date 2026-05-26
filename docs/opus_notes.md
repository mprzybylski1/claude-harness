# Opus Review — S13 2026-05-26

Scope: 8 tickets closed (T044, T055, T056, T058–T061, T063) — clearing most of S12's carry-forward backlog including the 4-session `_log_error` rate-limit. Hook commands rebased onto `$(git rev-parse --show-toplevel)` for cross-machine portability with regression guard test. Static-analysis boundary hardened (T044). Session-brief now surfaces hook errors (T061). ~1587 insertions / 155 deletions across 36 files. Highest-throughput session in recent history. 8 new tickets opened (T064–T071) from workflow-review and impl-review — backlog rolled, not eliminated.

## Invariant Violations

None new. Invariant 5 (workspace isolation) is *strengthened* by T044 — `_is_within_root()` filters symlinks escaping scan_root in `check_test_syntax`, and `check_utcnow` / `check_bash_blocks` are documented as bounded by either grep's no-deref-of-dirs behavior or anchored-path construction. Invariant 4 (fail-closed) is also strengthened by the new `_detect_workspace` exception path, though with a side-effect — see Bug #1 below.

## Architectural Concerns

1. **S12 Concern #3 (`~/` paths in Bash never match workspaces) NOT addressed.** Carry-forward — `_candidate_paths` still accepts tokens starting with `~/` but `_detect_workspace` calls `is_within_workspace(Path(path), cfg)` without `expanduser()`. `cat ~/PycharmProjects/scrabble-score/foo.md` is still stamped harness-root. No ticket opened. Was a S12 regression and remains live.
2. **S12 Concern #15 (`_ws_internal_dir` unused import in `close_ticket.py:34`) NOT addressed.** Carry-forward — 1 session.
3. **S12 Concerns #5/#6 (re.sub injection + permissive-fallback content-preservation lack tests) NOT addressed.** Carry-forward — 1 session, no ticket.
4. **`_log_error` rate-limit is per-process — T071 correctly opened.** S13 closed T059 (the 4-session backlog item) but T071 notes the counter resets every hook invocation. Each hook is a fresh process, so the 10/60s limit only protects against bursts WITHIN one hook call — which already fires only once per tool event. The fix gives ~zero practical protection against the "read-only `.git/` causes every tool call to append" scenario S8 #4 originally raised. Honest assessment: T059 closed the symptom (unbounded loops within one process) but not the original problem. T071 needs cross-process state (file lock + counter) or a different approach (e.g. truncate-on-rotate).
5. **`_detect_workspace` fail-closed change is overcorrection.** [Carry-forward S12 #1 — addressed but altered] Old code: `except: continue` → silent skip, missed errors. New code: `except Exception as exc: _log_error(...); return ("", None)` — bails on the FIRST exception even if a later workspace cfg would legitimately match. If workspace[0] has a malformed config and workspace[1] should match the path, S13's code now stamps harness-root and logs an error, where the right behavior is "log + continue, only return harness-root if ALL workspaces fail". Practically: only one workspace today, so latent.
6. **`check_utcnow` static-analysis false-positives on test fixtures.** The S13 static analysis output shows 25+ WARN hits, ALL from `tests/test_static_analysis_symlink_boundary.py` where the test writes `datetime.utcnow()` as fixture STRING content (`(outside_dir / "evil_utcnow.py").write_text("import datetime\nnow = datetime.utcnow()\n")`). These are intentional — the test verifies the static check doesn't follow symlinks to find them. But the harness's OWN static check now permanently shows WARN, masking real utcnow regressions. Fix: `check_utcnow` should skip `tests/test_static_analysis_*.py` (the meta-tests), or use a stricter grep pattern that ignores string-literal context.

## Bugs & Implementation Issues

1. **`scripts/hooks/log_tool_usage.py:108-110` — `_detect_workspace` returns on first exception instead of continuing.** See Concern #5. Should be `_log_error(...); continue` not `return ("", None)`. Otherwise one bad cfg blinds telemetry for all other workspaces.
2. **`scripts/hooks/log_tool_usage.py:182-191` — rate-limit boundary off-by-one + counter never decays.** Trace: count starts 0, threshold 10. Calls 1-10 write normal messages (count goes 1→10). Call 11: `if _ERR_COUNT > 10` false (count=10), increment to 11, second `if _ERR_COUNT > 10` true, writes the marker. Call 12: count=11, `> 10` true, returns silently. Net: 10 real errors + 1 marker per 60-second window. Acceptable, but: (a) the comparison `if _ERR_COUNT > _ERR_RATE_LIMIT` could be `>=` to enforce a clean 10-message cap instead of 10+marker. (b) `_ERR_WINDOW_START` only resets when an error fires AFTER the window elapsed — if errors stop entirely, the window stays open until the next error, which is fine. (c) Per-process scope means this never engages in practice (T071 covers).
3. **`scripts/tools/extract_session_brief.py:88-94` — hook errors tail keeps trailing newlines, prints with double-newlines.** `for ln in deque(_ef, maxlen=...)` retains `\n`; `ln.strip()` filters empties but doesn't strip the newline from kept lines. `print(line)` then adds its own newline → double-spaced output. Minor cosmetic. Fix: `[ln.rstrip("\n") for ln in deque(...) if ln.strip()][-HOOK_ERRORS_KEEP:]`.
4. **`scripts/tools/extract_opus_key_sections.py:170-187` — `run_with_carry_forwards` re-emits stderr after the carry-forward list, not before.** The "(run expand_carry_forward.py ...)" hint follows the Note: line. If the user only sees the brief output sequentially, the Note about the warning shows up under the carry-forwards section but BEFORE the explanatory hint. Probably fine, but a user might read the hint and assume the Note is part of the hint. Low priority.
5. **`scripts/tools/run_static_analysis.py:55-62` — large block comment claims `check_bash_blocks` has "no direct file opens" but doesn't actually verify it.** The audit-comment refactor (T044) added a multi-line claim about each check's symlink behavior. This is documentation of intent, not enforcement. If a future contributor adds `open()` to `check_bash_blocks`, the comment becomes stale and there's no test to catch it. Convert to an explicit assertion or test.

## Test Gaps

1. **`_detect_workspace` early-return on exception is uncovered.** The new `return ("", None)` branch has no test. A regression to `continue` (correct behavior per Concern #5) would not be caught — and conversely, the current bug-via-overcorrection has no failing test pinning it.
2. **`_log_error` rate-limit boundary not tested at the marker emission point.** Tests in test_telemetry.py likely cover the burst case but no test asserts the marker text "[rate-limit engaged — further errors suppressed]" appears exactly once at count 11.
3. **`run_with_carry_forwards` stderr capture not tested with a missing-current-session scenario.** The function exists to surface a specific warning; no test exercises the path where `extract_carry_forwards` actually emits to stderr.
4. **`~/` expansion in `_candidate_paths` regression (Concern #1) is not tested.** T058 added rsplit coverage but `~/` paths still silently stamp harness-root.
5. **Hook errors tail double-newline cosmetic (Bug #3) — test_session_brief.py checks substrings but not exact line spacing.**

## Suggested Next Session Focus

1. **Fix `_detect_workspace` overcorrection — change `return ("", None)` to `continue` at log_tool_usage.py:109.** Bundle with `~/` expansion (S12 Concern #3 still live) and stricter `check_utcnow` to ignore test fixtures (Concern #6). Three small fixes in already-touched files. ~15 LoC + 3 tests.
2. **Close T071 properly: per-process rate-limit gives no real protection.** Options: (a) move counter to a file in `.git/` with flock for cross-process accumulation; (b) accept per-process scope and document T071 as policy-closed with rationale that hook errors are bounded by tool-call frequency anyway. Don't leave the ticket open with the false impression that T059 fixed the original problem.
3. **Close T070 (close_ticket.py BOTH-locations unlink — carry-forward S10 #1 / S11 #1 / S12 #14, now 3 sessions).** A try/except around `ticket_path.unlink()` with an actionable error message. ~10 LoC + 1 test. Repeatedly suggested across sessions and now ticketed.

## Carry-forwards (issues unresolved ≥ 2 sessions)

- S12 #3 (`~/` paths in Bash never match workspaces) — 1 session unaddressed, no ticket (treated as carry-forward because it was an explicit S12 regression flag).
- S10 #1 / S11 #1 / S12 #14: close_ticket.py BOTH-locations unlink — 3 sessions, NOW TRACKED as T070.
- S10 #6 / S11 #11 / S12 #13: regenerate_ticket_index `_get_docs_path_map` cache invalidation — 3 sessions, NOW TRACKED as T069.
- S11 #4 / S12 #15: `_ws_internal_dir` unused import — 2 sessions, no ticket.
- S11 #5 / S11 #6 / S12 #16: close_ticket.py test gaps (re.sub injection, permissive fallback) — 2 sessions, no ticket.
- S8 #4 / S9 #8 / S10 #8 / S11 #9 / S12 #5: `_log_error` rate-limit — 5 sessions; T059 closed in S13 but T071 correctly notes the fix doesn't address the original cross-process concern.

---

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
