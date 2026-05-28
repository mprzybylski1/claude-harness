---
id: T115
title: fix workspace isolation hook: block cross-workspace writes, fail closed when state file absent
severity: critical
status: closed
phase: 2
layer: infra
# repo: <name from workspace.yaml repos list>
opened: S21 2026-05-28
closed: S21 2026-05-28
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] check_cross_layer_writes.py blocks workspace-A→workspace-B internal writes (not just workspace→harness and harness→workspace-internal)
- [x] Hook fails closed when .claude/.active_workspace is missing or empty: blocks writes to docs/ AND workspaces/*/internal/ and emits a message instructing the operator to run /session-start
- [x] Single source of truth for active workspace — state file is the single declared signal; fail-closed semantics make the write *enforced*, not just documented. Harness sessions now write a `__harness__` sentinel; empty/missing fails closed
- [x] Regression tests cover all three branches: missing state file, empty state file, cross-workspace write attempt (12 new tests across TestCrossWorkspaceWrites and TestUndeclaredSession)

## Resolution
Three-part fix to check_cross_layer_writes.py: (1) introduced __harness__ sentinel for harness-root sessions so empty/missing state file is unambiguously fail-closed (closes the 'forgot to write slug' attack vector Opus flagged); (2) added cross-workspace internal write blocking in the workspace branch, refactoring _is_workspace_internal into _workspace_internal_slug which returns the slug for comparison (resolves Invariant 5 hole); (3) session-start SKILL.md now writes the sentinel for harness sessions. 12 new tests in TestCrossWorkspaceWrites and TestUndeclaredSession; all 24 hook tests pass.

Closed S21 2026-05-28.
