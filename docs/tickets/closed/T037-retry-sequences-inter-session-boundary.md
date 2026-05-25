---
id: T037
title: analyze_tool_log.py _retry_sequences interleaves sessions (S6 C#10 / S7 C#7)
severity: medium
status: closed
phase: 2
layer: infra
opened: S8 2026-05-25
closed: S8 2026-05-25
---

## Problem

S6 Concern #10 / S7 Concern #7. Same-tool calls at session boundaries flagged as retries.

## Acceptance Criteria

- [x] `_retry_sequences` groups by session first, computes retries per-session, concatenates.
- [x] Existing retry test still passes.

## Resolution

S8 2026-05-25: `_retry_sequences` now uses `defaultdict` to group records by session key before computing pairs. Retries at session boundaries are no longer flagged.
