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

---

# Opus Review — S10 2026-05-26

Scope: closed T043 (YAML load cache in regenerate_ticket_index), T049
(settings.json dynamic hook paths), T051 (close_ticket.py correctness — S9
#1/#2/#3), T052 (expand_carry_forward session-boundary bleed — S9 #4),
T053 (S9 carry-forward backlog: #5/#6 docstring + structural header, #9
lexical Path.parts, #10 invariants label, #12 repr() paths, #13 T026
forward-note, #14 grouping comment, #15 utcnow grep exclude). Plus four
impl-review hardening fixes during the session. ~526 insertions / 84
deletions across 19 files. Net carry-forward shrinkage for the fourth
straight session — first sustained contraction in project history.

S9 inline-fix status check: Concerns #2 (atomic write), #3 (duplicate
ticket disambiguation), #4 (session-boundary bleed), #6 (aging section
header), #9 (Path.resolve → Path.parts), #10 (invariants label), #12
(subprocess f-strings), #13 (T026 framing), #14 (defaultdict comment),
#15 (utcnow false positive) all closed. Concern #1 (YAML loader vs regex)
closed via T051's import of `load_workspace`. Concerns #5 (mid-session
semantic) addressed via docstring only — no `--current-session` flag.
Concerns #7, #8, #11 still carry forward, plus the never-addressed S9
Bugs #1, #2, #6 (see below).

## Invariant Violations

None new. Invariant 5 (workspace isolation) is unchanged. The new
`_get_docs_path_map` cache in `regenerate_ticket_index.py` walks
`workspaces_base()` — but each entry only resolves to its own workspace
internal/docs path, so cross-workspace leakage is not introduced. The
cache is keyed by `str(docs / "tickets")` so an attacker-controlled
docs_path could in principle alias another workspace's tickets dir, but
that's a pre-existing concern not introduced by S10.

## Architectural Concerns

1. **`scripts/tools/close_ticket.py:267-269` — "atomic" fix is still not
   atomic; can leave the ticket in BOTH locations.** [Bug, partial fix
   of S9 #2/#3] The S10 change reorders write-then-delete to
   `dest.write_text(content); ticket_path.unlink()`. This DOES fix the
   originally-reported failure mode (write to dest fails → open/ ticket
   untouched, verified by `test_write_to_dest_before_unlink`). But if
   `dest.write_text` succeeds and `ticket_path.unlink()` then fails
   (permission, filesystem error, race), the file now exists in BOTH
   `tickets/open/` (with closure frontmatter already applied) AND
   `archive/`. Next `close_ticket.py` run on the same ID will hit the
   "already exists in archive" guard at line 261-263 and exit 2. S9's
   suggested fix was explicit: `os.replace(tempfile, dest)` of a same-
   directory tempfile, then `unlink`. Current code is better than the
   original `write+rename` but does not match the suggested atomic
   approach. Diff suggests the unlink failure mode is unhandled — no
   try/except surrounds it. Confirmed: lines 267-269 in the diff show
   `dest.write_text(...); ticket_path.unlink()` with no rollback path.

2. **`scripts/tools/close_ticket.py` — S9 #1 (`_replace_resolution` too
   strict) NOT addressed.** [Carry-forward from S9 #1 — 1 session
   unaddressed] T051's session log lists fixes for #1/#2/#3 but the
   diff only shows fixes for the YAML loader (Concern #1), atomic-write
   reorder (Bug #2/Concern #3), and `--workspace` disambiguation (Bug
   #3/Concern #3). The strict-regex resolution-placeholder fallback
   recommended by S9 #1 (split into strict + permissive passes, warn on
   fallback) does not appear in the diff. The original bug — exit 2
   with "ticket format unexpected" leaving the user stuck after AC
   validation passed — remains. Diff suggests no fix; confirmed by
   absence of `_replace_resolution` changes in the priority-ordered diff.

3. **`scripts/tools/close_ticket.py` — S9 #2 (session-stamp regex
   over-matches) NOT addressed.** [Carry-forward from S9 #2 — 1 session
   unaddressed] The check `re.search(r"\bS\d+\b.*\d{4}-\d{2}-\d{2}",
   resolution)` still false-positives on any resolution mentioning a
   historical session ("Reverted the S5 2026-01-01 commit") and
   suppresses the closure stamp. S10's session log claims #2 is closed
   under T051 but the diff change credited to "#2" is the write-dest-
   first reorder — which is actually S9 #3 (non-atomic write+rename).
   The labels were shuffled: S10 closed S9 Concern #2 (the write-rename
   atomicity) but did NOT close S9 Bug #2 (the stamp regex). Easy mix-up
   given that both "S9 #2" labels exist. Diff suggests no stamp-regex
   change; confirmed by absence of `re.search.*S\\d.*\\d{4}` modification
   in the diff.

4. **`scripts/tools/extract_carry_forwards.py` — S9 #6 (warning swallowed
   in brief output) NOT addressed.** [Carry-forward from S9 #6 — 1
   session unaddressed] T053's resolution mentions #5 (docstring) but
   not #6. The warning still prints to stderr; when called from
   `extract_opus_key_sections.py` via Python import, the brief
   capture-path still drops it. User sees an empty carry-forward list
   and doesn't know why. Diff suggests only the docstring change at
   line 296-306, no stdout redirect or brief surface change.

5. **`scripts/tools/close_ticket.py:243` — `_docs_paths` now imports the
   YAML loader at module level but error handling is silent.** [Concern]
   `load_workspace(ws_dir)` returns `None` on read/parse failure (per
   the existing fail-closed pattern? — diff doesn't show the loader
   body, but the caller does `if not cfg or not cfg.get("docs_path"):
   return []`). A workspace with a corrupted workspace.yaml will be
   silently treated as having no docs_path, and the ticket search will
   fall back to `internal/tickets/open/`. If the user has a docs_path
   ticket that's now invisible, they get a "not found" error with no
   indication that one of the workspaces failed to parse. Either log a
   warning when `load_workspace` returns None despite the file existing,
   or surface the parse failure as a hard error. Diff suggests the
   silent-None branch; confirmed by `if not cfg or not cfg.get(...)`
   pattern at the change site.

6. **`scripts/hooks/regenerate_ticket_index.py:_get_docs_path_map` cache
   never invalidated for the life of the process.** [Concern] The
   module-level `_docs_path_cache` is populated once and reused. If a
   long-running hook process (or a future daemonized variant) sees a
   workspace's `workspace.yaml` change at runtime — adding/removing a
   docs_path — the cache won't reflect it. Today the hook runs once per
   tool invocation so this is moot, but the cache comment promises
   "once per process" which depends on the hook being short-lived. Add
   a TTL or stat-based invalidation if the hook is ever made persistent.
   Not actionable today; flag for future.

7. **`scripts/hooks/regenerate_ticket_index.py:81-83` — `try/except
   Exception: pass` in `_get_docs_path_map` swallows everything.**
   [Concern] The cache-build helper catches `Exception` and returns an
   empty map. The intent (per the impl-review test) is that the cache
   is not poisoned on transient failure. Good. But this also masks
   programming errors — e.g. a typo in `_internal_dir` that raises
   `AttributeError` will look like "no workspaces configured" forever
   in this process. At minimum, log the exception to stderr before
   `pass`. Diff suggests bare `pass`; confirmed at the change site.

8. **`scripts/hooks/log_tool_usage.py` bootstrap-failure rate-limit.**
   [Carry-forward from S8 Finding #4 / S9 Concern #8 — 2 sessions
   unaddressed] Still no rate-limit on `_log_error` writes to
   `.git/session_tool_log.errors`. Not actionable yet; preserved.

9. **`scripts/tools/extract_carry_forwards.py` mid-session semantic
   only documented, not fixed.** [Carry-forward from S9 #5 — 1 session
   unaddressed] T053's resolution updated the docstring (good — verified
   in the diff at lines 296-306). But the call site in
   `extract_opus_key_sections.py` still computes "current" from the
   notes file's last header rather than the live session. If
   workflow-review or a future mid-session caller relies on this, ages
   will be off by one. The docstring now says this is "intentional —
   designed for session-start archaeology" so consider this closed by
   policy rather than fixed; flagging to confirm the policy decision.

10. **Test for `_get_docs_path_map` cache uses `importlib.reload(rti)`
    inside an `autouse` fixture.** [Concern] `tests/test_hooks_workspace_scoping.py:407-413`
    reloads `regenerate_ticket_index` before each test in the class to
    reset module state. This works but is fragile: reload re-runs
    module-level imports, which means any side-effect at import time
    (e.g. log file creation, env-var reads) happens twice per test.
    Cleaner approach: explicitly assign `rti._docs_path_cache = None`
    in setup, no reload. Diff suggests `importlib.reload(rti)` at
    line 413; confirmed.

11. **`scripts/tools/surface_stale_tickets.py` couples to the literal
    `*(none)*` string emitted by `generate_ticket_index.py`.** [Concern]
    T053 #6's pair of changes: generator always emits header and writes
    `*(none)*` body when empty; consumer regex-matches `^\*\(none\)\*`
    as clean-state signal. This is fine today but the marker string is
    duplicated across two files with no shared constant. A maintainer
    who changes one and forgets the other will reintroduce the format-
    drift ambiguity. Fix: define `EMPTY_AGING_MARKER = "*(none)*"` in a
    shared module (e.g. `workspace_config.py`) and reference it from
    both. Minor.

## Suggested Next Session Focus

1. **Close out the remaining S9 close_ticket.py bugs (S9 #1 stub
   resolution; S9 #2 stamp regex; Concern #1 above — true atomic move
   via `os.replace` of same-directory tempfile).** Three correctness
   issues in the same brand-new file. The session log claims S9 #1/#2/#3
   are all closed under T051 but the diff only confirms #3 (and that
   one is "better, not atomic"). One small ticket, ~20-30 LoC + 3
   tests. File: `scripts/tools/close_ticket.py`.

2. **Surface the carry-forward warning to brief output (S9 #6).** When
   `extract_carry_forwards.py` disables its session-reference pattern,
   the user must see why. Either reroute the warning through the brief
   composer or include it as a `Note:` line in the brief output itself.
   File: `scripts/tools/extract_carry_forwards.py:58-63` and
   `scripts/tools/extract_opus_key_sections.py` (the consumer).

3. **Decide and document the close_ticket "session log honesty"
   policy.** The S10 session log entry claims fixes for #1, #2, #3
   under T051, but only #3 is actually fixed. This is the second time
   in recent history (S8 also had similar slippage on T035's claim to
   close S7 C#6) that a session log overstates closure scope. Either
   adopt a check that verifies the diff matches the resolution claims
   before commit, or have session-close reviewer (Opus) validate
   resolution claims against the actual diff. Not file-specific —
   process change.
