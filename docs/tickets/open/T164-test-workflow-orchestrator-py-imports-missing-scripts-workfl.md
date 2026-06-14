---
id: T164
title: test_workflow_orchestrator.py imports missing scripts/workflows/implement_ticket module
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-14
closed:
---

## Problem

13 tests in tests/test_workflow_orchestrator.py fail with 'ImportError: cannot import name implement_ticket from scripts.workflows'. The package scripts/workflows/ contains only __init__.py (empty) and lib/; the orchestrator module the tests import (from scripts.workflows import implement_ticket; implement_ticket.run_workflow(...)) does not exist. Pre-existing on master (confirmed by stashing S30 work — fails without any S30 changes). Either implement_ticket.py was removed/renamed or never committed, or the tests are stale. The implement-background skill drives a Python orchestrator, so the skill itself may also be broken.

## Acceptance Criteria

- [ ] Determine via git history whether implement_ticket.py was removed/renamed or never committed
- [ ] Either restore/relocate the orchestrator module or update the tests to the current entry point
- [ ] tests/test_workflow_orchestrator.py passes (the 13 currently-failing tests go green)
- [ ] Confirm the implement-background skill's orchestrator entry point matches reality

## Resolution
(Fill in on close.)
