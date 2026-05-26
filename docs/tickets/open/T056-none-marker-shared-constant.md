---
id: T056
title: S10 — *(none)* aging marker duplicated across generator and consumer
severity: low
status: open
phase: 2
layer: infra
opened: S10 2026-05-26
closed:
---

## Problem

`generate_ticket_index.py` emits `*(none)*` as the aging-section body when no stale tickets
exist. `surface_stale_tickets.py` regex-matches `^\*\(none\)\*` to detect that clean state.
The literal string is duplicated across two files with no shared constant. A maintainer who
changes one and forgets the other reintroduces format-drift ambiguity (the very bug T053 #6
was meant to fix).

## Acceptance Criteria

- [ ] Define `EMPTY_AGING_MARKER = "*(none)*"` in a shared module (e.g. `workspace_config.py`
      or a new `ticket_index_constants.py`).
- [ ] Both `generate_ticket_index.py` and `surface_stale_tickets.py` reference the constant.
- [ ] All existing tests still pass (the marker value does not change).

## Notes

Minor. No behaviour change — purely a maintainability improvement.

## Resolution
(Fill in on close.)
