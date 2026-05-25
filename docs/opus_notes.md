# Opus Review — S6 2026-05-25

Scope: closed T026 (telemetry hook + analyzer), T027 (classify_session `--repo`
config), T028 (prepare_opus_context invariants/template per-repo), T029
(`scripts/` in code_paths), T030 (batch consistency fixes). ~1061 insertions /
32 deletions. New PostToolUse hook wired in `.claude/settings.json`, new
`analyze_tool_log.py`, and 18 new telemetry tests.

## Invariant Violations

None new. S3 #6 / S4 #1 (dead `sessions_rel` path-based comparison) and the
broader carry-forward backlog from S5 remain unchanged this session.

## Concrete Bugs

1. **`scripts/hooks/log_tool_usage.py:48-53` — session tag in the JSONL log is
   wrong because the fast-path reads a bare integer and returns it as the
   session ID.** `current_session.persist_session(n)` writes `str(n)` (e.g.
   `"6"`) to `.git/CLAUDE_SESSION_ID`; the hook reads it via
   `claude_id.read_text().strip()` and returns `"6"` unchanged. The slow path
   (line 117) correctly returns `f"S{int(entries[-1]) + 1}"` (e.g. `"S6"`).
   Result: when the cache file exists (the common case once
   `current_session.py` has been run at session-start), every record gets
   `"session": "6"` instead of `"session": "S6"`. The analyzer's
   `--session S6` filter (`analyze_tool_log.py:48`,
   `rec.get("session") != session_filter`) then returns zero records, and
   `workflow-review`'s Step 1b call to `analyze_tool_log.py --session
   S[CURRENT]` silently produces an empty report. Fix: prepend `"S"` in
   `_current_session()` when the cached value is numeric, or change
   `persist_session` to write `f"S{n}"`. Neither is covered by the 18 new
   telemetry tests — every test in `tests/test_telemetry.py` either constructs
   JSONL fixtures directly or runs the hook in isolation without populating
   `.git/CLAUDE_SESSION_ID`, so the bug is invisible to CI.

2. **`scripts/tools/harness_config.py:514-517` — `load_for_repo` silently falls
   back to harness config when the workspace `harness.yaml` exists but is
   malformed (YAMLError, IOError, etc.).** The `except Exception` block prints
   a WARNING to stderr but still returns `load()` — the harness root config.
   This is a fail-open: a workspace with a typo in its `harness.yaml` (e.g.
   wrong indentation in `code_paths`) silently gets the harness's
   classification config, producing wrong "code"/"docs" verdicts. Fix-closed
   behavior: `sys.exit(2)` on parse failure of an existing file, so the user
   sees the error before classification runs on the wrong rules. The current
   warning is easy to miss in a long session-close output stream.

3. **`scripts/hooks/log_tool_usage.py:89` — `_SESSION_CACHE` is declared but
   never read or written.** Dead code introduced this session. Either remove
   it or use it (presumably it was meant to cache the resolved session ID to
   avoid the slow-path re-read on every tool call; if so, that's a separate
   feature). At minimum, delete the unused module-level constant so it doesn't
   mislead the next reader.

4. **`scripts/hooks/log_tool_usage.py:134-142` — `_extract_exit` always returns
   0 for non-Bash tools because only `tool_response["exit_code"]` is checked.**
   Edit/Write/Read/NotebookEdit hook responses never include `exit_code`, so
   the `exit` field in the JSONL is uniformly 0 for those tools — making the
   field meaningless except as a Bash-vs-non-Bash signal. `analyze_tool_log.py`
   doesn't currently use `exit` in any of its sections, so this is latent
   noise rather than a downstream miscalculation, but the field name implies
   data that isn't actually being captured. Either drop the field, document
   "Bash only" in the docstring, or add Edit/Write success detection (the
   `tool_response` payload typically has `success` or error keys for those).

5. **`scripts/hooks/log_tool_usage.py:124-131` — Bash `command` is truncated to
   120 chars and logged verbatim with no secret scrubbing.** Commands like
   `psql -p hunter2 ...` or `curl -H 'Authorization: Bearer SECRET' ...` land
   in `.git/session_tool_log.jsonl` in plaintext. The log is local to `.git/`
   so confidentiality risk is bounded, but if a user ever shares the file
   (e.g. uploading for a workflow-review consultation), credentials leak. At
   minimum, document the risk in the hook docstring; ideally, scrub common
   secret patterns (`-p \S+`, `Bearer \S+`, `password=\S+`) before logging.

## Test Gaps

6. **No test exercises `_current_session()` in `log_tool_usage.py`.** The
   integration between `persist_session` (writes `"6"`) and `_current_session`
   (returns it verbatim) — Bug #1 above — is the highest-leverage missing
   test. A single test that writes `"6"` to a temp `.git/CLAUDE_SESSION_ID`,
   invokes the hook, and asserts the log line has `"session": "S6"` would
   catch the bug immediately.

7. **No test for `load_for_repo` malformed-YAML fail-closed behavior** (Bug #2).
   The new tests cover the happy path and the missing-file fallback but not
   the corrupt-YAML case. A test that writes invalid YAML and asserts the
   intended behavior (currently: silent fallback with WARNING; should-be:
   `sys.exit(2)`) would lock in either decision.

8. **No test that the PostToolUse hook self-gates correctly (exits 0 silently)
   when `workflow_telemetry` is unset or False.** The hook is wired in
   `.claude/settings.json` unconditionally, so every tool call spawns
   `log_tool_usage.py`. If the early-exit gate ever regresses (e.g. someone
   inverts a boolean), the hook would start writing logs on every harness
   install with no opt-in. Easy guard: a test that runs the hook with
   `workflow_telemetry: false` and asserts no log file is created.

## Architectural Concerns

9. **PostToolUse hook fires on every tool call regardless of telemetry-enabled
   state**, spawning a Python subprocess that does an import + YAML load
   before exiting. On a session with hundreds of tool calls, this adds
   measurable overhead even when telemetry is off. Two cheap mitigations:
   (a) check for a sentinel file (`.git/workflow_telemetry_on`) before any
   Python import, exiting in <10ms; (b) gate the hook in `.claude/settings.json`
   itself with a matcher that's only added when the feature is enabled (via
   a setup script). The current architecture pays the subprocess cost
   universally for an opt-in feature.

10. **`analyze_tool_log.py` `_retry_sequences` (line 317-333) interleaves
    sessions when computing "same tool ≤30s" pairs.** If session S5 ends at
    timestamp T and session S6 starts at T+10s with the same tool, the pair
    is flagged as a "retry" even though they're in different sessions. Easy
    fix: split records by `session` first, then compute retries per-session,
    then concatenate. Without this, multi-session aggregation reports are
    polluted with false-positive retries at session boundaries.

11. **`scripts/tools/prepare_opus_context.py` repo-local invariants/template
    lookup is correct but doesn't surface which set was used in the output
    context.** When `--repo` is provided and the repo has its own
    `architecture_invariants.md`, that file is embedded; if not, the harness's
    is embedded silently. Opus reviewing the context can't tell which it got
    without re-reading the diff. Add a header line like `Source:
    <repo>/docs/architecture_invariants.md` or `Source: harness fallback` to
    the section so the review is explicit about which constraints apply.

## SKILL / Consistency

12. **`scripts/tools/README.md` `analyze_tool_log.py` row** (line 47) lists it
    in the "Workspace-compatible scripts" table but the script reads only
    `.git/session_tool_log.jsonl` from the harness root — it has no workspace
    awareness at all. Strictly speaking it's harness-root-only because the
    hook writes to harness `.git/`. If the intent is per-workspace telemetry,
    the hook needs `--repo`-style scoping too. If single-harness telemetry is
    the design, the README row should say so explicitly to avoid confusion
    when a workspace user runs `analyze_tool_log.py` expecting workspace data.

## Carry-forwards from S1–S5

No carry-forward was addressed this session (S6 was a pure-ticket-closure
session for T026–T030, all newly opened in S5). The backlog of ~18 carry-forwards
remains unchanged from the S5 review. The Phase 1 gate dependency ("create
first real workspace and use it") is still blocking — and worth doing before
or in parallel with the carry-forward cleanup, since live use is the only way
to validate the workspace-aware paths against real workloads.

## Suggested Next Session Focus

1. **Fix Bug #1 (session ID format mismatch in telemetry hook).** This makes
   the entire T026 deliverable inert for the headline use-case
   (`workflow-review` calling `--session S<N>`). One-line fix in
   `_current_session()` plus one integration test (Test Gap #6). Without it,
   T026 is shipped but functionally broken.

2. **Fix Bug #2 (load_for_repo fail-open on malformed YAML)** with a test.
   Small change but it closes a fail-closed invariant gap before the first
   real workspace lands. Bundle with Bug #1 as a single "telemetry hardening"
   ticket.

3. **Then the carry-forward backlog session.** S5's recommendation #3 still
   stands and is now more urgent — the backlog grew by zero this session
   (good) but hasn't shrunk in three sessions (bad). Block out one full
   session for S1 #3 + S1 #7 / S3 #6 + S1 #11 + S3 #3 as a coherent
   workspace-scoped-paths cleanup, before any client workspace goes live.

---

# Opus Review — S7 2026-05-25

Scope: closed T031 (extract_opus_key_sections header-level bug), T032 (session-start
skill workspace flag), T033 (telemetry hook off-state overhead) + enabled
telemetry by default. ~440 insertions / 21 deletions across one tool, one
hook, one new helper, and two skill docs.

S6 inline-fix status check: Bug #1 (session ID `S<n>` normalisation) closed inline
(commit bf1f00d). Bug #3 (`_SESSION_CACHE` dead code) closed inline.
Bugs #2, #4, #5, and Concerns #10, #11, #12 from S6 remain open and unaddressed
this session — they should be noted as carry-forward.

## Invariant Violations

None new. Architecture invariants 1-5 are placeholders/optional and Invariant 5
(workspace isolation) is not touched by this diff. The fail-closed-on-exceptions
invariant (#4) is still violated by `harness_config.load_for_repo` (S6 Bug #2,
unchanged this session) — fail-open silent fallback on malformed YAML remains.

## Architectural Concerns

1. **`scripts/hooks/log_tool_usage.py:128-135` — the bootstrap-from-yaml path
   subverts the T033 design goal.** T033's acceptance criterion was "OFF-state
   hook completes in well under 10 ms". With the bootstrap logic, the
   first-tool-call-after-fresh-clone (or after sentinel deletion outside
   `toggle_telemetry.py`) does a stdlib regex read of `harness.yaml` AND then
   touches the sentinel AND then proceeds to do the full slow path (PyYAML
   import + load via `_hc.load()`). That's the worst of both worlds — the
   user pays the cost they were trying to avoid, exactly when the cache is
   cold. The intended fast-OFF path only works when telemetry is genuinely off
   in `harness.yaml`. Fix options:
   (a) drop the bootstrap entirely — require explicit `toggle_telemetry.py on`,
       and remove the auto-touch logic; OR
   (b) bootstrap-touch the sentinel but `sys.exit(0)` after — skip the slow
       path on the very first call; the next call will hit the fast path. This
       drops one record on fresh clone but eliminates the cost spike.
   Current code does the bootstrap touch AND proceeds, which is the worst
   choice.

2. **`scripts/hooks/regenerate_ticket_index.py:127-134` — same workspace-flag
   omission as T032, but in a hook (not a skill).** `get_current_session()`
   at line 28-37 invokes `current_session.py` with no `--sessions` flag.
   `check_closed_attribution` calls it to validate the `closed:` field of a
   newly-written ticket. When the ticket lives under
   `<workspace>/internal/tickets/closed/`, the hook compares the workspace's
   `closed: S<workspace_session>` value against the **harness-global** session,
   producing spurious "T016 attribution mismatch" warnings on every workspace
   close. T032 fixed the user-facing skill but missed this hook — same root
   cause (T020 made the script accept `--sessions` but consumers didn't
   migrate). Fix: in `regenerate_ticket_index.py`, detect the workspace
   (already done at line 82 via `_detect_workspace_from_path`) and pass
   `--sessions <ws>/internal/sessions.md` to the subprocess.

3. **`scripts/tools/toggle_telemetry.py:31-36` — regex `^#?\s*(workflow_telemetry\s*:\s*).*$`
   only strips a single leading `#`.** A `# # workflow_telemetry: true` (double-
   commented, as some users do when temporarily disabling) becomes
   `# workflow_telemetry: false` after toggle off — still commented, and
   `_yaml_telemetry_enabled()` in the hook treats it as false even when the
   user toggles on. Minor edge case but trivially fixed by `^[#\s]*` or
   `^(#\s*)*` in the prefix. Also note: the regex matches `workflow_telemetry:
   trueblue` because `_yaml_telemetry_enabled` in the hook (line 118) has no
   trailing `\s*$` or word boundary — same class of bug. Add `\b` or `\s*$`
   to both.

4. **`tests/test_telemetry.py:128-132` — `test_exits_silently_when_telemetry_disabled`
   no longer tests what its name promises.** The pre-S7 version had a
   comment about "Log must NOT have been written" but the assert never
   verified it. S7 removed the comment but didn't add a check. With S7's
   default-on state, this test runs with telemetry ON — so the hook *does*
   write a log line. The test passes because it only asserts exit code 0.
   Either rename to `test_exits_silently_with_any_state` (descriptive of
   actual behaviour) or rebuild the test to set telemetry off, run the hook,
   and assert no append to `.git/session_tool_log.jsonl`. The `test_exits_
   silently_when_both_off` test (lines 88-109) does cover this case
   properly, so this old test is now redundant noise.

5. **`tests/test_telemetry.py:88-109` — `test_exits_silently_when_both_off`
   mutates the real `harness.yaml` and `.git/workflow_telemetry_on` of the
   running repository.** The `try/finally` restores state on success, but if
   the test is interrupted (SIGINT, OOM, runner timeout), the user's actual
   harness.yaml is left in `workflow_telemetry: false` state — silently
   disabling telemetry until the next manual fix. A safer pattern is to
   patch `ROOT` via monkeypatch (as the sibling `test_current_session_normalises_
   bare_integer` does at lines 143-156). The existing isolated-root helper
   `_make_fake_root` (lines 52-72) does exactly this but is unused. The test
   should use it.

6. **`scripts/hooks/log_tool_usage.py:75-82` — `_extract_exit` is still
   Bash-only (S6 Concern #4, unaddressed).** S6 raised this and S7 deferred
   it. The `exit` field is uniformly 0 for Edit/Write/Read records, making
   it a misleading column in the JSONL. Either drop it from the record dict
   at line 153-159, or rename to `bash_exit` and only emit for Bash records.
   Current state ships latent noise.

7. **`scripts/tools/analyze_tool_log.py:71-87` — `_retry_sequences` still
   interleaves sessions (S6 Concern #10, unaddressed).** With telemetry now
   default-on, multi-session aggregation (e.g. running
   `analyze_tool_log.py` with no `--session` filter) will continue to flag
   false-positive retries at session boundaries. The fix is ~5 lines: group
   `records` by `session` first, run `_retry_sequences` per group, then
   concatenate. The urgency goes up because the data starts accumulating
   silently from S7 onward.

## Bugs & Implementation Issues

1. **Confirmed: `scripts/hooks/log_tool_usage.py:135` — bootstrap failure is
   logged but not surfaced; the hook continues with a missing sentinel.**
   If `.git/` is missing or write-protected, `_log_error` writes to
   `.git/session_tool_log.errors` (which will also fail), and the hook
   proceeds to the slow path. On every subsequent tool call the bootstrap
   re-attempts and re-fails. There's no rate-limit on the error log either.
   In an environment where `.git` is genuinely inaccessible, this could
   inflate `session_tool_log.errors` to thousands of lines per session.
   Either fail-fast (`sys.exit(0)` after first bootstrap failure within a
   process — though hooks are per-tool-call subprocesses so this is moot)
   or rate-limit via `mtime` check on the error file.

2. **Confirmed: `harness.yaml:31-34` — `workflow_telemetry: true` default
   means the harness ships hot-by-default for all consumers cloning it.**
   This is a deliberate session decision (per the S7 active-work entry),
   but it deserves a note: T026 was originally framed as "opt-in"; flipping
   the default reverses that without a ticket explicitly authorizing the
   change. The flip is logged in commit b6a82d9 but not tied to a ticket.
   Either retroactively note the policy change in a ticket (T026 follow-up
   or new ticket) or annotate the comment in `harness.yaml` itself
   ("default-on as of S7; opt out via toggle_telemetry.py off"). Without
   that, future readers will see the S6 ticket description ("Off by default
   — opt in via harness.yaml") in `git log` and be confused.

3. **Suspected: `scripts/tools/extract_opus_key_sections.py:118-121` —
   `argparse.ArgumentParser()` (default `add_help=True`) combined with the
   `--with-carry-forwards` flag means `--help` exits with code 0 BEFORE the
   `if _args.with_carry_forwards:` branch at line 124 ever runs.** The test
   `test_help_flag_exits_zero` asserts exit 0 and `"usage" in stdout` —
   which passes — but the help text doesn't document `--with-carry-forwards`
   behavior (just that the flag exists). Minor docstring gap, not a bug.
   More importantly: `--with-carry-forwards` is undocumented in the SKILL
   and only mentioned in the source. If session-start skill ever wants
   carry-forwards in the briefing, the option is invisible.

## Suggested Next Session Focus

1. **Fix Concern #2 (`regenerate_ticket_index.py` workspace flag omission).**
   This is the exact same bug class as T032 just closed, in a noisier
   location: the PostToolUse hook fires on every workspace ticket Edit.
   With telemetry default-on, the false-positive T016 warnings will start
   spamming stderr on every workspace session. One-line fix + one test in
   `tests/test_workspace_path_flags.py`. Prioritise before next workspace
   session because it produces user-visible noise.

2. **Address Concern #1 (telemetry bootstrap kills the off-state perf goal)
   OR document the change.** The current implementation defeats T033's
   stated acceptance criterion on first-call-after-fresh-clone. Either
   (a) change the bootstrap to early-exit after touch (one extra `sys.exit(0)`),
   or (b) drop the bootstrap entirely and require explicit toggle. Either
   way, update the docstring to reflect actual behaviour. ~10 LoC; bundle
   with a fast-exit timing test in `test_telemetry.py`.

3. **Begin the carry-forward backlog session.** The backlog is now ~21 items
   (S5's ~18 plus four S6 concerns deferred). Two consecutive sessions
   (S6, S7) have closed only newly-opened tickets without touching the
   backlog. With Phase 1 gate complete and the first real workspace live,
   the workspace-scoped-paths cleanup (S1 #3 + S1 #7 / S3 #6 + S1 #11 +
   S3 #3) is now blocking confident expansion to a second workspace. One
   focused session, no new feature work.
