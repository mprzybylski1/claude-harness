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
