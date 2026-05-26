---
id: T090
title: Tighten or drop retry-sequence detection in analyze_tool_log.py
severity: low
status: closed
phase: 2
layer: tooling
opened: S18 2026-05-26
closed: S18 2026-05-26
---

## Problem

`analyze_tool_log.py`'s "Error / retry sequences" section uses a heuristic of
"same tool within ≤30s" which flags every adjacent tool call as a potential retry.
S18 produced 40+ entries — none were real retries; all were normal incremental
development (consecutive Bash calls with different commands). Signal-to-noise is
near zero and the section dominates the report.

S18 workflow-review finding #2.

## Acceptance Criteria

- [x] Either: the heuristic is changed to require an identical command string within
      Xs (true retry), OR the section is removed entirely.
- [x] If the heuristic is tightened: at most a handful of entries appear in a normal
      session report (goal: 0–5, not 40+).
- [x] Any existing unit test for this section is updated.
- [x] The script's docstring or a one-line comment documents the new semantics.

## Resolution
Tightened _retry_sequences to require same tool AND same path within 30s. Updated module docstring and section header. Added test_retry_detection_different_path_not_flagged to confirm different-path same-tool calls are no longer flagged. S18 report: 40+ false entries → 7 genuine ones.

Closed S18 2026-05-26.
