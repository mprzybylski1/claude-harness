---
id: T154
title: close_ticket.py auto-stages workspace internal/ archives
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S29 2026-06-01
closed:
---

## Problem

close_ticket.py fails to stage the archive move when the workspace's internal/ directory is gitignored by the harness repo. Operator must manually git add -f and commit on every workspace ticket close — 5 times in S3 alone.

## Acceptance Criteria

- [ ] close_ticket.py runs cleanly on workspace tickets without an add -f follow-up
- [ ] Existing harness-root ticket close path is unaffected
- [ ] Test covers both paths

## Resolution
(Fill in on close.)
