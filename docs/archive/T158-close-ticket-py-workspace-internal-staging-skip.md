---
id: T158
title: close_ticket.py workspace-internal staging skip
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-02
closed: S30 2026-06-14
source: menu-planner/SR-002
---

## Problem

When closing a workspace ticket, close_ticket.py --commit tries to git add files in workspaces/*/internal/ which is gitignored at the harness level. Archive move succeeds but staging always fails. Forces --force on every workspace close.

## Acceptance Criteria

- [x] Detect when target path is gitignored in the harness repo and skip staging rather than error
- [x] Exit success when archive move + INDEX regen succeed even if no staging occurred
- [x] Stderr note explaining the skip

## Resolution
close_ticket.py now detects when the archive dest is gitignored (workspace internal/ dirs are gitignored at the harness level) and skips git staging gracefully — archive move still happens, exit 0, with an informational NOTE instead of a 'staging failed' error. The --commit path skips the commit (with a note) when nothing tracked was staged, rather than failing 'nothing to commit'. New helper _nothing_staged; new tests in tests/test_close_ticket_workspace_internal.py. Resolves the manual 'git add -f' on every workspace close.

Closed S30 2026-06-14.
