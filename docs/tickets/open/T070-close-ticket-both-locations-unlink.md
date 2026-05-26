---
id: T070
title: close_ticket.py BOTH-locations unlink silent failure
severity: medium
status: open
phase: process
layer: process
opened: S13 2026-05-26
closed:
---

## Problem

`close_ticket.py` around line 189 attempts to `unlink()` the open ticket file after
moving it to the archive. If the file exists in both `docs/tickets/open/` and
`docs/archive/` (the BOTH-locations case), the unlink of the open copy can fail silently.

In S13 this failure mode manifested: a worktree agent's pre-written archive file caused
the BOTH-locations branch to trigger, but the open ticket file was not removed from disk
(or not staged for deletion). The result was an orphaned open ticket file that required
manual cleanup.

The issue is that this code path lacks adequate error handling — an `unlink()` exception
is caught too broadly or not logged in a way that surfaces to the caller.

## Acceptance Criteria

- [ ] `close_ticket.py` line ~189 BOTH-locations branch: if `unlink()` raises, the error
  is logged to stderr and the script exits non-zero (not silently continues).
- [ ] A test covers the BOTH-locations failure mode: if `unlink()` raises
  `PermissionError`, the script exits non-zero and prints an error.
- [ ] With T064 implemented (auto-stage), the BOTH-locations branch also stages the
  deletion via `git add -u` or `git rm`.
- [ ] Opus carry-forward for this issue is cleared in the next review.

## Notes

2-session Opus carry-forward (S12, S13). No ticket previously. Related to T064
(auto-stage) and T065 (--force bypass). All three touch `close_ticket.py` error
handling — coordinate implementation to avoid conflicting edits.

See also: `docs/tickets/open/T064-close-ticket-auto-stage-git-changes.md`
and `docs/tickets/open/T065-close-ticket-force-bypass-archive-exists.md`.

## Resolution

(Fill in on close: what was done and in which session/commit.)
