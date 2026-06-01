---
id: T149
title: Improve current_session.py error message when sessions.md exists in wrong format
severity: low
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S29 2026-06-01
closed:
---

## Problem

When sessions.md exists but contains no S<N> YYYY-MM-DD: entries (e.g. markdown table format from manual scaffolding), the error message says only 'no entries found' without indicating the file was loaded or showing the expected format. This blocked create_ticket.py invisibly during sub-tracker S1.

## Acceptance Criteria

- [ ] If the file exists and has content but no match, print the first non-blank line and the expected pattern
- [ ] Existing happy-path behaviour unchanged
- [ ] Unit test covering the wrong-format case

## Resolution
(Fill in on close.)
