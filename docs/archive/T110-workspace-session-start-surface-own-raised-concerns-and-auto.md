---
id: T110
title: Workspace session-start: surface own raised concerns and auto-archive terminal items
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

- [x] Workspace session-start reads workspaces/<slug>/raised/*.md (excludes archive/)
- [x] Briefing shows active items (raised/promoted) and items resolved/rejected since last session
- [x] Terminal items (resolved/rejected) are moved to raised/archive/ after being surfaced once
- [x] Section omitted entirely when workspace has no raised concerns
- [x] Regression test: terminal item appears exactly once then is absent from next session-start run

## Resolution
Implemented surface_workspace_concerns.py: reads workspaces/<slug>/raised/*.md, surfaces active and newly-terminal items, auto-archives terminal files after first surfacing. Updated SKILL.md Step 1.8 and Step 3 briefing template for workspace sessions.

Closed S20 2026-05-27.
