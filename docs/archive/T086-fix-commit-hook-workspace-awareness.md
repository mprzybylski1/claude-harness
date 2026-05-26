---
id: T086
title: Fix check_fix_commit_has_code.py workspace bypass and false-block
severity: high
status: closed
phase: 2
layer: tooling
opened: S18 2026-05-26
closed: S18 2026-05-26
---

## Problem

Two bugs in `scripts/hooks/check_fix_commit_has_code.py` (Opus S17 Concerns #1, #2):

1. **Wrong git repo queried** — `_staged_code_files` runs `git diff --cached` with no
   `-C` flag, so it queries the hook's cwd (harness root). Workspace commits using
   `git -C /external/project commit` get the harness index checked, not the project index.
   Result: workspace fix commits are blocked when correct code is staged in the project
   repo, or allowed when only archive is staged in the project repo.

2. **`git -C <path> commit` form not parsed** — `_parse_fix_commit` requires
   `tokens[git_idx + 1] == "commit"`. For `git -C /path commit -m "fix(T001): ..."`,
   the token after "git" is "-C", so the function returns None and the hook bypasses
   entirely.

3. **Archive exclusion only covers harness paths** — `docs/archive/` and `docs/tickets/`
   are hardcoded. Workspace archive paths (`workspaces/<slug>/internal/archive/`,
   external `.harness/archive/`) are not excluded.

## Acceptance Criteria

- [x] `git -C <path> commit -m "fix(TXXX): ..."` form is detected and the correct git
      repo (at `<path>`) is queried for staged files.
- [x] Archive-path exclusion covers `*/archive/*` and `*/tickets/*` patterns (any depth).
- [x] Existing tests still pass.
- [x] Two new tests: one for the workspace false-block (commit correctly staged in
      external repo is allowed), one for the workspace false-allow (only archive staged
      in external repo is blocked).

## Resolution
Fixed _parse_fix_commit to walk past git flags (handles git -C <path> commit). Fixed _staged_code_files to accept git_cwd and run git -C <root> diff --cached. Generalized archive exclusion to use Path.parts membership (archive/tickets at any depth). 3 new tests for workspace false-block, false-allow, and deep archive paths.

Closed S18 2026-05-26.
