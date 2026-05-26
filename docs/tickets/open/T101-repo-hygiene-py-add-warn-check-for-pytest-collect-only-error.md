---
id: T101
title: repo_hygiene.py: add WARN check for pytest --collect-only errors
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S19 2026-05-26
closed:
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [ ] repo_hygiene.py --warn-only runs pytest --collect-only -q and reports any import errors
- [ ] WARN line names the test file and the failing import
- [ ] Check is best-effort: missing pytest does not fail the script

## Resolution
(Fill in on close.)
