---
id: T002
title: Workspace management CLI — create, list, archive
severity: medium
status: open
phase: 2
layer: infra
opened: S002 2026-05-25
closed: S002 2026-05-25
---

## Problem
No way to create or manage workspaces. Without tooling, workspace setup is manual and
error-prone — missing directories, wrong gitignore, no remote configured.

## Acceptance Criteria
- [x] `scripts/tools/workspace.py` implemented with subcommands: `create`, `list`, `archive`
- [x] `create <slug>` scaffolds `workspaces/<slug>/` with correct structure, generates `workspace.yaml` from prompts (name, type, repos)
- [x] `list` prints active workspaces with: name, type, repo count, last session date, open ticket count
- [x] `archive <slug>` moves workspace to `workspaces/archive/<slug>/`, sets status to archived in workspace.yaml
- [x] `create` validates that declared repo paths exist on disk
- [x] `create` optionally initialises a private git remote for the client-facing layer (prompts for remote URL, skippable)
- [x] Script is callable from harness root and from within a workspace directory

## Notes
Depends on T001 (workspace schema). This is a developer-facing CLI, not a Claude skill —
invoked via `python scripts/tools/workspace.py <subcommand>`.

A future skill wrapper (`/workspace-new`) can call this script; don't build the skill here.

Related: T001 (schema), T003 (session-start uses list).

## Resolution
S002 2026-05-25: Created `scripts/tools/workspace.py` with `create`, `list`, `archive`
subcommands. `create` prompts for name/type/repos/client_remote, validates repo paths
exist on disk, scaffolds internal/ and client/ directory trees, generates workspace.yaml,
sessions.md, opus_notes.md, tickets/INDEX.md, client/progress.md, and CLAUDE.md.
`list` shows slug, name, type, repo count, open ticket count, last session date.
`archive` moves workspace to workspaces/archive/ and sets status:archived in yaml.
