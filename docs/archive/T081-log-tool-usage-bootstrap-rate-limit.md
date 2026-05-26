---
id: T081
title: log_tool_usage.py bootstrap-path errors bypass rate-limit
severity: medium
status: closed
phase: process
layer: infra
opened: S16 2026-05-26
closed: S17 2026-05-26
---

## Problem

Carry-forward from S9 onwards (7-session run as of S15). Opus has repeatedly noted:
"`_log_error` bootstrap-failure rate-limit STILL not addressed; S12 added MORE
`_log_error` call sites."

The rate-limit machinery in `_log_error` itself depends on file I/O against
`_ERR_STATE_PATH` (under `.git/`). If a module-import-time failure happens
*before* the harness root is resolvable, or if `.git/` isn't reachable, calling
`_log_error` from the bootstrap path will (a) silently swallow the rate-limit
state failure and (b) write directly to `_ERR_PATH` without any cap. Each
subsequent hook invocation appends another error line until something else
cleans up — exactly the "bootstrap storm" pattern Opus has been calling out.

T073 (just closed in S16) addressed the **normal-path** TOCTOU race, boundary
check, and tilde expansion. It did not touch the bootstrap path.

## Acceptance Criteria

- [x] Module-level imports in `log_tool_usage.py` that can fail
      (`harness_config`, `workspace_config`) are wrapped to not call
      `_log_error` if `_ERR_STATE_PATH.parent` does not exist yet.
- [x] `_log_error` short-circuits and writes a single one-shot
      `[bootstrap: <error>]` line to stderr (not `_ERR_PATH`) when
      `_ERR_STATE_PATH.parent` is missing, then returns.
- [x] Test in `tests/test_telemetry.py`: simulate `.git/` absence (point
      `_ERR_PATH` at a non-existent directory) and call `_log_error` 100
      times — verify total stderr/file output is bounded (1 line, not 100).
- [ ] Opus review of S<close-session> confirms the carry-forward is cleared.

## Notes

S16 workflow-review finding (recurring Opus complaint section).
Tracks back through S12, S13, S14, S15 Opus reviews.
Distinct from [[T073]] which fixed normal-path race + boundary + expanduser.

## Resolution

Added _BOOTSTRAP_STDERR_LOGGED module-level flag and two guards in _log_error: (1) bootstrap guard checks _ERR_STATE_PATH.parent.exists() and emits one-shot stderr message if .git/ is absent; (2) state_ok sentinel prevents falling through to _ERR_PATH when state file IO fails (disk full, IsADirectoryError, etc.) — previously the inner except pass left count=0 so all calls wrote to the error log uncapped. Also covers the Opus S16 concern #1 (state IO failure bypassing rate limit), not just the bootstrap path. 3 new tests in TestLogErrorBootstrapGuard.

Closed S17 2026-05-26.
