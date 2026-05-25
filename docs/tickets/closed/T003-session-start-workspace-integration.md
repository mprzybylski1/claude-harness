---
id: T003
title: Session-start workspace integration
severity: high
status: open
phase: 2
layer: process
opened: S002 2026-05-25
closed: S002 2026-05-25
---

## Problem
`/session-start` has no concept of workspaces. It reads global state and loads global
context. In the multi-workspace model, a session must be scoped to one workspace —
loading only that workspace's sessions, tickets, and repos.

## Acceptance Criteria
- [x] `/session-start` detects whether it is running from harness root or from within `workspaces/<slug>/`
- [x] When run from harness root: lists active workspaces (name, type, open tickets, last session), prompts user to select one, then scopes the session to that workspace
- [x] When run from within a workspace directory: auto-detects workspace from `workspace.yaml`, skips selection prompt
- [x] Session briefing sources from workspace-scoped files: `internal/sessions.md`, `internal/tickets/open/`, `internal/opus_notes.md`
- [x] Repos listed in `workspace.yaml` are surfaced in the briefing (names + paths)
- [x] No state from other workspaces appears in the session briefing

## Notes
Depends on T001 (workspace schema), T002 (workspace list).

The workspace selection step is the only cross-workspace operation in a normal session.
Once a workspace is selected, the session is fully isolated to that workspace.

Related: T004 (session-close), T005 (script isolation).

## Resolution
S002 2026-05-25: Updated `.claude/skills/session-start/SKILL.md` with Step 0 (workspace
detection). Skill now runs `workspace.py list`, detects CWD context (harness root vs.
workspace), prompts workspace selection when at root, auto-detects when inside a workspace.
Path substitution table added mapping all context file reads to workspace-scoped paths.
Session briefing extended with Workspace and Repos fields.
