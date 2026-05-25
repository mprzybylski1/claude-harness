---
id: T034
title: regenerate_ticket_index.py get_current_session missing --sessions flag in workspace mode
severity: high
status: closed
phase: 2
layer: infra
opened: S8 2026-05-25
closed: S8 2026-05-25
---

## Problem

S7 Opus Concern #2. `get_current_session()` invoked `current_session.py` without
`--sessions`, returning the harness-global session ID in workspace mode. Caused
spurious T016 attribution warnings on every workspace ticket close.

## Acceptance Criteria

- [x] `get_current_session()` accepts optional `sessions_file` param and passes `--sessions` to subprocess.
- [x] `check_closed_attribution()` calls `_detect_sessions_file()` and passes result to `get_current_session()`.
- [x] `_is_closed_ticket()` tightened to use path-component check (S1 #11).

## Resolution

S8 2026-05-25: `get_current_session()` now accepts `sessions_file` param; `check_closed_attribution()` derives sessions path via `_detect_sessions_file()` before calling it. Also tightened `_is_closed_ticket()` to check path components (`parts[i-1] == "tickets" and parts[i] == "closed"`) instead of substring match.
