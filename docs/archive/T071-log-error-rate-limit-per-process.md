---
id: T071
title: _log_error rate-limit is per-process, resets every hook call
severity: medium
status: closed
phase: process
layer: process
opened: S13 2026-05-26
closed: S14 2026-05-26
---

## Problem

`log_tool_usage.py` uses module-level globals (`_ERR_COUNT`, `_ERR_WINDOW_START`) to
rate-limit error writes to `.git/session_tool_log.errors`. However, the hook is invoked
as a fresh Python interpreter on every tool event (via the `PostToolUse` hook command).
Module globals reset to zero on each process start, making the rate-limit a no-op: every
process can write up to 11 error lines regardless of how many errors have been emitted
by prior processes in the same session.

The rate-limit was added in T059 specifically to "cap unbounded error emissions at
10/60s". In its current form it achieves that only within a single process invocation,
not across the session.

**Fix:** Persist rate-limit state in a small JSON file (e.g.
`.git/session_tool_log.errors.state`) containing `{count, window_start}`. Read it at
the start of `_log_error`, update it atomically (via temp-file rename) after each write.
If the state file is missing or malformed, start fresh (fail-open for telemetry).

**Alternative (simpler):** Accept the per-process limitation, document it, and rename
`_ERR_RATE_LIMIT` to `_ERR_RATE_LIMIT_PER_INVOCATION` so the intent is clear. The
errors file is inside `.git/` and is not committed; a session with many workspace-
detection failures would produce many error lines but the file is bounded by other
means (rotation).

## Acceptance Criteria

- [x] If "fix" path is chosen: `_log_error` reads/writes `.git/session_tool_log.errors.state`;
  calling the hook 100 times in a loop (via subprocess) produces ≤ 11 error lines
  in `.git/session_tool_log.errors` regardless of process restarts between calls.
- [x] If "document" path is chosen: N/A — fix path chosen.
- [x] Existing rate-limit tests (`TestLogErrorRateLimit`) continue to pass.

## Notes

Found during S13 Opus implementation review. The current code is not incorrect — it
limits errors within a single invocation — but does not achieve the cross-session cap
that the ticket description implied.

## Resolution

Implemented file-based cross-process rate-limit state. _log_error now reads/writes .git/session_tool_log.errors.state (JSON) via atomic temp-file rename. Removed module-level _ERR_COUNT/_ERR_WINDOW_START globals. Updated 4 existing rate-limit tests to mock _ERR_STATE_PATH; added test_rate_limit_cross_process (100 subprocess calls → ≤ 11 lines). S14.

Closed S14 2026-05-26.
