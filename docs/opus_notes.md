# Opus Review — S28 2026-06-01 (static analysis, docs session)

**Session type:** docs-only — portfolio layer creation, app workspace scaffolding, idea research. No code changes.
**Static analysis:** 3/3 PASS — 35 test files compile cleanly, no `datetime.utcnow()`, all 9 CLAUDE.md bash blocks valid.
**Stale `.active_workspace` at close:** Found `scrabble-score` in `.active_workspace` at session-close time, blocking harness docs writes. Reset manually to `__harness__`. This is a recurring risk — a crashed or improperly-closed workspace session leaves stale state that blocks subsequent harness-root closes. Worth a low-priority ticket: session-start should set `.active_workspace` and session-close should reset it atomically, so stale state cannot persist across sessions.

---

# Opus Review — S26 2026-05-31

Scope: cleared the full S25 Opus backlog and both spin-outs — closed T142/T143/T140/T144/T145,
verified+deferred T141, opened T146. Net: `run_hook.sh` keeps its default fail-OPEN but gains
an explicit `FAIL_CLOSED` allowlist (exactly `check_cross_layer_writes`) so a missing enforcement
script stderr-warns + exit-2-blocks (T142, directly answering S25 Concern #1); the cross-layer
hook drops its private `_read_session_state`/`_HARNESS_SENTINEL` and imports
`workspace_config.read_session_state` as the single source of truth, mapping import failure to
exit 2 (T143, S25 Concern #2); `create_ticket.py` bare invocation is now session-aware —
fail-closed for workspace/undeclared, with a new explicit `--harness` bypass for programmatic
callers (T140, Inv 3 extension); `close_ticket.py` gains `--append` to preserve work-authored
Resolution content (T144) and a clearer no-placeholder error (T145); T141's join-key premise was
verified and deferred under YAGNI (S25 Concern #3 retired). One impl-review fix updated Invariant
2's verification grep for the T143 refactor. ~894 insertions / 74 deletions; static analysis
clean (33 test files compile, no `datetime.utcnow()`, 9/9 SKILL bash blocks valid). A focused,
high-discipline session — every S25 concern was retired at its root, and the T142 narrowing
(3 hooks → 1) is backed by an explicit matcher-by-matcher deadlock analysis rather than a
blanket policy. One real defect in the new `--append` path (Concern #1 below) and a recurring
section-terminator pattern (Concern #2).

## Invariant Violations

None.

Per-invariant verification against the S26 diff:
- **Inv 1 (workspace↔harness session-number separation):** Holds. No S26 change touches the
  `--sessions` routing in `create_ticket.py`/`close_ticket.py` (T140 changed only *layer
  selection*, not the session-ID lookup). The `--harness` bypass question resolves cleanly:
  `_current_session(internal=None)` reads the **harness** `sessions.md`, so a `create_ticket
  --harness` invocation stamps a **harness** `S<N>` into a **harness** ticket — no cross-layer
  number leak even if the flag is misused from a workspace session.
- **Inv 2 (session-type declaration required):** Holds, and the verification grep was correctly
  updated this session to match the refactor. First grep (`read_session_state|STATE_UNDECLARED`):
  diff confirms the hook imports `workspace_config as _wc`, re-exports `STATE_UNDECLARED`/
  `STATE_HARNESS`/`STATE_WORKSPACE` from it (lines 86-88), and calls `_wc.read_session_state(ROOT)`
  at the decision point (replacing the deleted private `_read_session_state`). Second grep
  (`_HARNESS_PROTECTED|sys\.exit`): `_HARNESS_PROTECTED` list is intact; `sys.exit(2)` now also
  guards the import-failure path (line 84), in addition to the unchanged undeclared/mismatch
  blocking paths (`main()` body below line 125 is untouched). The matcher is still `Edit|Write`
  (settings.json unchanged this session). The S25 Concern #2 silent-divergence risk is closed:
  one reader, with a test (`test_hook_has_no_private_tri_state_reader`) asserting the private copy
  and `_HARNESS_SENTINEL` are gone.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** Holds. The verification grep's two
  named tools (`raise_for_harness.py`, `close_ticket.py`) are untouched by S26 in their boundary
  exits, and `close_ticket.py`'s new `_append_resolution` adds *more* exit-2 sites (no
  Resolution header → exit 2; empty/placeholder-only section under `--append` → exit 2). T140
  extends the same principle to a new surface: `create_ticket._resolve_bare_layer` exits 2 for
  both `STATE_WORKSPACE` (refuse to create a harness ticket from a workspace session) and
  `STATE_UNDECLARED`, returning the harness layer only for an explicit `STATE_HARNESS` — a
  correct, idiomatic application of fail-closed-on-ambiguity that mirrors T136's
  `generate_ticket_index`.
- **Inv 4 (workspace isolation):** Holds. The `_workspace_internal_slug` / "may not write to
  other workspace" logic in `check_cross_layer_writes.py` is unchanged by the T143 refactor (the
  diff touches only the tri-state *reader* extraction and the import-failure guard, not the
  cross-workspace block). The run_hook.sh `FAIL_CLOSED` allowlist now makes a missing
  `check_cross_layer_writes` script fail closed, *strengthening* this invariant's enforcement
  relative to S25 (the S25 Concern #1 defense-in-depth gap).

## Fail-closed direction audit (priority-2 check)

Both new fail-closed directions are exit 2 (block), not exit 1 (non-blocking), which is the
correct and load-bearing distinction:
- `run_hook.sh`: missing FAIL_CLOSED script → `exit 2` (lines 173-178). The `case
  "$FAIL_CLOSED" in *" $name "*` match is space-padded on both the list (`" check_cross_layer_writes "`)
  and the pattern, so a hook named e.g. `check_cross` cannot substring-collide into the list.
  Confirmed correct.
- `check_cross_layer_writes.py`: import failure → `sys.exit(2)` with a recovery-pointing stderr
  message (lines 78-84). The in-code comment correctly states the rationale: Claude Code treats
  exit 2 as a block but *any other* non-zero (an uncaught `ImportError` → exit 1) as non-blocking
  → the tool proceeds → fail OPEN. The `except Exception` → exit 2 maps that correctly. Confirmed.
- T142 narrowing (3 → 1 hooks) is sound: `check_ticket_acs` matches `Edit|Write|Bash`, so
  fail-closing it would block every recovery surface (the SR-011/T138 deadlock class).
  `check_cross_layer_writes` matches `Edit|Write` only, leaving Bash (`git checkout`) as a
  recovery surface. Both fail-closed sites point the operator at that Bash recovery in stderr.

## `--harness` bypass audit (priority-2 check)

The `--harness` flag is an unconditional bypass of the session-state check (sets `internal = None`,
the harness layer). It does **not** open a separation hole in the Invariant sense: stamping is
correct (harness `S<N>` into a harness ticket, per Inv 1 above), and the flag is an explicit,
non-default override — the *bare* path fails closed, so nothing silently routes a workspace
session's ticket to harness. The residual gap is policy-vs-mechanism, not invariant: because
`create_ticket` writes via plain `open()` (not Edit/Write), the PreToolUse cross-layer hook cannot
catch a misused `--harness`, so the *only* guard against a workspace session doing harness ticket
work is "don't pass the flag." That is acceptable for a programmatic-caller escape hatch
(`promote_raised_concern.py` is the sole intended user and always creates harness tickets), but it
is an unguarded surface — see Concern #3.

## Architectural Concerns

1. **`scripts/tools/close_ticket.py` `_append_resolution` (~L146-185, per diff hunk `@@ -143`;
   exact source line not verifiable without reading the file) — its "nothing to preserve" guard
   misses the real fresh-ticket shape; `--append` on a fresh ticket leaves the
   `(Fill in on close.)` placeholder in the closed ticket.** [Low impact (audit smudge,
   opt-in), but a confirmed correctness bug with a test that masks it] The guard is
   `if not body or re.fullmatch(r"\(Fill in on close[^)]*\)", body)`. But a *fresh* ticket's
   Resolution body is not the bare placeholder — per the embedded template (context lines
   1170-1175) it is the `> **Client-visible:**` blockquote *followed by* the placeholder.
   `body = section.strip()` therefore starts with `>`, so `re.fullmatch` against the
   `(Fill in...)` pattern returns `None`, `body` is non-empty, and the guard **does not fire**.
   `--append` then preserves the blockquote+placeholder and appends the summary after it,
   producing a closed ticket that still contains `(Fill in on close.)`. The asymmetry is the
   tell: replace-mode's `strict` regex explicitly accounts for the optional client-visible block
   (`(?:> \*\*Client-visible:\*\*.*?\n(?:> .*\n)*\n)?`), but the append guard does not. **Test
   gap (priority-4):** `test_append_errors_when_only_placeholder` uses `_ticket("(Fill in on
   close.)")` — a bare placeholder with no blockquote — so it passes while never exercising the
   shape a real ticket has. The new safety-relevant path has false-confidence coverage.
   Recommendation: reuse the same optional-blockquote-aware pattern as `strict` when deciding
   whether the section is "only the placeholder", and add a test whose Resolution body is the
   full template shape (blockquote + placeholder) under `--append`.

2. **`scripts/tools/close_ticket.py` `_resolution_section` (~L146-160, per diff hunk `@@ -143`;
   exact source line not verifiable without reading the file) — its `\n##\s` terminator is the
   same fenced-code false-terminator pattern Opus flagged in S23 Concern #2.** [Low impact,
   latent] `nxt = re.search(r"\n##\s", after)` treats the first `## ` at line start as the end of
   the Resolution section. A `## ` inside a fenced code block in the Resolution body — a commit
   message snippet, a diff hunk header is `@@` not `##` so that's safe, but a markdown sample or
   a shell heredoc with `## ` would trip it — truncates the section there, so the append lands
   before the fence and any real content after it gets shoved past the (mis-detected) section
   boundary. This is mitigated because Resolution is usually the last `##` section (`nxt` is then
   `None` and the whole tail is the section), so the bug only bites when a later `##` section
   exists *and* the Resolution body contains a fenced `## `. S23 Concern #2 flagged the identical
   shape in `_extract_active_work_section` (terminating at `\n---` inside a fence); this is a
   recurring section-parsing pattern in the same codebase. Recommendation: low priority given the
   last-section mitigation, but worth a fence-aware scan or at least a code comment naming the
   assumption, so the next section-parser author doesn't copy the pattern a third time.

3. **`scripts/tools/create_ticket.py` `main()` layer-selection branch + `_resolve_bare_layer`
   (per diff hunk `@@ -159` / `@@ -101`; exact source line not verifiable without reading the
   file) — `--harness` is an unguarded mechanism bypass; only
   `promote_raised_concern.py` is the intended caller.** [Low impact, policy-vs-mechanism] Covered
   in the bypass audit above. The flag is correct for its programmatic purpose and the bare-path
   fail-closed default is the right design, but there is no mechanism stopping an interactive
   workspace session from typing `create_ticket --harness` and writing a harness ticket (the
   `open()`-based write is invisible to the Edit/Write hook). Recommendation: no code change
   required this session — the explicit-flag-only surface is an acceptable escape hatch — but if a
   future session wants belt-and-suspenders, `--harness` could additionally assert
   `read_session_state(ROOT) != STATE_WORKSPACE` (allowing harness + undeclared, since the
   programmatic caller may run before declaration) and exit 2 otherwise. Flagging so the bypass is
   a recorded decision, not an unexamined hole.

## Cross-change interaction check (priority-5)

The five tickets touched four shared files; no seams left:
- `workspace_config.py` (T143) ↔ `check_cross_layer_writes.py` (T143): the hook now imports the
  reader the comment promised in S25; `workspace_config.py`'s deferred-debt note was replaced with
  a single-source statement. The two authorities (attribution + enforcement) now share one reader —
  the S25 Concern #2 divergence risk is closed at the source, not merely documented.
- `create_ticket.py` (T140) ↔ `promote_raised_concern.py` (T140): the promoter passes `--harness`
  so it keeps working under the new fail-closed bare default. This is necessary and correct — without
  it, promotion (a harness-layer operation often run mid-session before/independent of state) would
  have started exit-2'ing. Verified the promoter is the one caller updated.
- `run_hook.sh` (T142) ↔ `check_cross_layer_writes.py` (T143): T142 makes the *missing-script* case
  of this specific hook fail closed; T143 makes the *broken-import* case fail closed. The two cover
  complementary failure modes of the same enforcer — no overlap, no gap between them.

## Suggested Next Session Focus

1. **Fix the `_append_resolution` fresh-ticket guard and its masking test (Concern #1).** ~3 LoC +
   1 test. Make the empty/placeholder-only check blockquote-aware (reuse `strict`'s optional
   client-visible pattern) and add a test whose Resolution body is the full template shape under
   `--append`. This is the only confirmed defect and it silently degrades the audit trail (closed
   tickets retaining `(Fill in on close.)`).

2. **Add a fence-aware comment or scan to `_resolution_section` (Concern #2).** ~2 LoC comment now,
   or a small fence-skip later. Cheap insurance against the third recurrence of the section-terminator
   pattern S23 already flagged once.

3. **Record the `--harness` bypass decision (Concern #3).** Either add the
   `read_session_state != STATE_WORKSPACE` assertion, or leave a one-line code comment stating that
   `--harness` is a deliberate unguarded escape hatch for programmatic callers. Lowest priority —
   it's a documentation/decision item, not a fix.

No multi-session carry-forwards: all three S25 concerns were retired this session (Concern #1 → T142,
Concern #2 → T143, Concern #3 → T141 verify-and-defer). All three S26 items are net-new from this
session's diff, and two of the three are Low impact.
