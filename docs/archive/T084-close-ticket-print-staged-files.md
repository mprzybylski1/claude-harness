---
id: T084
title: close_ticket.py prints staged files after staging
severity: low
status: closed
phase: process
layer: process
opened: S17 2026-05-26
closed: S17 2026-05-26
---

## Problem

After `_git_stage` succeeds, `close_ticket.py` is silent about what it staged.
The model must then run `git status && git diff --cached --stat` to verify staging
before committing — an extra Bash call (and ~500 tokens of output) per ticket close
that is purely redundant with information the tool already has.

Over 5 tickets in S17, this was 5 avoidable Bash calls (~2,500 tokens of verification
output that contributed nothing to correctness).

## Acceptance Criteria

- [x] `close_ticket.py` prints a staging summary to stdout after `_git_stage` returns
      successfully, listing each path staged (ticket removal, archive destination,
      INDEX.md, and any `--files` paths).
- [x] Format: one path per line, prefixed with `  staged: `, before the "Suggested
      commit:" block.
- [x] If `_git_stage` is skipped (no-git path), no staging summary is printed.
- [x] At least one existing test or new test asserts the staging summary appears in
      stdout on success.

## Notes

S17 workflow-review finding #3. Pairs with T083 (carry-forward sweep) and T085
(--path-only flag) as part of reducing per-ticket mechanical overhead.

## Resolution

Added staged-path summary to close_ticket.py main(): after _git_stage succeeds, prints one 'staged: <path>' line per staged file (archive dest, INDEX.md, and any --files paths), before the 'Suggested commit:' block. Two new tests in test_close_ticket_stage_files.py.

Closed S17 2026-05-26.
