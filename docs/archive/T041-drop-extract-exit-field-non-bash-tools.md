---
id: T041
title: Drop _extract_exit field from telemetry records for non-Bash tools
severity: low
status: closed
phase: 2
layer: infra
opened: S9 2026-05-26
closed:
---

## Problem

`scripts/hooks/log_tool_usage.py:75-82` — `_extract_exit` emits `"exit": 0` for every
Edit/Write/Read record. `analyze_tool_log.py` never consumes the field. Every non-Bash
record has a misleading `"exit": 0` column that looks like Bash exit data but isn't.
Future maintainers building exit-failure reports will build on data that only exists for
~5% of records (Bash calls only).

Flagged as S6 Concern #4, S7 Concern #6, S8 Finding #3. T035 updated the docstring
but left the field in the record dict.

Decision: **drop the field entirely** (not rename). `analyze_tool_log.py` doesn't use it;
if Bash exit data is wanted in future, add `bash_exit` properly at that time.

## Acceptance Criteria

- [ ] `"exit"` key removed from the record dict in `log_tool_usage.py:main()`.
- [ ] `_extract_exit` function removed (or kept as dead code if tests import it — prefer
      removal).
- [ ] Module docstring updated to reflect new log format (no `exit` field).
- [ ] Tests that assert `"exit"` in record are updated or removed.
- [ ] `analyze_tool_log.py` verified to not reference `exit` field (grep check in test
      or in this ticket's resolution).
- [ ] All telemetry tests still pass.

## Resolution

Dropped `_extract_exit` function and `"exit"` field entirely from `log_tool_usage.py`.
Updated module docstring log format example. Removed two tests (`test_extract_exit_*`).
`grep` confirmed `analyze_tool_log.py` had zero references to `exit` field.
21/21 tests pass.

Closed S9 2026-05-26.
