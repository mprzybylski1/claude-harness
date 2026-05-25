---
id: T001
title: Workspace model — schema and directory structure
severity: high
status: open
phase: 2
layer: infra
opened: S002 2026-05-25
closed: S002 2026-05-25
---

## Problem
The harness is per-project only. There is no concept of a workspace — a named unit that
owns one or more repos, scoped session state, and optional client metadata. Without this
foundation, none of the multi-project orchestration can be built.

## Acceptance Criteria
- [x] `workspace.yaml` schema defined and documented (name, type, status, opened, repos list with name/path/role)
- [x] `workspaces/<slug>/` directory structure established: `internal/` (sessions.md, opus_notes.md, tickets/), `client/` (progress.md, tickets/)
- [x] `workspaces/` skeleton committed to harness repo
- [x] `harness.yaml` updated to reference workspaces dir
- [x] `.gitignore` updated: `workspaces/*/internal/` excluded from harness repo; `workspace.yaml` committed (config, not content)
- [x] `docs/architecture_invariants.md` updated with workspace isolation invariant: scripts must never read repo paths not declared in the active workspace's `workspace.yaml`

## Notes
Multi-repo: each workspace declares a list of repos. Single-repo workspaces are just a list
of one. `role` field: `primary` (deep Opus review), `secondary` (lighter review, included
only if dirty).

Two-layer structure is required for client confidentiality: `internal/` stays local,
`client/` is pushed to a client-accessible private git remote.

Related: T002 (workspace management), T003 (session-start), T005 (script isolation).

## Resolution
S002 2026-05-25: Created `workspaces/` directory with `.gitkeep`. Defined workspace.yaml
schema (name, type, status, opened, repos[]/name/path/role, optional client_remote) in
`scripts/tools/workspace_config.py`. Added `workspaces_dir` key to `harness.yaml` and
`workspaces_dir()` accessor to `harness_config.py`. Updated `.gitignore` to exclude
`workspaces/*/internal/` and `workspaces/*/client/`. Added Invariant 5 (workspace
isolation) to `docs/architecture_invariants.md`. Directory template scaffolded by T002
`workspace.py create`.
