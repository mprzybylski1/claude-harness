---
id: T016
title: Reject docs_path inside workspaces_base() at workspace create
severity: high
status: closed
phase: 2
layer: tools
opened: S4 2026-05-25
closed: S4 2026-05-25
---

## Problem

`workspace.py cmd_create` calls `is_within_workspace(docs_path, temp_ws)` to verify
docs_path is inside a declared repo, but does not check whether docs_path is inside
`workspaces_base()`. A user can declare primary repo `~/projects/myapp` and set
docs_path to `~/projects/myapp/workspaces/other-ws/internal/`, which passes the
current check but colocates this workspace's docs inside another workspace's tree —
violating Invariant 5 (cross-workspace isolation).

## Acceptance Criteria

- [x] `cmd_create` rejects docs_path that is inside `workspaces_base()` with a
  clear error message
- [x] Test: docs_path under `workspaces_base()` is rejected at create time
- [x] Test: docs_path outside `workspaces_base()` but inside declared repo is accepted
- [x] All existing tests still pass

## Resolution

S4 2026-05-25: Workspace create now rejects docs_path that falls inside the harness workspaces directory, preventing cross-workspace contamination.

Added a `relative_to(ws_base)` check immediately after the existing `is_within_workspace` guard in `cmd_create` — reuses the already-computed `ws_base`. 2 new tests in TestDocsPathContainmentCheck; 67/67 pass.
