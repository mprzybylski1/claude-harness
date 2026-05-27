---
id: T111
title: PostToolUse hooks: block cross-layer writes between workspace and harness state
severity: high
status: closed
phase: 2
layer: infra
# repo: <name from workspace.yaml repos list>
opened: S20 2026-05-27
closed: S20 2026-05-27
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] PostToolUse hook blocks writes to docs/tickets/, docs/sessions.md, docs/opus_notes.md, docs/architecture_invariants.md when active session is a workspace session
- [x] PostToolUse hook blocks writes to workspaces/*/internal/ from a harness-root session
- [x] Boundary slot writes (workspaces/*/raised/) are exempt from both blocks
- [x] Error message names the correct session type and suggests the right tool
- [x] No --cross-layer or equivalent override flag is added to any tool
- [x] Regression tests: workspace->harness write refused; harness->workspace internal write refused; boundary slot write allowed

## Resolution
Implemented check_cross_layer_writes.py as a PreToolUse hook on Edit|Write. Reads .claude/.active_workspace state file (written by session-start) to determine session type: workspace session blocks writes to harness-layer docs (docs/tickets/, docs/sessions.md, docs/opus_notes.md, docs/architecture_invariants.md); harness-root session blocks writes to workspaces/*/internal/. workspaces/*/raised/ (boundary slot) is always exempt. Hook registered in settings.json. State file added to .gitignore. Session-start SKILL.md updated with state-file write step. 12 regression tests added.

Closed S20 2026-05-27.
