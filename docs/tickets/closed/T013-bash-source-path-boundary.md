---
id: T013
title: check_ticket_acs.py Bash source path fallback not bounded to repo or harness root
severity: high
status: closed
phase: process
layer: infra
opened: S1 2026-05-25
closed: S2 2026-05-25
---

## Problem

`scripts/hooks/check_ticket_acs.py:139-145` — when resolving a Bash command's source path,
the hook tries `ws_dir/src` first, then falls back to `REPO_ROOT/src`. If `src` contains `..`
traversal (e.g. `mv ../../etc/passwd closed/T001.md`), the resolved path escapes both
`ws_dir` and `REPO_ROOT`. The `except Exception: continue` on line 145 then silently absorbs
any OSError, giving no signal that an out-of-bounds path was attempted.

## Acceptance Criteria

- [x] After resolving `src` to an absolute `resolved` path, verify it is either
  `relative_to(REPO_ROOT)` or `relative_to(ws_dir)` (if in workspace context)
- [x] If the resolved path escapes both roots, skip the source (do not read it) and
  print a WARNING to stderr
- [x] Test: command containing `mv ../outside/T001.md closed/T001.md` does not cause
  the hook to read the outside file

## Notes

Opus S1 finding #6. Low likelihood in practice but the fallback must be bounded.

## Resolution

Added `resolved.resolve()` plus `relative_to(REPO_ROOT)` / `relative_to(ws_dir)` bounds check in `check_ticket_acs.py` Bash branch before `resolved.read_text()`. Out-of-bounds paths are skipped with a WARNING to stderr. Added `TestCheckTicketAcsPathDetection::test_bash_traversal_path_skipped_with_warning` in `test_hooks_workspace_scoping.py`. All 51 tests pass.
