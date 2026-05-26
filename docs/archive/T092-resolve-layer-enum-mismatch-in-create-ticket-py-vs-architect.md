---
id: T092
title: Resolve layer: enum mismatch in create_ticket.py vs architecture_invariants.md
severity: low
status: closed
phase: 2
layer: tooling
opened: S19 2026-05-26
closed: S19 2026-05-26
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] architecture_invariants.md enum updated to include 'tooling'
- [x] create_ticket.py --layer CLI arg added with validation against enum

## Resolution
Added 'tooling' to layer enum in docs/opus_review_context.md (where Opus reads the template). Added --layer CLI arg to create_ticket.py with choices validation against all valid values. Added --repo arg (T093) and O_CREAT|O_EXCL write (T094) in the same edit pass.

Closed S19 2026-05-26.
