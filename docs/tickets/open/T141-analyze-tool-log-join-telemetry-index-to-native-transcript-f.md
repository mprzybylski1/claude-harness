---
id: T141
title: analyze_tool_log: join telemetry index to native transcript for token-level data
severity: low
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S25 2026-05-31
closed:
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [ ] Join the live-stamped index (claude_session_uuid) to the native JSONL transcript under ~/.claude/projects/.../<uuid>.jsonl to surface per-call/per-message token counts and full I/O
- [ ] Only build when a consumer needs token-level data (e.g. a richer /workflow-review token audit) — YAGNI until then
- [ ] Handle transcript-schema fragility/format drift defensively; locate the transcript by claude_session_uuid (= filename)
- [ ] This is the deferred half of T137's fix+bridge decision (see docs/native_vs_custom.md telemetry rationale)

## Resolution
(Fill in on close.)
