---
id: T106
title: promote_raised_concern.py — accept SR, open harness ticket, stamp raised file
severity: high
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

- [x] Script exists at scripts/tools/promote_raised_concern.py <slug>/SR-NNN
- [x] Creates a harness ticket via create_ticket.py pipeline; copies title/severity/body from SR
- [x] Stamps new ticket frontmatter with source: <slug>/SR-NNN
- [x] Updates raised file atomically: status: promoted, harness_ticket: T###
- [x] Refuses if SR is not in raised status
- [x] Regression test: promote round-trip correctly mutates both files in one transaction

## Resolution
Implemented promote_raised_concern.py: finds SR by slug/SR-NNN, validates status=raised, creates harness ticket via create_ticket.py (using __file__-relative path for sibling invocation), stamps source: field and injects Context+Proposed change into Problem section, updates SR status→promoted and harness_ticket→T###.

Closed S20 2026-05-27.
