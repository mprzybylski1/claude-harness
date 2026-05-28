# Opus Review Notes — Archive S10–S19

Archived from `docs/opus_notes.md`. All findings are either fixed or tracked in `docs/tickets/`.
Use `grep` to search. Do not load into session context.

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

---

# Opus Review — S11 2026-05-26

Scope: closed T054 only (close_ticket.py remaining correctness — S9 #1
strict-regex fallback, S9 #2 stamp-regex over-match, S10 #1 atomic-move
via os.replace, S10 #5 _docs_paths silent parse failure). ~157 insertions
/ 12 deletions in 2 files. Smallest session in recent history but high
correctness density — all four items in one tight ticket plus an
undocumented bonus fix for a pre-existing re.sub injection bug.

S10 inline-fix status check: Concerns #2 (S9 #1 strict-resolution) closed
by T054 permissive fallback. Concern #3 (S9 #2 stamp regex) closed by
T054 tightening to `\bClosed\s+S\d+\s+\d{4}-\d{2}-\d{2}`. Concern #5
(_docs_paths silent on parse failure) closed by T054 try/except + WARNING.
Concern #1 (atomic-move BOTH-locations) PARTIALLY closed — see #1 below.
Concerns #4, #6, #7 (semi-actionable), #8, #9 (policy-closed), #10
(addressed in S10 inline), #11 still carry forward.

## Invariant Violations

None new. Invariant 5 (workspace isolation) unaffected — `_docs_paths`
change only affects the parse-failure error path within a single workspace
directory. `_atomic_move` operates inside one workspace's archive dir.
Invariants 1–4 remain placeholders.

## Architectural Concerns

1. **`scripts/tools/close_ticket.py:175-189` — "atomic" move still leaves
   ticket in BOTH locations if `ticket_path.unlink()` fails.** [Partial
   fix of S10 #1, S9 #3] T054 correctly closes the partial-write window:
   `tmp.write_text` + `os.replace(tmp, dest)` guarantees `dest` is never
   half-written. BUT the BOTH-locations failure mode flagged by S10 #1
   remains: if `os.replace` succeeds and then `ticket_path.unlink()`
   raises (permission, filesystem error, race), the file exists in BOTH
   `tickets/open/` (with closure frontmatter already applied via
   `_update_frontmatter` and resolution placeholder already gone via
   `_replace_resolution`) AND `archive/`. The next `close_ticket.py` run
   on the same ID will hit the "already exists in archive" guard at
   line 263-265 and exit 2 — user is stuck. The test
   `test_atomic_move_archive_clean_if_unlink_fails` verifies dest exists
   with correct content after unlink failure, but the asymmetric outcome
   (dest written, source remains) is not flagged as a problem. Fix:
   wrap `ticket_path.unlink()` in try/except; on failure, log a clear
   recovery instruction ("manually `rm tickets/open/<file>` — archive
   copy at <dest> is correct"). Alternative: roll back by removing
   `dest` if unlink fails (loses atomic guarantee but matches S9's
   original "ticket in exactly one location" intent).

2. **`scripts/tools/close_ticket.py:248` — stamp regex still false-positives
   on legitimate non-stamp text containing "Closed S<N> YYYY-MM-DD".**
   [Narrowed bug from S9 #2] The new regex `\bClosed\s+S\d+\s+\d{4}-\d{2}-\d{2}`
   is much tighter than the old `\bS\d+\b.*\d{4}-\d{2}-\d{2}`, but
   resolutions like "Originally closed S5 2026-01-01 but reopened in S7
   when..." or "Closed S5 2026-01-01 was a mistake — reverted in S6"
   will still suppress the auto-stamp. The check is now narrow enough
   that the trigger phrase is unusual prose, but it is not impossible.
   Fix considered (and rejected by T054): always append the stamp,
   forcing the user to manually elide history mentions. Probably
   acceptable as-is — but worth a one-line comment at line 247-249
   documenting the trade-off so future maintainers don't widen the
   regex again.

3. **`scripts/tools/close_ticket.py:182` — tempfile name is deterministic
   and collides across concurrent runs or with stale `.tmp` files.**
   [Concern] `tmp = dest.parent / (dest.name + ".tmp")` produces e.g.
   `archive/T054-foo.md.tmp`. If a previous run crashed mid-write and
   left `T054-foo.md.tmp` behind, a new run will silently overwrite it
   (probably fine). Two concurrent runs of `close_ticket.py T054` would
   race on the tmp file. The second `os.replace(tmp, dest)` would either
   succeed (overwriting the dest from the first run) or fail. Practical
   risk: low (no concurrent invocation in the workflow today). Fix if
   tightening: use `tempfile.NamedTemporaryFile(dir=dest.parent,
   delete=False)` for a unique name, or include `os.getpid()` in the
   suffix.

4. **`scripts/tools/close_ticket.py:34` — `_ws_internal_dir` import alias
   is unused.** [Minor] `from workspace_config import load_workspace,
   internal_dir as _ws_internal_dir` imports `internal_dir` under an
   alias that has no callers anywhere in the module. Dead import.
   Pre-existing from S10 (T051) but trivially removable as part of the
   next close_ticket touch. `grep _ws_internal_dir` in the file returns
   only the import line.

5. **`scripts/tools/close_ticket.py:129-172` — re.sub injection fix
   landed without a test.** [Test gap] The T054 resolution mentions
   "fixed a pre-existing re.sub injection bug in _replace_resolution
   where backslashes in resolution text were misinterpreted as regex
   escapes (switched to lambda replacement)". The strict-path fix
   `strict.sub(lambda m: m.group(1) + repl, content)` is correct, but
   none of the seven new tests pass a resolution containing `\g<1>`,
   `\1`, or other regex metacharacters. A regression that reverts to
   the string form would not be caught. Add a single test:
   `_replace_resolution(content, r"Resolved by patching \g<1> placeholder")`
   and assert the literal text survives.

6. **`tests/test_workspace_path_flags.py:781-788` — permissive-fallback
   test does not verify pre-placeholder text is preserved.** [Test gap]
   The test asserts `"Fixed via fallback." in result` and
   `"(Fill in on close." not in result`, but does NOT assert that
   `"Note: see T052 for background."` (the pre-placeholder text) is
   preserved in the output. The current implementation does preserve it
   — but a future "simplification" that nukes the whole Resolution
   section would still pass the test. One-line addition:
   `assert "Note: see T052 for background." in result`.

7. **`tests/test_workspace_path_flags.py:849-852` — monkeypatch on
   `Path.unlink` is global and matches by `parent == open_dir` only.**
   [Test fragility] The test monkeypatches `Path.unlink` globally for
   the test, intercepting on `self_path.parent == open_dir`. If
   `_atomic_move`'s implementation ever changes to call `unlink` on
   the tmp file in the success path (e.g. cleanup of a leftover .tmp),
   the test would still pass — but if it called `unlink` on `dest` to
   roll back, the test would silently miss it. Tightening: assert
   `ticket_path.exists()` after the failed `_atomic_move` returns,
   confirming the source file is still there (and proving the
   BOTH-locations concern #1 above).

8. **`scripts/tools/extract_carry_forwards.py` — S9 #6 warning swallowed
   in brief output.** [Carry-forward from S9 #6 / S10 #4 — 2 sessions
   unaddressed] T055 tracks this in the open ticket queue. Still not
   addressed; user sees an empty carry-forward list with no signal
   when the session-reference pattern is disabled.

9. **`scripts/hooks/log_tool_usage.py` bootstrap-failure rate-limit.**
   [Carry-forward from S8 #4 / S9 #8 / S10 #8 — 3 sessions unaddressed]
   Read-only `.git/` causes every tool call to append to
   `.git/session_tool_log.errors` without rate-limiting. Not actionable
   yet (no reported case) but the carry-forward count is climbing.

10. **`scripts/tools/surface_stale_tickets.py` — `*(none)*` literal
    duplicated across files.** [Carry-forward from S10 #11 — 1 session
    unaddressed] T056 tracks this. Trivial fix when picked up.

11. **`scripts/hooks/regenerate_ticket_index.py:_get_docs_path_map` cache
    never invalidated.** [Carry-forward from S10 #6 — 1 session
    unaddressed] Not actionable today (hook is short-lived per
    invocation) but flagged for future daemon variants.

## Suggested Next Session Focus

1. **Close the close_ticket.py "BOTH-locations" tail (Concern #1 above).**
   The S10 #1 bug is now narrower — partial-write window is gone — but
   the asymmetric `os.replace` succeeded / `unlink` failed → ticket in
   both places scenario remains. Add a try/except around
   `ticket_path.unlink()` at line 189; on failure emit an actionable
   recovery message and exit non-zero so the user knows to clean up.
   Add a test that monkeypatches unlink to fail and asserts the script
   exits with a message containing the source path. ~10 LoC + 1 test.

2. **Close T055 (carry-forward warning surface in brief).** Now 3
   sessions unaddressed. T055 is open with a clear scope: either
   re-route the stderr warning through the brief composer or include
   it as a "Note:" line in the brief output. ~5 LoC + 1 test.
   File: `scripts/tools/extract_opus_key_sections.py:124-128`.

3. **Add the missing tests for T054 (Concerns #5 and #6 above).**
   The re.sub injection fix and the permissive-fallback content
   preservation both lack regression tests. Two ~3-line additions to
   `tests/test_workspace_path_flags.py::TestCloseTicketT054`. Bundling
   into a single follow-up commit on close_ticket.py would be cheaper
   than opening a ticket.

Opus carry-forwards (>= 2 sessions):
S8 #4 / S9 #8 / S10 #8: log_tool_usage.py bootstrap-failure rate-limit (3 sessions)
S9 #6 / S10 #4: extract_carry_forwards warning swallowed in brief output — tracked as T055 (2 sessions)

---

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

---

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


