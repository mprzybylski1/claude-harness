---
id: T127
title: promote_raised_concern.py: carry SR Proposed change bullets into harness ticket ACs
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed:
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [ ] Parse bullet or numbered list items from the SR's ## Proposed change section and emit one - [ ] <text> AC per item into the new harness ticket
- [ ] Fall back to today's - [ ] (fill in) placeholder if no parseable list is found
- [ ] Operator can still hand-edit before close (ACs are pre-populated, not locked)
- [ ] Tests cover: bullet list parsed, numbered list parsed, prose-only fallback, mixed bullets-and-prose

## Resolution
(Fill in on close.)
