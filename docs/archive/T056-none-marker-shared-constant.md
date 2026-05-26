---
id: T056
title: S10 — *(none)* aging marker duplicated across generator and consumer
severity: low
status: closed
phase: 2
layer: infra
opened: S10 2026-05-26
closed: S13 2026-05-26
---

## Problem

`generate_ticket_index.py` emits `*(none)*` as the aging-section body when no stale tickets
exist. `surface_stale_tickets.py` regex-matches `^\*\(none\)\*` to detect that clean state.
The literal string is duplicated across two files with no shared constant. A maintainer who
changes one and forgets the other reintroduces format-drift ambiguity (the very bug T053 #6
was meant to fix).

## Acceptance Criteria

- [x] Define `AGING_EMPTY_MARKER = "*(none)*"` in a shared module (`ticket_constants.py`).
- [x] Both `generate_ticket_index.py` and `surface_stale_tickets.py` reference the constant.
- [x] All existing tests still pass (the marker value does not change).

## Notes

Minor. No behaviour change — purely a maintainability improvement.

## Resolution
Created ticket_constants.py with AGING_EMPTY_MARKER = '*(none)*'; updated generate_ticket_index.py (lines 140, 182) and surface_stale_tickets.py (line 61 regex) to import and use the constant instead of hardcoded literals.

Closed S13 2026-05-26.
