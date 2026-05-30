---
id: T136
title: generate_ticket_index.py overwrites harness INDEX when run from a workspace session
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S24 2026-05-30
closed:
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

- [ ] (fill in)

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
(Fill in on close.)
