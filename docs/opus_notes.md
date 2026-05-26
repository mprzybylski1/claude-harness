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

---

# Opus Review — S9 2026-05-26

Scope: closed T039–T042 (hook absolute paths, test isolation, drop `_extract_exit`,
`_is_closed_ticket` tests) and T045–T048 (carry-forward script, close_ticket
script, surface_stale_tickets clean-state, carry-forward session-ref pattern).
Merged project-agnostic workflow-review skill. ~1686 insertions / 169 deletions
across 27 files. Net carry-forward shrinkage again: S8 findings #2, #3, #8 are
addressed; findings #4, #5, #6, #9, #10, #11, #12, #13 carry forward.

S8 inline-fix status check: Finding #2 (`test_exits_silently_when_both_off`
mutating real harness.yaml) closed by T040. Finding #3 (`_extract_exit` field
still in records) closed by T041. Finding #8 (no test for `_is_closed_ticket`)
closed by T042.

## Invariant Violations

None new. Invariants 1–4 are placeholders. Invariant 5 (workspace isolation) is
not regressed; `close_ticket.py` correctly searches both harness root and
workspace internal dirs and picks the right archive/.

## Architectural Concerns

1. **`scripts/tools/close_ticket.py:172-189` — workspace YAML parsing uses a
   stdlib regex, not the YAML loader.** `_docs_paths()` does
   `re.search(r"^\s*docs_path\s*:\s*(.+)$", text, re.MULTILINE)` to extract
   `docs_path` from `workspace.yaml`. Same anti-pattern S6/S7 worked hard to
   remove from the telemetry hook. A `docs_path: "/quoted/path"` value will
   include the quotes; a multi-line YAML value will fail; a commented-out
   `# docs_path:` is correctly skipped only because `^\s*` doesn't match `#`.
   The harness already has a parsed-YAML loader (`harness_config.load`). Use
   it. Otherwise this divergence becomes another bug surface as workspace.yaml
   schemas evolve.

2. **`scripts/tools/close_ticket.py:286-301` — non-atomic write+rename.**
   `ticket_path.write_text(content); ticket_path.rename(dest)` writes the
   modified content to the original `tickets/open/` path THEN renames to
   `archive/`. If the rename fails (cross-filesystem, permission error, dest
   suddenly created by another process), the ticket is left in `open/` with
   the closure changes already applied — frontmatter says `status: closed`,
   resolution placeholder is gone, but the file still lives in open/. The
   next `close_ticket.py` invocation will exit because the `Resolution`
   placeholder is gone, leaving the user stuck. Safer: write to `dest` first,
   then `unlink` the original (or use `os.replace` with full path swap).

3. **`scripts/tools/close_ticket.py:141-169` — harness root wins on duplicate
   ticket IDs.** `_find_ticket` returns on the first match — searches harness
   root, then iterates workspaces. If two workspaces independently allocate
   T100, or a workspace and harness both have T045 (entirely possible since
   numbering is per-scope), the caller silently gets the harness one. No
   warning, no `--workspace` flag to disambiguate. The early-return loop on
   line 153 actually only fires once (it returns inside the for-loop), so
   even multiple harness matches aren't surfaced. Fix: collect all matches,
   error if >1 unless `--workspace=<name>` is supplied.

4. **`scripts/tools/expand_carry_forward.py:_extract_findings` end-of-finding
   detection only checks finding heads, not session heads.** Lines 388-405:
   `end = next((hp for hp in head_positions if hp > start), len(content))`
   where `head_positions` comes from `_ANY_FINDING_HEAD` only. If the matched
   finding is the LAST numbered finding in its session block, the extracted
   text will bleed into whatever follows — potentially the next session's
   header line, intro paragraph, and any prose until the next finding head
   (which could be 50+ lines away in the next review). The displayed `[From:
   <file> — S<N>]` label will be correct for the start position, but the
   trailing content can include unrelated material from the next session.
   Fix: include `_SESSION_HEAD` positions in the end-boundary computation
   (`min` of next finding head and next session head).

5. **`scripts/tools/extract_carry_forwards.py:54-60` —
   `_current_session_number()` derives "current" from the LAST `Opus Review
   — S<N>` header in `opus_notes.md`.** That works on a fresh session when
   the prior session's review is the newest header. But during the active
   session (between session-start and session-close), no header for the
   current session exists yet — so "carry-forward from S8" computed against
   `current_sn=8` yields age 0 and is silently filtered out. The threshold
   = 2 default makes this matter less, but the semantics are: ages are
   relative to the LAST WRITTEN REVIEW, not to the LIVE SESSION. If the
   intent of the script is to surface stale items at session-start, that's
   actually fine. If it's ever called mid-session (e.g. workflow-review)
   the result is off by one. Document the chosen semantic.

6. **`scripts/tools/surface_stale_tickets.py:54-56` — silent absence of
   aging section is now indistinguishable from format drift.** T047 changed
   the behavior from "warn that section parse drifted" to "return clean
   state". This is correct when the aging section is genuinely absent (no
   stale tickets), but it now masks the case where `generate_ticket_index.py`
   stops emitting the section because of a regression in the generator. The
   only signal of a generator regression would be: "no aging warnings ever".
   Mitigation: add a structural check at a higher level — e.g.
   `generate_ticket_index.py` should ALWAYS emit the section header, with
   "(none)" body if empty. Then `surface_stale_tickets.py` truly absent
   header = clean state with no ambiguity.

7. **`.claude/settings.json` hardcoded absolute paths.** Already tracked
   as T049, just noting it surfaced this session as the fastest fix for the
   workspace-cwd silencing problem (T039). The fix is correct but creates
   a portability landmine — anyone cloning this harness to a different path
   will silently get no hooks. T049 is open and the right next step.

8. **`scripts/hooks/log_tool_usage.py` bootstrap-failure rate-limit.**
   [Carry-forward from S8 Finding #4 — 1 session unaddressed] T035 fixed the
   bootstrap-cost concern by exiting after touch, but the failure-mode
   concern remains: a read-only `.git/` causes every tool call's bootstrap
   attempt to fail, and `_log_error` appends to `.git/session_tool_log.errors`
   without rate-limiting. Not actionable yet (no reported case), but should
   be a known limit.

9. **`scripts/hooks/regenerate_ticket_index.py:107-112` — `Path.resolve()`
   on tool-provided paths.** [Carry-forward from S8 Finding #5 — 1 session
   unaddressed] Symlink canonicalisation behavior is strictness-sensitive
   across Python versions; a portability landmine for tickets being moved
   atomically. Easy switch to lexical `Path(file_path).parts`.

10. **`scripts/tools/prepare_opus_context.py:402-411` — invariants source
    labeled "repo-local" even when `--repo` was not supplied.** [Carry-forward
    from S8 Finding #6 — 1 session unaddressed] Misleading label for the
    Opus reviewer. Trivial fix in the label-emitting code.

11. **No test for `regenerate_ticket_index.py` workspace-aware T016
    attribution.** [Carry-forward from S8 Finding #9 — 1 session unaddressed]
    A regression that drops the `--sessions` flag again would not be caught.

12. **`tests/test_telemetry.py:337-352` f-string-interpolated subprocess
    source.** [Carry-forward from S8 Finding #10 — 1 session unaddressed]
    Quote/backslash brittleness in tmp_path interpolation. Low urgency.

13. **`harness.yaml:30` "Default: ON" vs. T026 ticket framing.**
    [Carry-forward from S8 Finding #11 — 1 session unaddressed] Closed T026
    ticket still says "opt-in" without forward-pointer to the policy flip.
    One-line edit to closed ticket Resolution.

14. **`scripts/tools/analyze_tool_log.py:76-78` defaultdict empty-string
    grouping.** [Carry-forward from S8 Finding #12 — 1 session unaddressed]
    Minor robustness comment.

15. **Static analysis false positive: `harness_config.py:99` `utcnow` in
    docstring.** [Carry-forward from S8 Finding #13 — 1 session unaddressed]
    Still showing in this session's static analysis output ("WARN deprecated
    datetime.utcnow() usage" at line 99 — that line is a docstring listing
    example check names). Trivially fixed by renaming the docstring example;
    pragma-strip the docstring in the static analyser would be more robust.

## Bugs & Implementation Issues

**S9 #1 — `scripts/tools/close_ticket.py` `_replace_resolution` is too
strict.**
- File: `scripts/tools/close_ticket.py:214-225`
- The placeholder regex requires a specific shape:
  `## Resolution\s*\n` then optional `(?:> \*\*Client-visible:\*\*.*?\n(?:> .*\n)*\n)?`
  then `\(Fill in on close[^)]*\)\s*`. If a ticket's resolution section has
  extra blank lines, lacks the trailing `\n` after the blockquote, or has
  the `Client-visible` block written without leading `> ` on continuation
  lines, the regex fails and the script exits 2 — the user sees "ticket
  format unexpected" but the ticket has already been validated as having
  acceptable ACs. The user is now stuck without an obvious next step.
- Fix: split into two passes — first try the strict match, then fall back
  to a permissive match that replaces everything from `## Resolution` up to
  the next `^## ` heading. Print a warning instead of exiting on the
  fallback path.

**S9 #2 — `scripts/tools/close_ticket.py` session-stamp regex over-matches.**
- File: `scripts/tools/close_ticket.py:280-283`
- `re.search(r"\bS\d+\b.*\d{4}-\d{2}-\d{2}", resolution)` is used to decide
  whether to auto-append the closure session/date. If the user's resolution
  text mentions any historical session ("Reverted the S5 2026-01-01 commit")
  the check passes and the actual closure session is NOT recorded. The
  resolution is then archived without a verifiable closure timestamp.
- Fix: always append the closure stamp on a new line; if the user wants to
  reference history in prose that's separate from the stamp. Or require an
  explicit `--skip-stamp` flag.

**S9 #3 — `scripts/tools/close_ticket.py` non-atomic write + rename.**
- File: `scripts/tools/close_ticket.py:296-301`
- Already covered in Concerns #2 above. Re-listed here because it's a real
  failure mode in practice (cross-mount renames, permission flips on
  archive/), and the recovery path leaves the user with a half-closed
  ticket that the script can no longer process.
- Fix: write the modified content to a tempfile in the same directory as
  `dest`, then `os.replace(tempfile, dest)`. Only after the replace
  succeeds, `ticket_path.unlink()`.

**S9 #4 — `scripts/tools/expand_carry_forward.py` end-of-finding bleeds
across session boundaries.**
- File: `scripts/tools/expand_carry_forward.py:388-405` (`_extract_findings`)
- See Concern #4 above. When the matched finding is the last numbered item
  in its session block, the extracted text includes everything up to the
  next finding head — which can be in a later session, after a session
  header, intro paragraph, scope section, and invariant violations section.
  The `[From: <file> — S<N>]` header at line 437-440 correctly identifies
  the source session of the START, but the displayed body misleadingly
  includes content from S<N+1> or later.
- Fix: in `_extract_findings`, change `end = next((hp for hp in
  head_positions if hp > start), len(content))` to also consider
  `_SESSION_HEAD` positions: build `boundary_positions = sorted(set(
  head_positions + [m.start() for m in _SESSION_HEAD.finditer(content)]))`
  and use that for the boundary search.

**S9 #5 — `scripts/tools/extract_carry_forwards.py` `current_sn` derived
from notes, not the live session.**
- File: `scripts/tools/extract_carry_forwards.py:54-65`
- See Concern #5 above. If this script is called mid-session by any
  workflow other than session-start (e.g. workflow-review), age computations
  are off by one because the "current" review header hasn't been written
  yet. The session-start path happens to work because the previous
  session's review IS the most recent. But the comment says "current"
  session which is misleading.
- Fix: either accept `--current-session` as an arg and let the caller
  pass the live session ID (from `current_session.py`), or rename to
  `_latest_review_session_number()` and document the semantics.

**S9 #6 — `scripts/tools/extract_carry_forwards.py` warning prints once
per call but doesn't surface in `extract_opus_key_sections.py` output.**
- File: `scripts/tools/extract_carry_forwards.py:58-63`
- The new warning ("session-reference pattern disabled") prints to stderr.
  When called from `extract_opus_key_sections.py` via `_cf_main` as a
  Python import (line 127 of that file), the warning still goes to stderr
  — but `extract_opus_key_sections.py` is typically captured for the
  session brief, and stderr is often dropped on the way to the user. The
  user will see the carry-forward list look empty without knowing why.
- Fix: print the warning to stdout when invoked via the brief path, or
  surface it as a note in the brief output itself.

## Test Gaps

Most S9 changes have tests in `tests/test_workspace_path_flags.py` (22 new
tests across 6 classes per the session log). The diff truncation prevents
verifying every test, but the named classes suggest reasonable coverage of
T042/T045/T046/T047/T048. Outstanding gaps from prior sessions are listed
as carry-forwards above (notably the T034 regression test from S8 #9 and
S8 #8 which T042 partially addressed).

One specific gap in S9 itself:

- **`close_ticket.py` `_replace_resolution` fallback path** — if the bug
  in S9 #1 is fixed by adding a permissive fallback, that fallback needs
  its own test (template with no Client-visible block, template with
  trailing blank-line variance).

- **`expand_carry_forward.py` session-boundary bleed** — the end-of-
  finding bug (S9 #4) needs a regression test with two consecutive
  reviews where the queried finding is the last item in the older review.

## Suggested Next Session Focus

1. **Fix `close_ticket.py` correctness bugs (S9 #1, #2, #3).** Non-atomic
   write+rename and over-strict regex will bite real workspace closures.
   Bundle all three into one small ticket — close_ticket.py is brand new,
   easier to harden now than after it's entrenched in muscle-memory.
   ~30 LoC + 3 tests.

2. **Fix `expand_carry_forward.py` session-boundary bleed (S9 #4).** This
   is the primary tool for surfacing carry-forward context — if the
   output mixes adjacent sessions, the carry-forward backlog tracking
   degrades. One-line fix + one parametrised test.

3. **Carry-forward backlog cleanup session.** The list is now 8 items
   (S8 findings #4, #5, #6, #9, #10, #11, #12, #13) — manageable in a
   single session. T044 (S1 #3 boundary check) and T043 (S3 #3 YAML loads)
   are already on the open list. Bundle the remaining S8 carry-forwards
   into one or two more tickets and clear them. Three sessions of carry-
   forward shrinkage in a row would be the first sustained backlog
   contraction in the project's history.
