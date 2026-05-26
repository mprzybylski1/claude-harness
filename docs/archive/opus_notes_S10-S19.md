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


