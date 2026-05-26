---
id: T074
title: generate_ticket_index.py scans --tickets-dir directly, not open/
severity: medium
status: closed
phase: 2
layer: process
opened: S16 2026-05-26
closed: S16 2026-05-26
---

## Problem

`generate_ticket_index.py` when passed `--tickets-dir <ws>/.harness/tickets` scans the
directory directly, not `<ws>/.harness/tickets/open/`. This causes two bugs:

1. `TEMPLATE.md` (or other non-ticket files in the root) is picked up as a phantom `T000`
   row in the generated INDEX.
2. Real open tickets inside `open/` are omitted.

Observed in scrabble-score S4. Workaround: pass `tickets/open/` directly, but both
`session-start` and `session-close` SKILLs document the broken form (`tickets/`), so
SKILL-following operators hit this every workspace session-close.

**Fix:** In `generate_ticket_index.py`, if the passed `--tickets-dir` contains an `open/`
subdirectory, scan that instead. Script-side fix is cheaper than updating both SKILLs and
prevents future SKILL drift.

## Acceptance Criteria

- [x] `generate_ticket_index.py --tickets-dir <dir>` automatically scans `<dir>/open/`
  if that subdirectory exists, otherwise scans `<dir>` directly (backwards-compatible).
- [x] `TEMPLATE.md` at the root of `--tickets-dir` does not appear as a ticket row.
- [x] Real tickets inside `open/` appear correctly in the generated INDEX.
- [x] Existing harness-root invocations (which pass `docs/tickets/`) continue to work.

## Notes

Related to T075 — both are workspace-path-handling gaps in the ticket-index pipeline
surfaced in scrabble-score S4. See `docs/workflow_review_S4_findings.md` finding #1.

## Resolution

Fixed in generate_ticket_index.py main(): after resolving open_dir, auto-descend into open/ subdir if it exists. Backwards-compatible — dirs without open/ subdir are scanned directly as before. Two tests added to test_workspace_path_flags.py: auto-descent with TEMPLATE exclusion, and no-open-subdir backward compat.

Closed S16 2026-05-26.
