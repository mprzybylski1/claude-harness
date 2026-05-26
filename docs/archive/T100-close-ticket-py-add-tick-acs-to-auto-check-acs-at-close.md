---
id: T100
title: close_ticket.py: add --tick-acs to auto-check ACs at close
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S19 2026-05-26
closed: S19 2026-05-26
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] --tick-acs flag rewrites all '- [x]' to '- [x]' in the ACs section before close
- [x] --tick-acs is mutually exclusive with --force (--force skips the gate; --tick-acs asserts pass)
- [x] Test covers ticket with 3 unchecked ACs and asserts close succeeds and ticket shows all checked

## Resolution
Added --tick-acs flag (mutually exclusive with --force via argparse group). _tick_acs() rewrites all '- [ ]' boxes to '- [x]' in content before the AC gate check, so close proceeds normally. The ticked content is written to archive, making the check-off permanent. 3 tests added.

Closed S19 2026-05-26.
