---
id: T014
title: Support docs_path in workspace.yaml for remote docs
severity: high
status: closed
phase: 2
layer: infra
opened: S2 2026-05-25
closed: S3 2026-05-25
---

## Problem

Workspace development docs (sessions.md, tickets/, opus_notes.md) currently live in
`workspaces/<slug>/internal/` which is gitignored from the harness. They are local-only
and not backed up — lost on reinstall or machine change. For personal and client projects,
docs should travel with the code inside the project repo.

## Acceptance Criteria

- [x] `workspace.yaml` supports an optional `docs_path` field (absolute or `~`-expandable
  path pointing to a directory inside the primary repo, e.g. `~/projects/myapp/.harness/`)
- [x] `workspace_config.py` — `internal_dir(ws)` helper returns `docs_path` if set, else
  falls back to `workspaces/<slug>/internal/` (preserves backward compatibility)
- [x] All path resolution in `session-start`, `session-close`, hooks, and scripts that
  currently derives `workspaces/<slug>/internal/` uses `internal_dir(ws)` instead
- [x] `workspace.py create` prompts for `docs_path` (optional; blank = use harness-local default)
- [x] `workspace.py create` scaffolds the `docs_path` directory with the same initial files
  as the current `internal/` scaffold
- [x] Invariant 5 boundary check: `docs_path` must be inside one of the workspace's
  declared repos — `assert_workspace_boundary(docs_path, ws)` called at workspace load
- [x] Test: workspace with `docs_path` set routes session log writes to that path
- [x] Test: workspace without `docs_path` continues to use harness-local `internal/`
- [x] All existing tests still pass

## Notes

Motivated by personal project onboarding — docs should live in `.harness/` inside the
project repo so they are versioned and portable. `workspaces/*/internal/` stays gitignored
in the harness repo regardless; when `docs_path` is set the docs are committed to the
project repo instead.

Multi-repo workspaces: `docs_path` should point into the primary repo only.

Confidentiality note: opus_notes.md contains internal critique — if `docs_path` is inside
a repo shared with clients or external contributors, consider gitignoring opus_notes.md
in the project repo and only committing sessions.md and tickets/.

## Resolution

S3 2026-05-25: Workspace session docs can now live inside the project repo by setting `docs_path` in `workspace.yaml`, keeping development notes versioned and portable alongside code.

Implemented `internal_dir(ws_dir, ws)` in `workspace_config.py` as the single resolution point — returns `docs_path` (expanded, resolved) when set, else falls back to `ws_dir/internal`. Updated all path consumers: `check_session_log.py`, `check_ticket_acs.py`, `regenerate_ticket_index.py`, `portfolio.py`, `generate_client_progress.py`, `workspace.py`. Added `workspace_internal_path.py` helper script. Updated session-start and session-close skill docs to use `<INTERNAL>` placeholder derived via the new script. 12 new tests (7 unit + 5 integration), all 63 tests pass.
