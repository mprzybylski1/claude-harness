---
id: T098
title: close_ticket.py: validate gitignored --files paths upfront before moving ticket
severity: high
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

- [ ] close_ticket.py runs git check-ignore on all --files paths before any state change
- [ ] If any path is gitignored, script exits non-zero with a clear error; ticket stays in open/
- [ ] Test covers a gitignored file in --files and asserts no ticket-move occurs

## Resolution
(Fill in on close.)
