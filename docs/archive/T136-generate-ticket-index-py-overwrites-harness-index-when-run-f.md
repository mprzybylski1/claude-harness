---
id: T136
title: generate_ticket_index.py overwrites harness INDEX when run from a workspace session
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S24 2026-05-30
closed: S25 2026-05-30
source: scrabble-score/SR-009
---

## Problem

Promoted from scrabble-score/SR-009.

## Context

Surfaced in scrabble-score S12 while creating workspace tickets. Running
`scripts/tools/generate_ticket_index.py` with no args from a workspace session
defaulted to the harness-root `docs/tickets/INDEX.md` and silently overwrote it
(header date+session bump S23→S24) even though `.claude/.active_workspace` was set
to `scrabble-score`. Had to `git checkout docs/tickets/INDEX.md` in the harness repo
to revert the stray change. Regenerating the *workspace* index requires the explicit
`--tickets-dir` / `--output` / `--sessions` triple every time.

Not blocking (the revert is one command), but it is a silent cross-layer write — a
workspace session mutating harness-root state — which is exactly the failure class
Invariant 2 exists to prevent. The cross-layer-write hook does not catch it because
the script runs from harness root with the harness path as an explicit-looking
default.

Same workspace-blind family as SR-008 (`create_ticket.py`) and SR-010 (telemetry).

## Proposed change

`generate_ticket_index.py` reads `.claude/.active_workspace` at entry. If a workspace
is declared AND `--tickets-dir`/`--output` are omitted, either (a) auto-route to that
workspace's `internal/tickets/` + INDEX paths, or (b) fail-closed (exit 2) printing
the correct command line — mirroring the fail-closed posture of
`check_cross_layer_writes.py`. Harness-root sessions (no `.active_workspace` or
`__harness__`) keep current behaviour. Add a test covering both branches.

Cleanest end state: SR-008/009/010 share a `workspace_context.py` helper that every
ticket/sessions/telemetry script calls to resolve `(slug, internal_path, sessions_md)`
or `None`, rather than each script re-deriving (or ignoring) workspace scope.
## Acceptance Criteria

- [x] Bare `generate_ticket_index.py` (no `--workspace`, no `--tickets-dir`/`--output`) in a declared-**workspace** session fails closed (exit 2) printing the corrected `--workspace SLUG` command, instead of silently overwriting the harness INDEX.
- [x] **Undeclared** session state (missing/empty `.claude/.active_workspace`) also fails closed (exit 2) — never silently writes the harness INDEX. Mirrors `check_cross_layer_writes.py`'s Invariant-3 posture.
- [x] **Harness** session (`.active_workspace == __harness__`) keeps current behavior: regenerates the harness INDEX.
- [x] `--workspace SLUG` resolves tickets/INDEX/sessions paths from that workspace's internal dir (the T135-deferred sibling fix); individual `--tickets-dir`/`--output`/`--sessions-file` still override.
- [x] Explicit `--tickets-dir`/`--output` bypass all session-state logic (existing callers — regen hook, session-close, close_ticket — pass explicit paths and are unaffected).
- [x] A shared session-state resolver lives in `workspace_config.py` (reads `.claude/.active_workspace`, cwd-independent), distinct from the CWD-sniffing `active_workspace_dir()`.
- [x] Guard test: the harness INDEX is NOT written/modified when generate runs in a workspace session.
- [x] Idempotency test: regenerating twice with identical inputs yields byte-identical output (locks the determinism the S24 field evidence flagged; the stale-stamp case is session-resolution, T139-class, and explicitly out of scope here).

## Coordination

Part of the workspace-blind tooling sweep (SR-007 family): **T135 (SR-008) →
T136 (SR-009) → T137 (SR-010)**, triaged S24 as "3 tickets, helper-first".

- **Shared workspace resolver deferred from T135 to here (S25).** T135 closed
  without building it — T135 had no consumer (it gets the slug from explicit
  `--workspace` and reuses `_resolve_internal`). T136 is the first real consumer,
  so build the `.active_workspace`-based resolver here and design its interface
  against this ticket's actual need. **Extend `workspace_config.py`** (which
  already has `active_workspace_dir`/`internal_dir`/`list_active_workspaces`) with
  an `.active_workspace`-reading resolver — do NOT spawn a parallel
  `workspace_context.py` module (a second overlapping module is its own divergence,
  which is the very thing the coordination note wanted to avoid).
- **`generate_ticket_index.py --workspace SLUG` sibling fix also deferred from
  T135 to here (S25).** T136 *is* `generate_ticket_index`, so the `--workspace`
  flag is its natural home. T135 did not touch the script.
- **The `regenerate_ticket_index.py` hook is NOT workspace-blind** (S25 finding):
  it already routes by the written file's path via `_detect_workspace_from_path`
  and writes the correct workspace/harness INDEX. The SR's guess that the hook
  "likely is" workspace-blind is wrong — don't re-investigate that. (The hook's
  *output instability* in the Field-evidence section below is a separate defect.)

## Field evidence (S24)

The `regenerate_ticket_index.py` PostToolUse hook (wired in `.claude/settings.json`
on `Edit|Write`) misbehaved **twice** in S24 during routine ticket edits, beyond
the workspace-blind default this ticket describes:

1. After committing the SR-008/009/010 promotions, the hook left the worktree
   `docs/tickets/INDEX.md` reverted to a stale `S23 / 0 tickets` state — had to
   re-run `generate_ticket_index.py` to reconcile it back to `S24 / 3 tickets`.
2. After a later edit to T137, the hook rewrote INDEX to a **content-identical**
   file that `git` still flagged as modified (0 real diff lines — whitespace /
   trailing-newline instability). Had to `git checkout HEAD -- docs/tickets/INDEX.md`.

So the regen path has two defects, not one: (a) the workspace-blind scoping in the
title, and (b) **unstable/incorrect output on harness-root edits** — stale session
stamp in case 1, whitespace churn in case 2. Whatever fix lands here should make
the regen output **deterministic** (same inputs → byte-identical file) and correct
under harness-root sessions, not only fix workspace routing. Add a test asserting
idempotency: regenerate twice, assert no diff.

## Resolution
Made generate_ticket_index.py workspace-aware and fail-closed, and centralised
the session-state read.

Behaviour (precedence): explicit --workspace > explicit --tickets-dir/--output >
.active_workspace state.
- --workspace SLUG resolves tickets/INDEX/sessions from that workspace's internal
  dir (the T135-deferred sibling fix); individual path flags still override.
- Bare invocation (no --workspace, no explicit paths) consults
  .claude/.active_workspace: harness (__harness__) → regenerate harness INDEX
  (unchanged); workspace slug → FAIL CLOSED (exit 2) printing the corrected
  `--workspace SLUG` command; undeclared/empty → FAIL CLOSED (exit 2). Never
  silently overwrites the harness INDEX from a non-harness session — the SR-009
  bug. Mirrors check_cross_layer_writes.py's Invariant-3 posture (that hook can't
  catch this write because it's a python open(), not Edit/Write).
- Explicit --tickets-dir/--output bypass all state logic, so existing callers —
  the regen hook, session-close, close_ticket._regenerate_index — are unaffected
  (verified: 480 suite tests pass, incl. close/create ticket integration).

Chose fail-closed over auto-route deliberately: auto-routing would resolve
workspace context by a different mechanism than create_ticket (explicit
--workspace), widening that sibling's divergence. Fail-closed + the new
--workspace flag keeps the family consistent and matches the cross-layer hook.

Shared resolver (T135-deferred): added read_session_state() and workspace_paths()
to workspace_config.py — reads .claude/.active_workspace, cwd-INDEPENDENT, mirroring
check_cross_layer_writes' tri-state. Deliberately EXTENDED workspace_config rather
than spawning a parallel workspace_context.py module. It sits beside (not replacing)
the CWD-sniffing active_workspace_dir(). A later pass could have the hook import
these to dedup its private copy — noted, not done (trust-boundary file, out of scope).

Determinism (S24 field evidence): generate output was ALREADY byte-identical on
identical inputs (verified empirically: two runs + committed INDEX all identical,
single trailing \n). Locked it with an idempotency test. The case-1 stale-stamp /
"0 tickets" artifact is NOT reproduced and NOT fixed here — it's session-resolution
(T139-class) and/or the pre-T138 cwd-drift instability, not output nondeterminism.
skip-if-unchanged was considered and rejected: identical content writes identical
bytes (git isn't dirtied anyway), so it would only avoid mtime churn — no real gain.

The regenerate_ticket_index.py hook is NOT workspace-blind (it routes by the written
file's path via _detect_workspace_from_path) — the SR's guess was wrong; recorded so
it isn't re-investigated.

Follow-up: create_ticket.py has the same silent-harness-default routing for bare
(no --workspace) invocations in a workspace session → opened T140 to converge the
family (reusing read_session_state).

Files: scripts/tools/generate_ticket_index.py, scripts/tools/workspace_config.py,
tests/test_generate_ticket_index.py (new — 8 tests). 480 suite tests pass.

Closed S25 2026-05-30.
