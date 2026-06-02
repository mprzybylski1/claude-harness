---
id: T160
title: close_ticket.py auto-pass ACs when --resolution given
severity: low
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-02
closed:
---

## Problem

close_ticket.py blocks on unchecked ACs unless --force. The natural flow is fix code then close ticket. Editing AC checkboxes manually is extra friction. When --resolution is given with a substantive message, the operator has already verified the work.

## Acceptance Criteria

- [ ] Add --all-acs-passed flag that checks all AC boxes before validation
- [ ] Alternatively default --force when explicit --resolution text is provided
- [ ] Existing unchecked-AC blocking still works when no --resolution given

## Resolution
(Fill in on close.)
