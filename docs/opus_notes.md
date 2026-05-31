# Opus Review — S27 2026-05-31

Scope: promoted SR-012/SR-013 → closed T147 (`close_ticket.py --commit`) and T148
(`create_ticket.py --problem`); impl-review added an index-clean guard + fail-closed
`_apply_problem`; `/simplify` deduplicated test boilerplate into a new `tests/conftest.py`
(net –226 test lines). The feature surface is small and well-factored: `--commit` runs
`git commit` after staging, refusing (exit 2) on multi-root spans and on an index that
holds staged changes beyond what close_ticket staged; `--problem` fills the `## Problem`
placeholder, failing closed (exit 1) if the placeholder is absent. The helper extraction
(`_ac_section_bounds`, `_resolution_section` reuse, `_rel`, module-level `defaultdict`) is
clean. One real test gap on the headline feature (Concern #1); everything else holds.

## Invariant Violations

None.

Per-invariant verification against the S27 diff:
- **Inv 1 (workspace↔harness session-number separation):** Holds. The one new write
  surface is `commit_msg = f"{prefix} {title}"` (close_ticket.py:858) — `prefix` is
  `fix(T###):`/`docs(T###):` from `_commit_prefix`, `title` is the ticket frontmatter
  title; no session ID is embedded, so `--commit` cannot leak an `S<N>` into a commit
  message. `--sessions` routing is untouched. `create_ticket --problem` only substitutes
  body text and does not touch the session-ID lookup.
- **Inv 2 (session-type declaration required):** Holds, unchanged. No S27 change touches
  `.claude/settings.json`, `check_cross_layer_writes.py`, or `workspace_config.read_session_state`.
  Note: both new write paths bypass the Edit/Write hook because they write via `os.replace`
  / `git`, but that is the pre-existing tool-write model (same as every other close/create
  operation) — not a regression introduced this session.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** Holds, and *strengthened*. The
  new `_refuse_multi_root_commit` (close_ticket.py:174) exits 2 when staged paths span >1
  git root before any commit — a direct extension of the T125 cross-repo case the invariant
  names. `_check_index_clean` (close_ticket.py:188) adds a further exit-2 site: a bare `git
  commit` would fold any pre-existing staged change into the ticket commit, so it refuses
  unless the index contains only the paths close_ticket staged. `git status` failure /
  non-zero also exits 2 (no silent proceed). `create_ticket._apply_problem` exits 1 — not 2 —
  when the placeholder is missing; correct, since create_ticket is not a tracked-audit-state
  write at that point and exit 1 simply aborts the create.
- **Inv 4 (workspace isolation):** Holds, unchanged. No diff touch to `_workspace_internal_slug`
  or `assert_workspace_boundary`. The multi-root refusal incidentally reinforces it: a close
  whose staged set spans a workspace repo and the harness repo cannot be auto-committed.

## Architectural Concerns

1. **`--commit` — the session's headline feature — has zero end-to-end test coverage.**
   [Medium impact, test gap on a new git-mutating path] `tests/test_close_ticket_commit.py`
   is entirely mocked unit tests of the helpers in isolation: `_commit_prefix` (pure),
   `_collect_staged_roots` (patches `_git_root_for`), `_refuse_multi_root_commit` (called
   directly), `_check_index_clean` (patches `subprocess.run` with canned porcelain). Nothing
   in the suite invokes `close_ticket.py --commit` against a real temp repo. sessions.md
   records that the refactor *deleted* `TestCommitMainPath` as "tested mocks" — so the
   `main()` composition (close_ticket.py:868-881) that wires `_collect_staged_roots` →
   `_refuse_multi_root_commit` → `_check_index_clean` → real `git commit` and prints
   `Committed:` is now untested. `grep -rn -- "--commit" tests/` returns only docstring
   lines. The guards are individually correct, but their integration in the commit path —
   the part that actually mutates HEAD — has no coverage, on the one feature this session
   shipped to do exactly that. The masking risk is concrete: a wiring bug (wrong `staged_paths`
   passed to `_check_index_clean`, `commit_msg` not threaded, `git -C git_root` root mismatch)
   would pass every existing test. Fix: one integration test using the new conftest helpers
   (`make_harness_tree` + `run_close_ticket(..., "--files", "x.py", "--commit")`) asserting
   `git rev-parse HEAD` advanced and `git log -1 --format=%s` equals `fix(T###): <title>`,
   plus a second asserting `--commit` with a pre-existing unrelated staged file exits non-zero
   and leaves HEAD unmoved. ~15 lines; the conftest scaffolding for it already exists.

## Notes (decisions, not defects)

- **SR-013 AC#3 vs. implementation — `--problem --ac` is not fully "close-ready."** SR-013
  AC#3 reads "a single create invocation produces a close-ready ticket (no unchecked-AC ...
  residue)." The implementation (and `test_close_ticket_commit`'s own docstring) deliberately
  leaves `- [ ]` boxes unchecked — "criteria to verify, not auto-ticked." So a
  `create --problem --ac` ticket still needs `--tick-acs`/`--force` at close. This is the
  correct call (auto-ticking ACs at create time would defeat the AC gate), but it diverges
  from the AC's literal wording. Recording as a decision so it isn't re-litigated, not a bug.
- **No carry-forwards.** All three S26 concerns were retired during S26 close, before the
  S27 baseline (3c42a45): Concern #1 (`--append` fresh-ticket guard) fixed in `42e7512`;
  Concern #2 (`\n##\s` non-fence-aware terminator) commented in `3bc8169`; Concern #3
  (`--harness` bypass) was a recorded decision. The live `close_ticket.py` still contains
  `_resolution_section` with the `\n##\s` terminator and the append guard, but both are
  addressed — not open.

## Suggested Next Session Focus

1. **Add end-to-end `--commit` coverage (Concern #1).** Two integration tests via the new
   conftest helpers: (a) `--files x.py --commit` advances HEAD with `fix(T###): <title>`;
   (b) `--commit` with an unrelated staged file exits 2 and leaves HEAD unmoved. ~15 LoC.
   This is the only Medium finding and it closes a coverage hole on the session's one
   git-mutating feature.
2. **Pick up a deferred ticket** — T141 (telemetry↔transcript join, deferred under YAGNI
   since S25) or T146 (cwd-drift fragility in `python scripts/tools/X.py` invocations).
   T146 sits closest to the harness trust boundary that recent sessions have been hardening.

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
