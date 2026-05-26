---
id: T065
title: close_ticket.py --force should bypass archive-exists check
severity: medium
status: closed
phase: process
layer: process
opened: S13 2026-05-26
closed: S14 2026-05-26
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

- [x] `close_ticket.py --force T0NN` succeeds when `docs/archive/T0NN-*.md` already
  exists, overwriting the archive file with the current ticket content.
- [x] Without `--force`, the "archive already exists" error is still raised (no
  regression).
- [x] Existing tests pass.
- [x] New test: `--force` succeeds when the archive file is pre-populated.

## Notes

Occurred S13 during parallel worktree agent work for T055 and T056. Agents wrote archive
files to their worktrees, which were then copied to main repo, leaving pre-existing
archive files when `close_ticket.py` was called on master.

Related: T064 (auto-stage git changes).

## Resolution

Added 'and not args.force' to the archive-exists guard in main(). One-line change at the if dest.exists() check. New test test_force_bypasses_archive_exists_check in TestCloseTicket verifies --force overwrites and plain invocation still errors. S14.

Closed S14 2026-05-26.
