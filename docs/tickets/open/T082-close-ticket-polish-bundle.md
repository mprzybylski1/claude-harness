---
id: T082
title: close_ticket.py polish — _git_root_for stderr, path mismatch
severity: low
status: open
phase: process
layer: process
opened: S16 2026-05-26
closed:
---

## Problem

Two small issues in `scripts/tools/close_ticket.py` flagged by S15 Opus review
(Concerns #4 and #5) and S16 workflow-review (findings #1, #2). Bundled because
each is < 5 LoC and they touch adjacent code.

1. `_git_root_for` swallows git's stderr. When `git rev-parse --show-toplevel`
   fails, the user sees a generic "git staging failed — stage manually" warning
   regardless of cause (not-a-repo, bare repo, permission denied, etc.). The
   actual git error message is captured but discarded.

2. `_git_root_for` always calls `git -C str(path.parent) rev-parse`. The
   docstring says "git worktree root that owns `path`", but for a directory
   `path` the call inspects the parent instead. Equivalent for files (today's
   only caller), but quietly wrong if a future caller passes a directory.

3. The manual-staging WARNING does not tell the operator which directory to
   run `git add` from. When workspace docs live outside the harness repo,
   "run git add manually" is ambiguous.

## Acceptance Criteria

- [ ] `_git_root_for` includes `result.stderr.strip()` text in the WARNING
      output when git exits non-zero, so the operator sees the real error.
- [ ] `_git_root_for` resolves the correct path for directories:
      `git -C str(path if path.is_dir() else path.parent)` — or, equivalently,
      update the docstring to match current behavior and add an `assert` that
      the path is a file.
- [ ] WARNING text in `_git_stage` includes `cd <git_root>` (or
      `git -C <git_root>`) so the operator knows which repo to stage in.
- [ ] Tests in `tests/test_workspace_path_flags.py` cover:
      (a) non-git path → WARNING includes git's stderr substring,
      (b) WARNING text contains the resolved git root path.

## Notes

S16 workflow-review findings #1 + #2.
S15 Opus Architectural Concerns #4 + #5.
Cosmetic / DX polish; not a correctness bug.

## Resolution

> **Client-visible:** Ticket-close warnings now include git's actual error
> message and the working directory you need to run manual staging from.

(Fill in on close.)
