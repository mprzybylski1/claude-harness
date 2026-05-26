---
id: T099
title: close_ticket.py: make atomic — stage --files before moving ticket
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

- [x] Reorder operations so --files validation and staging happen before the ticket file is moved to archive
- [x] If staging fails for any reason, ticket remains in open/ and INDEX is untouched
- [x] Test covers a failure path (e.g. nonexistent --files path) and asserts ticket stays in open/

## Resolution
Extracted _stage_extra_files() from _git_stage() and moved it to run BEFORE _atomic_move(). A staging failure (gitignored, nonexistent, not-in-git-repo) now exits before the ticket is touched, guaranteeing the ticket stays in open/ on any --files error. _git_stage() now handles only ticket/archive/INDEX.

Closed S19 2026-05-26.
