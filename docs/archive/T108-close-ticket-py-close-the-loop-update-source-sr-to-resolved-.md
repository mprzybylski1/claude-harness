---
id: T108
title: close_ticket.py close-the-loop: update source SR to resolved on ticket close
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

- [x] When closing a harness ticket with source: <slug>/SR-NNN frontmatter, close_ticket.py reads and updates the referenced SR file
- [x] SR file updated to: status: resolved, resolved_in: S<N>
- [x] SR update staged together with the ticket archive move in one transaction (single commit)
- [x] No-op when ticket has no source: field (existing close behaviour unchanged)
- [x] Regression test: promote+close round-trip correctly mutates both ticket and SR file

## Resolution
Added _parse_source() and _resolve_source_sr() to close_ticket.py. When a ticket has source: <slug>/SR-NNN frontmatter, the SR is updated (status→resolved, resolved_in→S<N>) and staged as part of the same transaction. No-op when source: is absent. Missing SR file warns but does not block the close.

Closed S20 2026-05-27.
