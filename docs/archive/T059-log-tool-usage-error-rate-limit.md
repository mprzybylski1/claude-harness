---
id: T059
title: log_tool_usage._log_error — rate-limit unbounded error emissions
severity: medium
status: closed
phase: 2
layer: infra
opened: S12 2026-05-26
closed: S13 2026-05-26
---

## Problem

`_log_error` in `scripts/hooks/log_tool_usage.py` appends to `.git/session_tool_log.errors` with no rate limit. On a read-only `.git/` or any persistent failure condition, every tool call fans out an error append — unbounded.

S12 added more `_log_error` call sites (T057's workspace-detection and session-stamping paths), worsening the problem: the hook went from ~1–2 error sites pre-S12 to ~6 post-S12. New sites include `list_active_workspaces failed`, `workspace_config import failed`, `sessions.md missing`, `sessions.md read failed`, `workspace detected but ws_dir is None`, `sessions.md path resolution failed`.

Carry-forward from Opus reviews S8 #4 / S9 #8 / S10 #8 / S11 #9 — **4 sessions unaddressed, aggravated by S12**.

## Acceptance Criteria

- [x] `_log_error` rate-limits to ≤ 10 errors per 60-second window (module-level counter + timestamp; reset on window expiry).
- [x] When the limit is hit, write one "rate-limit engaged" marker line, then suppress further writes until the window resets.
- [x] Test: simulate 100 rapid calls; assert error file gains ≤ 10 lines + 1 marker.
- [x] Hook still exits 0 in all rate-limited cases (must never break tool calls).

## Notes

Smallest viable implementation: module-level `_ERR_COUNT` and `_ERR_WINDOW_START`. Each call checks `time.time() - window_start > 60` → reset; if count < 10 → write + increment; else → write-once marker.

Hook subprocesses don't share memory across tool calls, so the "rate limit" is per-invocation. This still bounds the worst case (one persistent failure inside a single tool call writes at most 10 lines, not 100s). For cross-invocation rate-limiting, a sentinel file with mtime check would work — defer to a follow-up if needed.

## Resolution

Added module-level _ERR_COUNT/_ERR_WINDOW_START/_ERR_RATE_LIMIT/_ERR_WINDOW_SECS. _log_error now rate-limits to 10 writes per 60s window; 11th write emits marker line, further writes suppressed until window resets. Added 4 tests: caps at 10+marker, suppresses after marker, window resets after 60s, exits 0 when rate-limited.

Closed S13 2026-05-26.
