---
id: T159
title: close_ticket.py --files cross-repo support
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-02
closed:
---

## Problem

When ticket changes span the harness repo + a workspace project repo, the script rejects with 'out-of-repo --files'. For workspace sessions doing app work, this is the common case. Workaround is manual git commit in project repo then re-running close_ticket without --files.

## Acceptance Criteria

- [ ] Group --files paths by containing git repo
- [ ] Stage + commit per repo with a shared ticket-derived message
- [ ] Reject only when a file path is not inside any known repo

## Resolution
(Fill in on close.)
