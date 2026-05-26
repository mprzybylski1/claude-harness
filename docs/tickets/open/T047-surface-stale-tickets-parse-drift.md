---
id: T047
title: Fix surface_stale_tickets.py parse format drift
severity: low
status: open
phase: 2
layer: tooling
opened: S9 2026-05-26
closed:
---

## Problem

Session-start emits `WARNING: surface_stale_tickets.py could not parse INDEX.md aging
section — format may have drifted` on every harness-root session and continues silently.
The warning is visible but not actionable, and has persisted across multiple sessions
without being fixed. A WARN that fires every session and is never resolved is noise that
degrades signal quality.

Surfaced by workflow-review S9.

## Acceptance Criteria

- [ ] `surface_stale_tickets.py` parses the current `generate_ticket_index.py` output
      format correctly (or the generator is updated to emit the expected format).
- [ ] No WARNING emitted during a normal harness-root session-start.
- [ ] Test: pipe current INDEX.md output through `surface_stale_tickets.py` and assert
      exit 0 with no WARNING.

## Resolution
(Fill in on close.)
