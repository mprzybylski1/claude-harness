---
id: T035
title: Telemetry bootstrap exit-after-touch + batch small fixes (S7 C#1/C#3/C#4/C#6/Bug#2, S6 C#12, S1 #7)
severity: medium
status: closed
phase: 2
layer: infra
opened: S8 2026-05-25
closed: S8 2026-05-25
---

## Problem

Multiple small items from S6/S7 Opus reviews deferred from S7 inline fixes.

## Acceptance Criteria

- [x] Bootstrap exits after sentinel touch (S7 C#1) — drops one record, avoids slow path.
- [x] `_yaml_telemetry_enabled` regex has word boundary `\s*$` (S7 C#3).
- [x] `toggle_telemetry.py` regex handles multiple leading `#` (S7 C#3).
- [x] `_extract_exit` docstring clarifies Bash-only (S7 C#6).
- [x] Redundant test renamed to `test_exits_zero_with_any_state` (S7 C#4).
- [x] `harness.yaml` annotated with default-on change note (S7 Bug #2).
- [x] Dead `sessions_rel` path branch removed from `check_session_log.py` (S1 #7 / S3 #6).
- [x] `test_falls_back_on_invalid_yaml` updated to expect exit 2 (T036 follow-on).
- [x] All tests pass.

## Resolution

S8 2026-05-25: All items fixed. `log_tool_usage.py` bootstrap now exits after sentinel touch. `_yaml_telemetry_enabled` and `toggle_telemetry.py` both use tighter regexes. `check_session_log.py` dead code removed; error message uses `sessions_display` for correct path in workspace mode.
