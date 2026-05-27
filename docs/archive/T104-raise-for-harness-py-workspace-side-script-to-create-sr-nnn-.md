---
id: T104
title: raise_for_harness.py — workspace-side script to create SR-NNN boundary files
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

- [x] Script exists at scripts/tools/raise_for_harness.py
- [x] Allocates next SR-NNN by scanning workspaces/<slug>/raised/ + archive/
- [x] Resolves workspace slug from workspace.yaml; refuses if no workspace context
- [x] Writes correctly-formatted YAML frontmatter (id, from, raised, title, severity, status: raised, harness_ticket: empty)
- [x] Regression test: file created in correct path; duplicate SR number rejected

## Resolution
Implemented raise_for_harness.py with O_CREAT|O_EXCL retry loop, CWD-based workspace detection, raised/archive/ scanning for sequence allocation, and template with all required frontmatter fields and section stubs.

Closed S20 2026-05-27.
