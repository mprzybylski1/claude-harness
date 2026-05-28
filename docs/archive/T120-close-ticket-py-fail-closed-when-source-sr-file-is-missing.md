---
id: T120
title: close_ticket.py: fail closed when source: SR file is missing
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

- [x] Error message includes the resolved SR search path (`<raised_dir>/<SR-NNN>-*.md`) and notes how many matches were found
- [x] Default behavior: exit 2 and block the close
- [x] `--ignore-missing-sr` flag falls back to a warning and proceeds (legacy manual override)
- [x] Replaced existing `test_missing_sr_file_warns_but_closes` with three new tests: blocks-by-default, message-includes-path, ignore-flag-allows-close

## Resolution
close_ticket.py now exits 2 by default when a ticket has a source: SR reference but the SR file cannot be located in the workspace's raised/ directory. Error message includes the searched path, match count, and points operators at the --ignore-missing-sr override for the legitimate cases (SR manually archived, workspace renamed). Replaced the prior warn-and-close test with 3 new tests covering the new behavior.

Closed S21 2026-05-28.
