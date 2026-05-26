---
id: T094
title: Race-protect create_ticket.py _next_id via O_CREAT|O_EXCL
severity: medium
status: closed
phase: 2
layer: tooling
opened: S19 2026-05-26
closed: S19 2026-05-26
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] dest.write_text replaced with open(dest, 'x') write to prevent clobber on collision
- [x] Collision increments and retries up to N times before failing

## Resolution
Replaced dest.write_text() with open(dest, 'x') in a retry loop (up to 10 attempts). On FileExistsError, calls _next_id() again to get the latest maximum, preventing ID clobbering under concurrent invocations.

Closed S19 2026-05-26.
