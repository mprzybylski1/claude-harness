---
id: T013
title: check_ticket_acs.py Bash source path fallback not bounded to repo or harness root
severity: high
status: open
phase: process
layer: infra
opened: S1 2026-05-25
closed:
---

## Problem

`scripts/hooks/check_ticket_acs.py:139-145` — when resolving a Bash command's source path,
the hook tries `ws_dir/src` first, then falls back to `REPO_ROOT/src`. If `src` contains `..`
traversal (e.g. `mv ../../etc/passwd closed/T001.md`), the resolved path escapes both
`ws_dir` and `REPO_ROOT`. The `except Exception: continue` on line 145 then silently absorbs
any OSError, giving no signal that an out-of-bounds path was attempted.

## Acceptance Criteria

- [ ] After resolving `src` to an absolute `resolved` path, verify it is either
  `relative_to(REPO_ROOT)` or `relative_to(ws_dir)` (if in workspace context)
- [ ] If the resolved path escapes both roots, skip the source (do not read it) and
  print a WARNING to stderr
- [ ] Test: command containing `mv ../outside/T001.md closed/T001.md` does not cause
  the hook to read the outside file

## Notes

Opus S1 finding #6. Low likelihood in practice but the fallback must be bounded.

## Resolution
