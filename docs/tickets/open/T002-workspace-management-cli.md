---
id: T002
title: Workspace management CLI — create, list, archive
severity: medium
status: open
phase: 2
layer: infra
opened: S002 2026-05-25
closed:
---

## Problem
No way to create or manage workspaces. Without tooling, workspace setup is manual and
error-prone — missing directories, wrong gitignore, no remote configured.

## Acceptance Criteria
- [ ] `scripts/tools/workspace.py` implemented with subcommands: `create`, `list`, `archive`
- [ ] `create <slug>` scaffolds `workspaces/<slug>/` with correct structure, generates `workspace.yaml` from prompts (name, type, repos)
- [ ] `list` prints active workspaces with: name, type, repo count, last session date, open ticket count
- [ ] `archive <slug>` moves workspace to `workspaces/archive/<slug>/`, sets status to archived in workspace.yaml
- [ ] `create` validates that declared repo paths exist on disk
- [ ] `create` optionally initialises a private git remote for the client-facing layer (prompts for remote URL, skippable)
- [ ] Script is callable from harness root and from within a workspace directory

## Notes
Depends on T001 (workspace schema). This is a developer-facing CLI, not a Claude skill —
invoked via `python scripts/tools/workspace.py <subcommand>`.

A future skill wrapper (`/workspace-new`) can call this script; don't build the skill here.

Related: T001 (schema), T003 (session-start uses list).
