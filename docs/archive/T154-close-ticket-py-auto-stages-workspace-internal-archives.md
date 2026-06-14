---
id: T154
title: close_ticket.py auto-stages workspace internal/ archives
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S29 2026-06-01
closed: S30 2026-06-14
---

## Problem

close_ticket.py fails to stage the archive move when the workspace's internal/ directory is gitignored by the harness repo. Operator must manually git add -f and commit on every workspace ticket close — 5 times in S3 alone.

## Acceptance Criteria

- [x] close_ticket.py runs cleanly on workspace tickets without an add -f follow-up
- [x] Existing harness-root ticket close path is unaffected
- [x] Test covers both paths

### Disposition note (S30)

The title says "auto-stages", but force-staging (`git add -f`) the archive into the
harness repo would commit deliberately-gitignored workspace internal/ files into the
harness layer — a layer-separation violation. Resolved instead by **skipping** staging
when the dest is gitignored (archive move still happens; exit 0 + informational note).
Duplicate of T158, which framed the same fix correctly; both closed by one change.

## Resolution
Duplicate of T158 — resolved by the same change. Disposition: skip staging when the archive dest is gitignored rather than force-add (git add -f), which would leak deliberately-gitignored workspace internal/ files into the harness repo and violate layer separation. See T158 and the disposition note in this ticket.

Closed S30 2026-06-14.
