---
id: T164
title: test_workflow_orchestrator.py imports missing scripts/workflows/implement_ticket module
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-14
closed: S30 2026-06-15
---

## Problem

13 tests in tests/test_workflow_orchestrator.py fail with 'ImportError: cannot import name implement_ticket from scripts.workflows'. The package scripts/workflows/ contains only __init__.py (empty) and lib/; the orchestrator module the tests import (from scripts.workflows import implement_ticket; implement_ticket.run_workflow(...)) does not exist. Pre-existing on master (confirmed by stashing S30 work — fails without any S30 changes). Either implement_ticket.py was removed/renamed or never committed, or the tests are stale. The implement-background skill drives a Python orchestrator, so the skill itself may also be broken.

## Acceptance Criteria

- [x] Determine via git history whether implement_ticket.py was removed/renamed or never committed
      → **never committed**: no log entry ever touched `*implement_ticket*`; only the `lib/`
      primitives and the tests were committed. The orchestrator was written against an unbuilt module.
- [x] Either restore/relocate the orchestrator module or update the tests to the current entry point
      → restored `scripts/workflows/implement_ticket.py` (`run_workflow` + `main`) wiring the existing
      lib primitives to the 12-outcome contract the tests define.
- [x] tests/test_workflow_orchestrator.py passes (the 13 currently-failing tests go green) → 15/15 pass.
- [x] Confirm the implement-background skill's orchestrator entry point matches reality
      → `python -m scripts.workflows.implement_ticket T###` works (prints usage + exit 2 with no args).

### Follow-up flagged (not in scope)

`prompt_builder.py` and the guard lists (`watcher.DENIED_PATHS`, `git_ops._SAFETY_PREFIXES`)
are written for an "Autonomous AI Trading Company" (`core/`, `execution/`, `strategies/`,
`config.yaml`, `infra/audit_log.py`) — none of which exist in the harness. Run against the
harness, the safety guards are inert. The orchestrator + lib were evidently copied from a
trading project with their tests but never adapted. Raise a separate ticket if the harness is
meant to actually run `/implement-background` (vs. keeping it as a tested portfolio artifact).

## Resolution
Root cause: scripts/workflows/implement_ticket.py was never committed — only the lib/ primitives (git_ops, watcher, agent_runner, hash_guard, prompt_builder, notifier) and the tests were. Restored the orchestrator: run_workflow() sequences preconditions (ALREADY_RUNNING lock / DIRTY_WORKING_TREE / AGENT_UNAVAILABLE), spawns the agent with a stderr-drain thread, runs the DenylistWatcher, then post-checks in priority order (credit exhaustion, hash-guard, unauthorized commit, tests, static analysis) and routes clean runs to AWAITING_REVIEW / AWAITING_ARCHITECTURE_REVIEW, reverting (git reset --hard + clean -fd) on every failure path. main() backs the 'python -m scripts.workflows.implement_ticket T###' entry the implement-background skill documents. 15/15 orchestrator tests pass; full suite 589 green. Flagged separately: the prompt/guard paths target a trading project, not the harness.

Closed S30 2026-06-15.
