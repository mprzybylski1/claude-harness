---
id: T160
title: close_ticket.py auto-pass ACs when --resolution given
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-02
closed: S30 2026-06-14
---

## Problem

close_ticket.py blocks on unchecked ACs unless --force. The natural flow is fix code then close ticket. Editing AC checkboxes manually is extra friction. When --resolution is given with a substantive message, the operator has already verified the work.

## Acceptance Criteria

- [x] A flag that ticks all AC boxes before validation exists — it's `--tick-acs`,
      added in T098 (`a3e9ca5`). No new flag needed; AC(a) already satisfied.
- [x] AC(b) "default --force when --resolution given" **rejected as unsafe** —
      `--resolution` is near-universal, so auto-forcing would silently disable
      AC-blocking entirely, gutting the verification gate. Recorded decision, not a build.
- [x] Existing unchecked-AC blocking still works when no override (`--force`/`--tick-acs`) is given.
- [x] `--tick-acs` help text clarified to surface it as the explicit alternative to manual AC ticking.

## Resolution
Closed as already-resolved + recorded decision. AC(a) (a flag that ticks all AC boxes) is already provided by --tick-acs (added T098); no new flag built. AC(b) (auto-force when --resolution is given) rejected as unsafe — --resolution is near-universal, so it would silently disable AC-blocking, the verification gate relied on this session. Only change: clarified --tick-acs help text to surface it as the explicit alternative to manual AC ticking.

Closed S30 2026-06-14.
