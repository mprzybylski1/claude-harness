---
id: T150
title: Warn on machine-specific absolute paths in workspace.py create and repo_hygiene.py
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S29 2026-06-01
closed: S29 2026-06-01
---

## Problem

workspace.py create accepts /Users/... or /home/... paths without warning. Result: workspaces break silently when the same harness repo is used on a different machine. SubTracker hit this on S1 — repo path and docs_path both needed migration to ~/symlink form.

## Acceptance Criteria

- [x] workspace.py create warns (not errors) when a path resolves to /Users/, /home/, /mnt/, /Volumes/, or C:\-style absolute paths, and suggests ~/symlink
- [x] repo_hygiene.py adds a WARN-level finding for any existing workspace.yaml repos[].path or docs_path with a machine-specific absolute prefix
- [x] Tests for both detection paths

## Resolution
Added shared is_machine_specific_path() and portable_path() to workspace_config.py. workspace.py create warns on machine-specific paths and stores portable ~/... form. repo_hygiene.py WARNs on existing workspace.yaml with machine-specific paths. Migrated scrabble-score to ~/... form.

Closed S29 2026-06-01.
