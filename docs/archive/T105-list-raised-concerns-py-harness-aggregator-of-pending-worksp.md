---
id: T105
title: list_raised_concerns.py — harness aggregator of pending workspace concerns
severity: high
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S20 2026-05-27
closed: S20 2026-05-27
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] Script exists at scripts/tools/list_raised_concerns.py
- [x] Scans workspaces/*/raised/*.md; excludes archive/ subdirectory
- [x] Groups output by workspace + severity; shows only raised and promoted items
- [x] Exits cleanly with no output when no pending concerns exist
- [x] Regression test: multi-workspace scan returns correct grouping

## Resolution
Implemented list_raised_concerns.py: scans workspaces/*/raised/*.md (excludes archive/), filters to raised/promoted status, groups by workspace sorted by severity descending, prints triage instructions; no output when empty.

Closed S20 2026-05-27.
