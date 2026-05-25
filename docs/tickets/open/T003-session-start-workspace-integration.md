---
id: T003
title: Session-start workspace integration
severity: high
status: open
phase: 2
layer: process
opened: S002 2026-05-25
closed:
---

## Problem
`/session-start` has no concept of workspaces. It reads global state and loads global
context. In the multi-workspace model, a session must be scoped to one workspace —
loading only that workspace's sessions, tickets, and repos.

## Acceptance Criteria
- [ ] `/session-start` detects whether it is running from harness root or from within `workspaces/<slug>/`
- [ ] When run from harness root: lists active workspaces (name, type, open tickets, last session), prompts user to select one, then scopes the session to that workspace
- [ ] When run from within a workspace directory: auto-detects workspace from `workspace.yaml`, skips selection prompt
- [ ] Session briefing sources from workspace-scoped files: `internal/sessions.md`, `internal/tickets/open/`, `internal/opus_notes.md`
- [ ] Repos listed in `workspace.yaml` are surfaced in the briefing (names + paths)
- [ ] No state from other workspaces appears in the session briefing

## Notes
Depends on T001 (workspace schema), T002 (workspace list).

The workspace selection step is the only cross-workspace operation in a normal session.
Once a workspace is selected, the session is fully isolated to that workspace.

Related: T004 (session-close), T005 (script isolation).
