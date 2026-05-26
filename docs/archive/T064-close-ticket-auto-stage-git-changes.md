---
id: T064
title: close_ticket.py should auto-stage git changes
severity: high
status: closed
phase: process
layer: process
opened: S13 2026-05-26
closed: S14 2026-05-26
---

## Problem

`close_ticket.py` moves the ticket file from `docs/tickets/open/` to `docs/archive/`
and regenerates `docs/tickets/INDEX.md` on disk, but never stages the git changes.
This leaves three changes unstaged after every `close_ticket.py` run:

1. Deletion of the open ticket file (`docs/tickets/open/T0NN-*.md`) — file is gone on
   disk but still tracked in git HEAD
2. New archive file (`docs/archive/T0NN-*.md`) — untracked
3. Updated `docs/tickets/INDEX.md` — modified

If the caller (usually a subagent or Claude) runs `git commit` before explicitly staging
these three paths, the ghost-tracked deletion is silently omitted. This produced a
cleanup commit during S13 when the open ticket file remained in HEAD after closing T058
and T059.

The correct fix is to have `close_ticket.py` call `git add` on all three paths after the
file operations succeed, so the caller only needs to run `git commit`.

## Acceptance Criteria

- [x] After `close_ticket.py` runs successfully, `git status` shows all three changes
  staged (deletion of open file, new archive file, updated INDEX.md) — no unstaged
  or untracked remnants from the ticket close.
- [x] If `git add` fails (e.g. not inside a git repo), `close_ticket.py` prints a
  warning and exits non-zero, rather than silently leaving things in a bad state.
- [x] Existing tests for `close_ticket.py` pass with no changes to test ACs.
- [x] New test: calling `close_ticket.py` in a temporary git repo leaves all three paths
  staged.

## Notes

Triggered by S13 ghost-tracked file bug. Root cause: `close_ticket.py` never called
`git add`. The bug was masked because agents can commit from worktrees (absolute paths
in agent prompts), so the unstaged deletion isn't caught until `git status` is inspected.

Related: T065 (`--force` should also bypass "archive already exists" check).

## Resolution

Added _git_stage() to close_ticket.py: calls git rm --cached --ignore-unmatch for the open ticket deletion, then git add for archive and INDEX.md (if they exist). Failure warnings and exits non-zero. Updated _setup in TestCloseTicket and TestCloseTicketT054 to git init + commit so existing tests pass. Added TestCloseTicketGitStaging with 2 tests (staging check + no-repo failure). S14.

Closed S14 2026-05-26.
