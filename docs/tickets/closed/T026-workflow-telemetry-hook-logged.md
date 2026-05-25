---
id: T026
title: workflow telemetry — hook-logged tool call data
severity: low
phase: 2
layer: infra
status: closed
opened: S5 2026-05-25
closed: S6 2026-05-25
---

## Problem

The manual retrospective (T025) relies on Claude's subjective in-session memory.
It cannot surface cross-session trends, compare workspace efficiency, or produce
objective counts ("session-start takes 18 tool calls on average; script X is the
bottleneck"). Without hard data, workflow improvements are anecdotal.

## Acceptance Criteria

- [x] A PostToolUse hook (`scripts/hooks/log_tool_usage.py`) appends one JSON line
      per tool call to `.git/session_tool_log.jsonl`:
      `{"ts": ..., "tool": ..., "path": ..., "exit": ..., "session": ...}`.
      File is inside `.git/` so it is never committed or pushed.
- [x] Log rotation: hook truncates (keeps last N lines) when file exceeds threshold.
- [x] Analysis script `scripts/tools/analyze_tool_log.py` reads the log and
      produces: tool call frequency by type, top-10 most-read files, top-10
      most-edited files, error/retry sequences, and session-level tool-call costs.
- [x] `workflow-review` SKILL.md Step 1b calls the analysis script when telemetry enabled.
- [x] Hook is off by default (opt-in via `harness.yaml: workflow_telemetry: true`).
- [x] All existing tests still pass.

## Notes

Option A from the workflow observability design discussion. Builds on T025 —
implement T025 first to establish the retrospective skill structure, then add
telemetry data as an enhancement.

The `.git/` location for the log means it is never committed or pushed, avoids
cluttering the working tree, and is naturally scoped to one repo checkout.

## Resolution

S6 2026-05-25: Implemented `scripts/hooks/log_tool_usage.py` (PostToolUse; appends JSON to `.git/session_tool_log.jsonl`; rotation via keep-last-N truncation; off by default). Implemented `scripts/tools/analyze_tool_log.py` (frequency, top files, retry sequences, per-session costs; `--log`, `--session` flags). Added opt-in comment block to `harness.yaml` with `workflow_telemetry` and `workflow_telemetry_max_lines`. Added Step 1b to workflow-review SKILL.md. Hook registered in `.claude/settings.json` PostToolUse with `".*"` matcher.
