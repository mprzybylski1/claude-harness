---
id: T061
title: Surface .git/session_tool_log.errors tail in /session-start briefing
severity: medium
status: closed
phase: 2
layer: infra
opened: S12 2026-05-26
closed: S13 2026-05-26
---

## Problem

When hooks fail silently (bash exec error, Python crash, permission denied), the `log_tool_usage` hook appends to `.git/session_tool_log.errors` — and that's it. Nobody reads that file. The `$CLAUDE_PROJECT_DIR`-empty regression (commit a11ee28) went undetected for at least one session because every hook silently failed and only the user noticing telemetry data was missing surfaced it.

There is no automated mechanism that signals hook failure to the operator. The next silent-failure mode will also go undetected until investigated.

## Acceptance Criteria

- [x] `/session-start` Step 1 (or a new Step 1c) tails `.git/session_tool_log.errors` and prints the last ~5 lines in the briefing.
- [x] If the file is empty or absent, briefing says "Hook errors: none" — no false positive.
- [ ] Optionally: include count of errors since last session-close (requires storing a marker).
- [x] Test: with a fake errors file containing 10 lines, briefing shows the last 5; with no errors file, briefing shows "none".

## Notes

Smallest viable: add a one-line tail to `extract_session_brief.py` output, or add it directly to the SKILL.md instructions. ~10-15 LoC if it's a script, ~5 lines of skill prose if inline.

Companion to T059 (`_log_error` rate-limit) — once errors are rate-limited and surfaced, silent-failure visibility is restored.

Surfaced by /workflow-review S12.

## Resolution

extract_session_brief.py now tails .git/session_tool_log.errors (last 5 lines) in Hook errors section. Empty/absent file shows 'none'. SKILL.md updated. 2 tests added.

Closed S13 2026-05-26.
