---
id: T100
title: close_ticket.py: add --tick-acs to auto-check ACs at close
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S19 2026-05-26
closed:
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [ ] --tick-acs flag rewrites all '- [ ]' to '- [x]' in the ACs section before close
- [ ] --tick-acs is mutually exclusive with --force (--force skips the gate; --tick-acs asserts pass)
- [ ] Test covers ticket with 3 unchecked ACs and asserts close succeeds and ticket shows all checked

## Resolution
(Fill in on close.)
