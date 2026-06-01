---
id: T156
title: Investigate telemetry under-counting in workspace sessions
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S29 2026-06-01
closed:
---

## Problem

S3 generated ~200+ tool calls; telemetry log captured 21 tagged S3 (only 2 tagged workspace: sub-tracker). The PostToolUse hook is silently dropping most tool calls. Without reliable telemetry, /workflow-review loses its objective signal.

## Acceptance Criteria

- [ ] Root cause of under-counting identified and fixed
- [ ] workspace field correctly populated for workspace sessions
- [ ] Regression test or smoke check that a representative session produces telemetry close to actual call count

## Resolution
(Fill in on close.)
