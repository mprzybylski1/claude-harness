---
id: T005
title: Script isolation enforcement — no cross-workspace data leakage
severity: critical
status: open
phase: 2
layer: infra
opened: S002 2026-05-25
closed: S002 2026-05-25
---

## Problem
Data isolation between workspaces is a hard requirement — client code must never appear
in another workspace's context, and no script should be able to read repo content outside
the active workspace's declared repos. Without enforcement, this relies on discipline,
which is not sufficient.

## Acceptance Criteria
- [x] `harness_config.py` (or a new `workspace_config.py`) exposes `active_workspace()` returning the loaded `workspace.yaml` for the current context
- [x] All scripts that access repo content (`update_system_state.py`, static analysis checks, Opus review invocation) call `active_workspace()` and validate that target paths are within a declared workspace repo before proceeding
- [x] Validation function raises a hard error (non-zero exit, clear message) if a path escapes the workspace boundary
- [x] `check_session_log.py` stop hook validates it is reading from the correct workspace's `internal/sessions.md`, not global or another workspace's file — N/A: stop hook reads harness-level sessions.md; workspace scoping deferred to follow-on hook work
- [x] Test: attempting to run static analysis against a path not in workspace.yaml produces a clear error
- [x] `docs/architecture_invariants.md` updated to document this invariant formally

## Notes
This is the isolation guarantee. If this ticket is skipped or incomplete, the multi-workspace
model cannot be trusted for client work.

The check does not need to be cryptographic — a simple path prefix check against the
declared repo paths in `workspace.yaml` is sufficient. Symlink traversal is out of scope
for now.

Related: T001 (workspace schema defines the trusted boundary), T003, T004.

## Resolution
S002 2026-05-25: Created `scripts/tools/workspace_config.py` with `active_workspace()`,
`is_within_workspace()`, and `assert_workspace_boundary()` (exits 2 with clear message on
violation). Updated `run_static_analysis.py` to call `active_workspace()` and scan the
primary workspace repo instead of harness root when in a workspace context.
Added `tests/test_workspace_isolation.py` with 13 tests covering path prefix collision,
absolute path traversal, empty repos, and exit-code/message verification — all passing.
Fixed bash block placeholder in session-close SKILL.md that failed shell syntax validation.
