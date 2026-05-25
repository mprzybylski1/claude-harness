---
id: T008
title: Global portfolio mode — cross-workspace metadata view
severity: low
status: closed
phase: 2
layer: process
opened: S002 2026-05-25
closed: S002 2026-05-25
---

## Problem
When operating at the harness root (not inside a workspace), there is no way to see the
state of all workspaces at a glance — which are active, what's open, when work last
happened. This makes it hard to prioritise across multiple engagements.

## Acceptance Criteria
- [x] `scripts/tools/portfolio.py` generates a cross-workspace summary: workspace name, type, status, open ticket count (by severity), last session date, repos
- [x] Summary is metadata only — no session content, no ticket body, no Opus findings
- [x] Output renders cleanly as markdown (suitable for piping to a file or printing to terminal)
- [x] `/session-start` at harness root calls `portfolio.py` before workspace selection prompt
- [x] `portfolio.py` is callable standalone: `python scripts/tools/portfolio.py`

## Notes
Depends on T001, T002. This is the lowest priority ticket — MVP is T001–T005.

The global mode is intentionally read-only for content. The only actions at harness root
are: workspace selection, workspace management (create/archive), and portfolio review.
All actual work happens inside a workspace session.

Related: T002, T003.

## Resolution

S002 2026-05-25: Implemented `scripts/tools/portfolio.py` — reads workspace.yaml (name,
type, repos count), ticket frontmatter severity fields only (no bodies), and sessions.md
date-pattern lines only. Outputs a markdown table sorted by last session date descending,
with per-workspace ticket breakdown by severity and a totals footer. Robust to missing
workspaces/ directory or empty list (prints "No active workspaces." and exits 0). Also
extended `.claude/skills/session-start/SKILL.md` Step 0 to run `portfolio.py` and show
its output before the workspace selection prompt when workspaces are present at harness root.
