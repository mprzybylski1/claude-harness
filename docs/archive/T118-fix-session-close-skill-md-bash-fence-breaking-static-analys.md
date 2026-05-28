---
id: T118
title: fix session-close SKILL.md bash fence breaking static analysis
severity: low
status: closed
phase: 2
layer: process
# repo: <name from workspace.yaml repos list>
opened: S21 2026-05-28
closed: S21 2026-05-28
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] Changed the bash fence to text and collapsed raise_for_harness.py invocation to a single line
- [x] run_static_analysis.py reports `All 9 bash block(s) passed` (was 10 with 1 failure)

## Resolution
Changed the abandoned-session pattern's raise_for_harness.py example from a backslash-continued bash fence to a single-line text fence. Static analysis no longer extracts and parses it as two separate bash statements.

Closed S21 2026-05-28.
