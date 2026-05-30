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

- **Depends on T135's `workspace_context.py` helper.** Consume the shared
  resolver rather than re-deriving workspace scope from `.claude/.active_workspace`.
- **Shares `generate_ticket_index.py` with T135.** T135's SR-008 sibling fix
  adds `--workspace SLUG` to this same script. Coordinate so only one ticket
  edits `generate_ticket_index.py` (and the `regenerate_ticket_index.py` hook);
  the other references that change. Avoid two independent edits to the script.

## Resolution
(Fill in on close.)
