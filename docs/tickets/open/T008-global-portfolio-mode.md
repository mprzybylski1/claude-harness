---
id: T008
title: Global portfolio mode — cross-workspace metadata view
severity: low
status: open
phase: 2
layer: process
opened: S002 2026-05-25
closed:
---

## Problem
When operating at the harness root (not inside a workspace), there is no way to see the
state of all workspaces at a glance — which are active, what's open, when work last
happened. This makes it hard to prioritise across multiple engagements.

## Acceptance Criteria
- [ ] `scripts/tools/portfolio.py` generates a cross-workspace summary: workspace name, type, status, open ticket count (by severity), last session date, repos
- [ ] Summary is metadata only — no session content, no ticket body, no Opus findings
- [ ] Output renders cleanly as markdown (suitable for piping to a file or printing to terminal)
- [ ] `/session-start` at harness root calls `portfolio.py` before workspace selection prompt
- [ ] `portfolio.py` is callable standalone: `python scripts/tools/portfolio.py`

## Notes
Depends on T001, T002. This is the lowest priority ticket — MVP is T001–T005.

The global mode is intentionally read-only for content. The only actions at harness root
are: workspace selection, workspace management (create/archive), and portfolio review.
All actual work happens inside a workspace session.

Related: T002, T003.
