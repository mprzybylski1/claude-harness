---
id: T101
title: repo_hygiene.py: add WARN check for pytest --collect-only errors
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S19 2026-05-26
closed: S19 2026-05-26
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] repo_hygiene.py --warn-only runs pytest --collect-only -q and reports any import errors
- [x] WARN line names the test file and the failing import
- [x] Check is best-effort: missing pytest does not fail the script

## Resolution
Added check_test_imports(tests_dir) to repo_hygiene.py. Runs 'python -m pytest --collect-only -q <tests_dir>' and emits a WARN finding for each ERROR/ImportError/ModuleNotFoundError line. Best-effort: missing pytest or dir absence returns []. Accepts --tests-dir PATH for testability. 3 tests added in test_repo_hygiene.py.

Closed S19 2026-05-26.
