---
id: T107
title: reject_raised_concern.py — reject SR with reason, write terminal status
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S20 2026-05-27
closed: S20 2026-05-27
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] Script exists at scripts/tools/reject_raised_concern.py <slug>/SR-NNN --reason '...'
- [x] Updates raised file: status: rejected, resolved_in: S<N>
- [x] Appends reason to ## Harness disposition section in the SR file
- [x] Refuses if SR is already in a terminal status (resolved/rejected)
- [x] Regression test: rejected file has correct terminal fields and disposition body

## Resolution
Implemented reject_raised_concern.py: validates non-terminal status, writes status→rejected and resolved_in→S<N> (inserting field if absent for legacy SRs), replaces/appends reason in ## Harness disposition. Also added resolved_in: to raise_for_harness.py template for future SRs.

Closed S20 2026-05-27.
