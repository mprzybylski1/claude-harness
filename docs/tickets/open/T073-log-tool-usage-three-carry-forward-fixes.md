---
id: T073
title: log_tool_usage.py three carry-forward fixes (race, >= window, expanduser)
severity: medium
status: open
phase: process
layer: process
opened: S15 2026-05-26
closed:
---

## Problem

Three issues in `log_tool_usage.py` and `workspace_config.py` have been flagged across
multiple Opus sessions (S12–S15) and not fixed:

### 1. Cross-process TOCTOU race in `_log_error` (S14 #2, S15 #1)

T071 added a JSON state file for cross-process rate-limiting, but the read-modify-write
cycle has no file lock (`fcntl.flock`). Two concurrent hook subprocesses can both read
`count=N`, both write `N+1`, and lose updates — the rate limit can be bypassed if enough
hooks fire simultaneously. T071's test is sequential and cannot catch this.

Fix: wrap the read-modify-write in `fcntl.flock(fd, fcntl.LOCK_EX)` on the state file.

### 2. `>` should be `>=` in window reset check (S14 #4, S15 #2)

`scripts/hooks/log_tool_usage.py` line ~189:
```python
if now - window_start > _ERR_WINDOW_SECS:
```
Should be `>=` — an elapsed time exactly equal to the window should reset it.
One-character fix.

### 3. `Path(path).expanduser()` missing in workspace matching (S12 #3, S13, S14 #7, S15 #3)

`workspace_config.py` `_candidate_paths` (or equivalent workspace path resolution) does
not call `.expanduser()` on `docs_path` values. Paths configured as `~/...` never match
workspaces in the telemetry hook, so workspace-aware session stamping silently falls back
to harness-root for any workspace whose `docs_path` uses a tilde.

Fix: apply `.expanduser()` when resolving `docs_path` in `_candidate_paths`.

## Acceptance Criteria

- [ ] `_log_error` state file read-modify-write is protected with `fcntl.flock` (exclusive
  lock). State file created atomically if absent.
- [ ] `>` → `>=` in the window reset comparison.
- [ ] `docs_path` values are passed through `.expanduser()` before path comparison in
  workspace resolution. Test: workspace with `~/...` docs_path is matched correctly.
- [ ] Existing rate-limit tests continue to pass.

## Notes

All three are ≤ 10 LoC each. Bundle in one commit. `fcntl` is POSIX-only — add a
`try/import` guard for portability (Windows stubs it as a no-op is fine given this
runs in hook subprocesses on Linux/macOS).

## Resolution

(Fill in on close.)
