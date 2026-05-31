# Opus Review — S25 2026-05-31

Scope: closed T135/T136/T137/T138/T139 — the full scrabble-score SR-008/009/010/011
workspace-blind-tooling sweep. Net: telemetry attribution rewritten from per-file-path
(T057) to active-session via `workspace_config.read_session_state` + a new
`claude_session_uuid` live join key (T137); `analyze_tool_log` gains a `(workspace,
session)` pair filter with gated auto-detect (T137); `create_ticket._next_id` scoped
per-layer (T135); `generate_ticket_index` fail-closes on bare workspace/undeclared
invocation (T136); new `run_hook.sh` wrapper resolves hook paths cwd-independently via
`$CLAUDE_PROJECT_DIR` + `$0` (T138); `raise_for_harness --session` bypasses the
last-logged+1 off-by-one during close (T139). ~1556 insertions / 547 deletions across
32 files; 477 tests pass (+22 net). Clean, well-documented sweep — every SR in the
batch landed, and the implementer left honest in-code notes on the residual skew and
the duplicated tri-state reader. Two spin-outs (T140/T141) correctly deferred.

## Invariant Violations

None.

Per-invariant verification against the S25 diff:
- **Inv 1 (workspace↔harness session-number separation):** grep #1 holds —
  `close_ticket.py:221` and `create_ticket.py:117` both route `--sessions
  <internal>/sessions.md`; `session_lookup.py:42-46` is the single consolidator that
  appends `--sessions PATH` only when given a workspace path. T135's `_next_id(internal)`
  rework keeps the per-layer counter (its docstring explicitly cites the
  `current_session.py --sessions` per-layer model). No harness `S<N>` is written into
  workspace state and vice versa in the diff.
- **Inv 2 (session-type declaration required):** grep #2 holds — the
  `check_cross_layer_writes` matcher is still registered on `Edit|Write`
  (settings.json:34), now dispatched through `run_hook.sh`. The hook body is unchanged:
  `_STATE_FILE`, `_HARNESS_PROTECTED`, `STATE_UNDECLARED` all present, `sys.exit(2)` at
  line 96 on the mismatch/undeclared path. The new T136 `workspace_config.read_session_state`
  reads the SAME `.claude/.active_workspace` tri-state (see Concern #2). Enforcement logic
  untouched — but its *invocation wrapper* changed; see Concern #1.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** grep #3 holds —
  `raise_for_harness.py:194` exits 2 on a malformed `--session` value (T139's new flag
  validates `S\d+` before stamping the tracked `raised:` field, so the explicit-value
  path can't smuggle garbage in), plus the pre-existing exits at 83/88. `close_ticket.py`
  retains its cross-repo guards (12 `sys.exit(2)` sites). T136's `generate_ticket_index`
  bare-invocation path also fail-closes (`sys.exit(2)`) for workspace/undeclared sessions
  rather than overwriting the harness INDEX — a new, correct application of this invariant.
- **Inv 4 (workspace isolation):** grep #4 holds — `check_cross_layer_writes.py:155`
  still blocks workspace-A→workspace-B `internal/` writes via `_workspace_internal_slug`.
  No diff change to the isolation logic; same wrapper caveat as Inv 2 (Concern #1).

Test suite: `477 passed` (ran with `--ignore=tests/test_workflow_orchestrator.py` per
the prompt).

## Architectural Concerns

1. **T138 inverted the enforcement hook's failure mode from fail-closed to fail-open
   — `scripts/hooks/run_hook.sh:31` + `.claude/settings.json:34`.** [Medium impact,
   defense-in-depth gap] T138 correctly fixed the SR-011 deadlock (cwd drifting into a
   workspace repo made `git rev-parse --show-toplevel` resolve to a repo with no harness
   hooks → `python3: can't open file` → exit 2 → every tool blocked). The fix —
   `$CLAUDE_PROJECT_DIR` to locate the wrapper, `$0`-relative to locate the script — is
   sound, and a *deliberate* `exit 2` still propagates correctly (`exec python3` replaces
   the process, so the python exit code is returned verbatim; I verified this). But the
   *script-not-found* path now changes behavior asymmetrically by hook type. Pre-T138, a
   missing/unresolvable hook script produced a non-zero exit → the write was **blocked**.
   Post-T138, `[ -f "$script" ] || exit 0` (and the settings.json `|| exit 0`) means a
   missing script → **silent exit 0** → write proceeds. For `log_tool_usage` and
   `regenerate_ticket_index` this fail-open is correct (best-effort telemetry/index must
   never block a tool). But the SAME blanket fail-open is applied to
   `check_cross_layer_writes` — the *enforcer* of Invariant 2 and Invariant 4. If that
   one script ever fails to resolve (rename, partial checkout, perms, a future refactor
   that moves it), workspace isolation silently vanishes instead of blocking. In normal
   operation the `$0`-relative resolution makes the script always present, so this is a
   defense-in-depth gap rather than an active hole — but the harness's own threat model
   (Inv 4: "cross-workspace data leakage is a confidentiality violation") is exactly the
   case where you want loud failure. Recommendation: differentiate enforcement hooks from
   best-effort hooks. The enforcement hooks (`check_cross_layer_writes`, and arguably
   `check_ticket_acs`/`check_fix_commit_has_code`) should fail closed — or at minimum emit
   a visible stderr warning AND exit 2 — when their script can't be resolved; only the
   telemetry/index hooks should silently `exit 0`. A small allowlist of fail-open hook
   names in `run_hook.sh`, defaulting to fail-closed, would express the policy in one place.

2. **Two parallel copies of the `.active_workspace` tri-state reader now exist, and one
   of them is the Inv 2/4 enforcer.** [Low-Medium impact, tracked debt] T136 added
   `workspace_config.read_session_state()` (workspace_config.py:147-163), which the
   implementer's own comment (lines 131-132) notes "Mirrors the tri-state read in
   `scripts/hooks/check_cross_layer_writes.py`; a future pass could have the hook import
   these instead of keeping its own copy." The hook's copy is at
   check_cross_layer_writes.py:34-57. They agree today (same sentinel `__harness__`, same
   `.strip()`, same empty→undeclared rule), but they are the attribution authority (which
   layer a telemetry record / index / SR is stamped with) and the enforcement authority
   (which writes get blocked). If they ever drift — a future fourth state, different
   whitespace handling, a sentinel rename done in one file — the tool that *attributes* and
   the hook that *blocks* would disagree about what layer the session is, and the
   disagreement would be silent. The implementer flagged this honestly as deferred debt,
   so this is tracked, not a missed defect. Recommendation: have the hook import
   `workspace_config.read_session_state` (the hook already manipulates `sys.path` for ROOT;
   the import is cheap and fail-open-able), collapsing to a single source of truth. T136's
   note already anticipates this — promote it to a ticket so it doesn't rot.

3. **`claude_session_uuid` join key rests on an unverified Claude Code internal
   assumption — `log_tool_usage.py:266`.** [Low impact] The new field stores
   `os.environ.get("CLAUDE_CODE_SESSION_ID", "")` on the documented premise that this value
   "IS the native JSONL transcript filename" (line 23). If that premise is wrong (env var
   unset in the hook subshell — note CLAUDE.md records `$CLAUDE_PROJECT_DIR` was *empty* in
   a hook subshell as of S3, later found present on 2.1.158; env availability in hooks has
   bitten this harness before — or the filename≠UUID), the field is silently dead weight: it
   degrades to `""` and the deferred T141 join finds nothing. Low risk because it fails
   gracefully and the join is explicitly deferred. Recommendation: before building T141,
   empirically verify the env var is populated in the `log_tool_usage` subshell AND that a
   live `.git/session_tool_log.jsonl` record's uuid matches an actual transcript filename
   on disk. One `/verify`-style check, not a code change. If it's empty in practice, drop
   the field rather than carry a dead join key.

Note (acknowledged, not a concern): the `_session_from_sessions_md` last-logged+1
off-by-one (log_tool_usage.py docstring) is pre-existing (path-based stamping had it too),
documented in-code, and explicitly deferred — the `claude_session_uuid` field is the
intended future reconciliation key (T141). Correctly out of scope for T137.

## Suggested Next Session Focus

1. **Differentiate enforcement vs. best-effort hooks in `run_hook.sh` (Concern #1).**
   ~8 LoC + 2 tests (script-present → runs; enforcement-script-missing → exit 2 + stderr;
   best-effort-script-missing → exit 0). This is the only Medium finding and it sits
   directly on the Inv 2/4 trust boundary that T138 touched. The existing
   `tests/test_hook_command_resolution.py` is the natural home for the cases.

2. **Collapse the duplicated tri-state reader (Concern #2).** Promote workspace_config.py's
   line 131-132 note to a ticket and have `check_cross_layer_writes.py` import
   `read_session_state`. ~10 LoC net negative. Single source of truth for the
   attribute-vs-block layer decision; closes the silent-divergence risk before a fourth
   state or a rename introduces it.

3. **Verify the `claude_session_uuid` premise before investing in T141 (Concern #3).**
   A read-only `/verify`: confirm `CLAUDE_CODE_SESSION_ID` is populated in the hook subshell
   and that a logged uuid maps to a real transcript filename. Cheap insurance against
   building the T141 join on a `""` field.

No multi-session carry-forwards remain (S23's three items were the carry-forward and S24
was docs-only). All three S25 items are net-new from this session's diff.

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
