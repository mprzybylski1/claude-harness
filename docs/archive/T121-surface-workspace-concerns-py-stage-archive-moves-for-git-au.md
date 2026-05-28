---
id: T121
title: surface_workspace_concerns.py: stage archive moves for git audit trail
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S21 2026-05-28
closed: S21 2026-05-28
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] surface_workspace_concerns.py stages the move via `git add -- <source> <dest>` after `shutil.move` — chose the in-script option so the staging is automatic and can't drift from documentation
- [x] Staging is best-effort: `subprocess.run` with `check=False` so the script still works when invoked outside a git repo (e.g. tests, fresh clones mid-bootstrap)
- [x] `test_archived_terminal_is_staged` verifies the moved file appears as staged (no unstaged delete) in `git status`
- [x] `test_works_outside_git_repo` verifies the archive move still completes when there is no git repo

## Resolution
After shutil.move archives a terminal SR, run 'git add -- <source> <dest>' to stage the rename. Best-effort (check=False) so the script still works outside a git repo. Chose the in-script approach over documenting an operator step so the staging cannot drift away from the move. 2 new tests in TestGitStaging cover the staging behavior and the no-git-repo fallback.

Closed S21 2026-05-28.
