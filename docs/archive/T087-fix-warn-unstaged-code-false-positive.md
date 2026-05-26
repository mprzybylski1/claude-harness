---
id: T087
title: Fix _warn_unstaged_code false-positive in close_ticket.py
severity: medium
status: closed
phase: 2
layer: tooling
opened: S18 2026-05-26
closed: S18 2026-05-26
---

## Problem

`_warn_unstaged_code` in `scripts/tools/close_ticket.py` runs
`git diff HEAD --name-only`, which lists all files that differ from HEAD — including
both unstaged and already-staged files. If a code file was staged before
`close_ticket.py` runs, it appears in this output and triggers a spurious WARNING
"no code files staged — pass --files explicitly".

The warning becomes noise that users learn to ignore, defeating its purpose.

(Opus S17 Concern #3)

## Acceptance Criteria

- [x] `_warn_unstaged_code` uses `git diff --name-only` (working tree vs index,
      unstaged only) to detect dirty code files.
- [x] Files that are already staged (in index) do NOT trigger the warning.
- [x] Files that are unstaged (dirty working tree, not staged) DO trigger the warning.
- [x] One new test: code file already staged before close_ticket runs → no warning.
- [x] Existing test `test_no_files_warns_when_unstaged_code_exists` still passes.

## Resolution
Replaced git diff HEAD --name-only with git diff --name-only (working tree vs index, unstaged only). Staged files no longer trigger the warning. 1 new test: already-staged code file → no spurious warning.

Closed S18 2026-05-26.
