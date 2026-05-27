---
id: T109
title: Harness-root session-start: surface pending raised concerns from all workspaces
severity: medium
status: closed
phase: 2
layer: process
# repo: <name from workspace.yaml repos list>
opened: S20 2026-05-27
closed: S20 2026-05-27
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] session-start skill invokes list_raised_concerns.py (T105) when no workspace selected
- [x] Briefing includes Pending raised concerns section grouped by workspace + severity
- [x] Section omitted entirely when no pending concerns exist (no noise)
- [x] Triage instructions shown: promote or reject commands with correct syntax
- [x] Regression: SR-001 appears in S20 briefing after this ticket is implemented

## Resolution
Updated session-start SKILL.md: added Step 1.7 (harness-root only) to run list_raised_concerns.py, added Pending raised concerns section to Step 3 briefing template (omitted when empty), and updated What good looks like checklist. Regression confirmed: SR-001 surfaces in list_raised_concerns.py output.

Closed S20 2026-05-27.
