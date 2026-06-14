---
id: T158
title: close_ticket.py workspace-internal staging skip
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-02
closed:
source: menu-planner/SR-002
---

## Problem

When closing a workspace ticket, close_ticket.py --commit tries to git add files in workspaces/*/internal/ which is gitignored at the harness level. Archive move succeeds but staging always fails. Forces --force on every workspace close.

## Acceptance Criteria

- [ ] Detect when target path is gitignored in the harness repo and skip staging rather than error
- [ ] Exit success when archive move + INDEX regen succeed even if no staging occurred
- [ ] Stderr note explaining the skip

## Resolution
(Fill in on close.)
