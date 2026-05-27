---
id: T112
title: Document abandoned-session pattern in session-close SKILL.md
severity: low
status: closed
phase: 2
layer: process
# repo: <name from workspace.yaml repos list>
opened: S20 2026-05-27
closed: S20 2026-05-27
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] session-close SKILL.md documents the abandoned-session pattern: WIP branch, raise_for_harness.py, session log note, no regular session-close
- [x] session_status: abandoned convention is defined and shown in example sessions.md entry
- [x] Workspace session-close skill references the abandoned path when a mid-session blocker is hit
- [x] No code changes required; documentation only

## Resolution
Added 'When to use the abandoned-session pattern instead' early-bailout note and full 'Abandoned session' section to session-close SKILL.md. Defines the WIP branch → raise_for_harness.py → session log → exit flow, the session_status: abandoned Session Log convention, and the resumption path. No code changes.

Closed S20 2026-05-27.
