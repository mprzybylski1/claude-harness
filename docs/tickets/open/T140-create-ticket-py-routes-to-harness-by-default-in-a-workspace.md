---
id: T140
title: create_ticket.py routes to harness by default in a workspace session (no .active_workspace awareness)
severity: low
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S25 2026-05-30
closed:
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [ ] Bare create_ticket.py (no --workspace) in a declared-workspace session does not silently create a harness ticket
- [ ] Mirror generate_ticket_index.py (T136): consult .claude/.active_workspace and fail closed (or route) for workspace/undeclared sessions; harness session unchanged; explicit --workspace always wins
- [ ] Reuse workspace_config.read_session_state (added in T136) — do not re-derive session state

## Resolution
(Fill in on close.)
