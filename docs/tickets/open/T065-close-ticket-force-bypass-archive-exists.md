---
id: T065
title: close_ticket.py --force should bypass archive-exists check
severity: medium
status: open
phase: process
layer: process
opened: S13 2026-05-26
closed:
---

## Problem

`close_ticket.py --force` currently only bypasses the unchecked-ACs guard. It does not
bypass the "archive already exists" check at line ~189. When a worktree agent pre-writes
an archive file (as happened with T055 and T056 in S13), calling `close_ticket.py` on
those tickets fails with an error about the archive already existing, even with `--force`.

This required a manual workaround in S13: deleting the open ticket file and committing
directly instead of using `close_ticket.py`.

The `--force` flag should be a blanket override for all recoverable error conditions,
including overwriting an already-existing archive file.

## Acceptance Criteria

- [ ] `close_ticket.py --force T0NN` succeeds when `docs/archive/T0NN-*.md` already
  exists, overwriting the archive file with the current ticket content.
- [ ] Without `--force`, the "archive already exists" error is still raised (no
  regression).
- [ ] Existing tests pass.
- [ ] New test: `--force` succeeds when the archive file is pre-populated.

## Notes

Occurred S13 during parallel worktree agent work for T055 and T056. Agents wrote archive
files to their worktrees, which were then copied to main repo, leaving pre-existing
archive files when `close_ticket.py` was called on master.

Related: T064 (auto-stage git changes).

## Resolution

(Fill in on close: what was done and in which session/commit.)
