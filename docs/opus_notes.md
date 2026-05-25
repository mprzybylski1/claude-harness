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

---

# Opus Review — S8 2026-05-25

Scope: closed T034 (regenerate_ticket_index workspace --sessions flag + path-component
closed check), T035 (telemetry bootstrap exit + batch fixes), T036 (load_for_repo
fail-closed on malformed YAML), T037 (_retry_sequences session isolation), T038
(prepare_opus_context invariants source labeling). All five tickets address S6/S7
Opus carry-forward findings. Roughly 125 insertions / 30 deletions across 7 source
files plus test updates.

S7 inline-fix status: All five tickets cleanly close the items called out in
S7's "Suggested Next Session Focus" #1 and #2, plus three more deferred S6
concerns (#10, #11, #4-docstring). Net carry-forward shrinkage this session
for the first time in three sessions — backlog drops from ~21 to ~17.

## Invariant Violations

None new. **Invariant 4 (fail-closed on exceptions)** — the long-standing
violation in `harness_config.load_for_repo` is now FIXED (T036). The fix
correctly calls `sys.exit(2)` with an ERROR message on YAMLError, and the
test asserts both exit code and ERROR presence in stderr. Verified by
inspection of `scripts/tools/harness_config.py:38-45` and
`tests/test_telemetry.py:337-352`.

**Invariant 5 (workspace isolation)** is unchanged. T034's fix to pass
`--sessions` in `regenerate_ticket_index.py` strengthens workspace isolation
in a related way — workspace ticket closes no longer accidentally consult
the harness-global session. Good direction even if not strictly an Invariant 5
matter.

## Architectural Concerns

None new. Carry-forwards from S7 that remain open and now drift further
behind are noted in the Findings section.

## Suggested Next Session Focus

1. **Carry-forward backlog cleanup.** Three sessions running, S5's
   recommendation is now the same as S6's and S7's: block out one session
   for the workspace-scoped-paths cleanup (S1 #3, S1 #11, S3 #3) plus the
   two surviving S7 carry-forwards (Concern #5: real-harness.yaml mutation
   in `test_exits_silently_when_both_off`; Concern #6: `_extract_exit`
   field is still in the record despite the docstring update). Most of
   these are 10–30 LoC each — bundleable in one session.

2. **Fix the S7-flagged test isolation gap (Concern #5).** With telemetry
   default-on, an interrupted `test_exits_silently_when_both_off` leaves
   the user's `harness.yaml` flipped to `false` silently. Adopt the
   `_make_fake_root` helper (already present in the file, unused). One
   test change, no source change.

3. **Decide on `_extract_exit` field — drop it or rename it.** The
   docstring update (T035) clarifies the semantics but does not address the
   downstream noise: `analyze_tool_log.py` doesn't use `exit`, every Edit/
   Write/Read record has a misleading `"exit": 0`, and the field will
   accumulate forever. Either rename to `bash_exit` and omit for non-Bash
   tools, or drop entirely. ~5 LoC change.

## Findings

1. **`scripts/tools/toggle_telemetry.py:31-36` — substitution regex consumes
   the trailing newline and re-emits it, producing fragile output if the
   regex is ever changed.** [Concern] The current pattern
   `r"^[#\s]*(workflow_telemetry\s*:\s*)\S*\s*$"` with replacement
   `rf"\g<1>{new_val}\n"` works correctly today because `\s*` is greedy
   and consumes the `\n` (since `\s` in Python re matches `\n`), and the
   replacement emits a fresh `\n`. But this is non-obvious and brittle —
   a maintainer who tightens `\s*` to `[ \t]*` will introduce a duplicate-
   newline regression on each toggle. Fix: replace with two explicit
   patterns — one for the literal `\n` boundary, one for last-line-without-
   newline — or use `re.MULTILINE` with `\s*$` excluding `\n` (`[ \t]*$`).
   Not blocking; document the subtlety as a code comment at minimum.

2. **`tests/test_telemetry.py:88-109` — `test_exits_silently_when_both_off`
   still mutates the real harness `harness.yaml` and `.git/workflow_telemetry_on`
   sentinel.** [Test gap, carry-forward from S7 Concern #5] The S7 Opus
   review called this out explicitly: the `_make_fake_root` helper at
   lines 52-72 already exists and would correctly isolate the test, but
   the test still touches real repo files. With telemetry default-on, an
   interrupted run (SIGINT/timeout/runner crash) silently flips the user's
   harness.yaml to `false` and removes the sentinel — and the user only
   discovers the regression when they notice their tool log has stopped
   growing. Fix: patch `ROOT` via monkeypatch using `_make_fake_root` (as
   `test_current_session_normalises_bare_integer` already does), or accept
   that this is a real-harness integration test and run it conditionally.

3. **`scripts/hooks/log_tool_usage.py:75-82` — `_extract_exit` field is
   still in every JSONL record despite the docstring clarification.**
   [Carry-forward from S6 Bug #4 / S7 Concern #6] T035's resolution
   credits "S7 C#6" as closed but only updated the docstring; the
   `exit` key is still emitted at line 160 in the record dict for all
   tools. Every Edit/Write/Read line has `"exit": 0` with no useful
   meaning. `analyze_tool_log.py` reads but does not consume the field
   anywhere. The next maintainer who adds an exit-failure report will
   build it on data that does not actually exist for ~95% of records.
   Either drop the field or rename it to `bash_exit` and conditionally
   emit (`if tool_name == "Bash":`).

4. **`scripts/hooks/log_tool_usage.py:128-138` — bootstrap path still
   pays the stdlib regex + sentinel-touch cost on every fresh clone's
   first tool call.** [Concern, follow-on from S7 Concern #1] T035
   resolved this partially: the hook now `sys.exit(0)` after touching
   the sentinel, dropping one record on bootstrap. That's the cleaner
   of the two options Opus proposed. However, the cost on the bootstrap
   call (one `re.search` against `harness.yaml` plus a filesystem touch)
   is still measurable on a fresh clone — it just happens once now
   rather than once per tool call. Acceptable trade-off, but worth a
   note: if a CI pipeline runs the hook with no `.git/` writable, the
   `_log_error` path will exhaust `.git/session_tool_log.errors` and
   continue to fail on every tool call. Not actionable yet, but flag
   it now so we know to add rate-limiting if it ever bites in production.

5. **`scripts/hooks/regenerate_ticket_index.py:107-112` — `_is_closed_ticket`
   calls `Path(file_path).resolve()` on tool-provided paths.** [Concern]
   `resolve()` touches the filesystem to canonicalise symlinks. For
   tickets being deleted (a future `git mv`-like workflow) the file
   may not exist; `Path.resolve()` in Python 3.6+ tolerates missing
   files (returns the would-be absolute path) but the behavior is
   strictness-sensitive across Python versions. Safer alternative:
   `Path(file_path).parts` directly (already absolute when claude-code
   provides the path; for relative paths the lexical check still works).
   `Path.resolve(strict=False)` is implicit but worth verifying against
   the Python versions you support. Not a bug today; a portability
   landmine.

6. **`scripts/tools/prepare_opus_context.py:402-411` — `inv_path =
   repo_root / "docs" / "architecture_invariants.md"` checks the workspace
   path even when `--repo` was not provided.** [Bug, latent] When the
   tool is run without `--repo`, `repo_root` defaults to `ROOT` (line
   ~50 in the same file). In that case, `repo_root / "docs" / ...` and
   `ROOT / "docs" / ...` are the same path. The `inv_source` label will
   say "repo-local" even though there is no separate repo — this is
   confusing for the Opus reviewer reading the context. Fix: only label
   as "repo-local" when `--repo` was explicitly provided AND the path
   exists at `<repo>/docs/`. Currently the label is technically correct
   (`repo_root == ROOT`, so the file IS the repo-local file by
   tautology) but misleading.

7. **`scripts/hooks/check_session_log.py:262-271` — `sessions_display`
   pattern is correct but the variable usage is unconventional.** [Style
   nit / concern] The pattern of `sessions_display = sessions_path`
   followed by `sessions_display = sessions_rel` inside the try block is
   subtle. If `relative_to` succeeds but `sessions_rel in all_changed`
   returns False, control falls through to the content-based check with
   `sessions_display = sessions_rel` — which is correct. If
   `relative_to` raises ValueError, `sessions_display = sessions_path`
   (the original assignment) survives. Verified correct by inspection.
   A clearer style would be to compute both branches with explicit
   else clauses, but this is non-blocking and the comments adequately
   document the intent.

8. **No test for the new `_is_closed_ticket` path-component check.**
   [Test gap] T034 closed S1 #11 by tightening `_is_closed_ticket` from
   a `"/tickets/closed/" in file_path` substring check to a path-
   component walk. This is a correctness improvement (rejects
   `/foo/tickets-closed-archive/bar` style false positives). But there's
   no test exercising the new function — neither the false-positive
   it now correctly rejects, nor the standard happy path. Easy add: two
   `pytest.parametrize` cases in `tests/test_workspace_path_flags.py`
   (existing file) or `tests/test_telemetry.py` (related-by-T034).

9. **No test for `regenerate_ticket_index.py` workspace-aware T016
   attribution.** [Test gap] T034's headline change is that
   `get_current_session()` now accepts `sessions_file` and that
   `check_closed_attribution()` derives the workspace sessions path via
   `_detect_sessions_file()`. There's no test that verifies the
   end-to-end behavior: write a workspace ticket with `closed: S<X>`
   matching the workspace's session, run the hook, assert no T016
   warning is emitted. Without it, a regression that drops the
   `--sessions` flag again would not be caught. Worth a single
   `subprocess.run` test that pipes a synthetic payload through the hook.

10. **`tests/test_telemetry.py:337-352` — the new `test_exits_on_invalid_yaml`
    uses `subprocess.run` with f-string-interpolated paths in source
    code.** [Concern] Embedding `{ROOT}` and `{repo}` directly into the
    `-c` source string works when paths contain no quote characters,
    but a tmp_path with quotes or backslashes would break it. Safer:
    use `--exit-on-fail` style env vars or a tiny script file written
    to tmp_path that does the import + call. Minor; tmp_path paths
    don't normally contain quotes.

11. **`harness.yaml:30` — the new "Default: ON" comment is in the right
    place but the previous "opt-in" framing in `docs/tickets/closed/T026-*.md`
    is now stale.** [Concern, carry-forward from S7 Bug #2] S7 review
    flagged that the default-on flip reverses T026's original "opt-in"
    framing without a documented decision. T035's resolution adds the
    comment to `harness.yaml` (good) but doesn't update or annotate the
    closed T026 ticket. Future readers consulting `git log` for the
    feature history will see "Off by default" in T026 and then "Default:
    ON in S7" in the YAML and have to reconcile the contradiction
    themselves. Add a one-line note to T026's Resolution section
    pointing forward, or open a tiny T039 documenting the policy flip.

12. **`scripts/tools/analyze_tool_log.py:76-78` — `defaultdict(list)` is
    correct but the explicit key for None-session records is `""`.**
    [Style nit] `r.get("session") or ""` collapses both `None` and the
    literal string `""` into the same group. If telemetry ever drops the
    `session` field entirely (e.g. the slow path in `_current_session()`
    returns `""`), records will be lumped together in a single group
    and could legitimately produce within-30s "retries" that span what
    should be inter-session boundaries. The S5/S6 bug that made this
    matter (bare-integer session ID) is fixed, so this is currently
    moot, but worth a `# session group ""` comment to document why
    empty-string is acceptable.

13. **Static analysis warning is a false positive.** [Concern, harness
    self-check robustness] `harness_config.py:99` triggers the `utcnow`
    static check because the substring "utcnow" appears in a docstring
    that lists example static check names. The actual code has no
    `datetime.utcnow()` call. This is a recurring pattern: docstrings
    that describe code patterns get flagged by the substring-based
    static analysis. Fix scope (large): add comment-stripping to the
    `utcnow` check in `prepare_opus_context.py`. Fix scope (small):
    rename the example in the docstring to a less collision-prone
    placeholder. Currently this generates one false-positive WARN in
    every session's static analysis section — not blocking, but it's
    visible noise that future Opus reviews will keep flagging.
