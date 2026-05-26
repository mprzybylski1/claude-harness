---
id: T098
title: close_ticket.py: validate gitignored --files paths upfront before moving ticket
severity: high
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

- [x] close_ticket.py runs git check-ignore on all --files paths before any state change
- [x] If any path is gitignored, script exits non-zero with a clear error; ticket stays in open/
- [x] Test covers a gitignored file in --files and asserts no ticket-move occurs

## Resolution
Added _check_gitignored() using 'git check-ignore' to validate all --files paths before any state change. If any path is gitignored, script exits 1 with a clear error and the ticket remains in open/. Covers the T092 regression where passing docs/opus_review_context.md to --files silently moved the ticket.

Closed S19 2026-05-26.
