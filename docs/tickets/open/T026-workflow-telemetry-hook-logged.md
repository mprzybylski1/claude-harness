---
id: T026
title: workflow telemetry — hook-logged tool call data
severity: low
phase: 2
layer: infra
status: open
opened: S5 2026-05-25
closed:
---

## Problem

The manual retrospective (T025) relies on Claude's subjective in-session memory.
It cannot surface cross-session trends, compare workspace efficiency, or produce
objective counts ("session-start takes 18 tool calls on average; script X is the
bottleneck"). Without hard data, workflow improvements are anecdotal.

## Acceptance Criteria

- [ ] A PostToolUse hook (`scripts/hooks/log_tool_usage.py`) appends one JSON line
      per tool call to `.git/session_tool_log.jsonl`:
      `{"ts": ..., "tool": ..., "path": ..., "exit": ..., "session": ...}`.
      File is `.gitignore`d (ephemeral, not committed).
- [ ] Log rotation: hook truncates or archives the file when it exceeds a
      configurable line threshold (default 5000 lines).
- [ ] Analysis script `scripts/tools/analyze_tool_log.py` reads the log and
      produces: tool call frequency by type, top-10 most-read files, top-10
      most-edited files, error/retry sequences (tool call followed by same tool
      call within 30 s), and session-start / session-close tool-call costs.
- [ ] A `workflow-review` skill step (or separate flag) calls the analysis script
      and includes its output in the retrospective alongside the qualitative findings.
- [ ] Hook is off by default (opt-in via `harness.yaml: workflow_telemetry: true`).
- [ ] All existing tests still pass.

## Notes

Option A from the workflow observability design discussion. Builds on T025 —
implement T025 first to establish the retrospective skill structure, then add
telemetry data as an enhancement.

The `.git/` location for the log means it is never committed or pushed, avoids
cluttering the working tree, and is naturally scoped to one repo checkout.

## Resolution

(Fill in on close.)
