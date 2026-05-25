---
id: T011
title: check_unstaged_code_changes workspace branch reads repos without boundary check
severity: critical
status: open
phase: process
layer: infra
opened: S1 2026-05-25
closed:
---

## Problem

`scripts/hooks/check_session_log.py:170-186` — the workspace branch of
`check_unstaged_code_changes()` iterates `_all_repos(ws)` and runs `git status --porcelain`
against each resolved repo path without first calling `assert_workspace_boundary()`. If
`workspace.yaml` has been tampered with or contains a stale path pointing outside the declared
repos, the hook reads it unchecked. Per Invariant 5, `assert_workspace_boundary()` must
precede any repo file access.

## Acceptance Criteria

- [ ] `assert_workspace_boundary(repo_path, ws)` is called inside the `_all_repos` loop before
  `subprocess.run(["git", "status", ...], cwd=str(repo_path))`
- [ ] New test: workspace with a tampered path escaping the declared repo root triggers
  `SystemExit(2)` from `assert_workspace_boundary` (not a silent pass)
- [ ] All existing tests still pass

## Notes

Opus S1 finding #2. Five-line fix plus one test.

## Resolution
