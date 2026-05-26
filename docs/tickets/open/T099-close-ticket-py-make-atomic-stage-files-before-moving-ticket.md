---
id: T099
title: close_ticket.py: make atomic — stage --files before moving ticket
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

- [ ] Reorder operations so --files validation and staging happen before the ticket file is moved to archive
- [ ] If staging fails for any reason, ticket remains in open/ and INDEX is untouched
- [ ] Test covers a failure path (e.g. nonexistent --files path) and asserts ticket stays in open/

## Resolution
(Fill in on close.)
