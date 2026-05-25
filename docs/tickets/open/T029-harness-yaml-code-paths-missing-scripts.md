---
id: T029
title: harness.yaml code_paths missing scripts/ — harness sessions misclassified
severity: medium
status: open
phase: 2
layer: infra
opened: S5 2026-05-25
closed:
---

## Problem

`harness.yaml` `code_paths` is configured as `[src/, lib/, tests/]` — none of which
match the harness's own production code in `scripts/tools/` and `scripts/hooks/`.

A session that touches only `scripts/tools/` (e.g. T020–T025 without test changes)
would be classified as "docs" and skip full Opus review. S5 was rescued only because
`tests/` were modified alongside the scripts.

Opus S5 finding #11.

## Acceptance Criteria

- [ ] `harness.yaml` `code_paths` includes `"scripts/"` (covers both `scripts/tools/`
      and `scripts/hooks/`)
- [ ] `classify_session.py` is verified to return "code" for a change to
      `scripts/tools/some_tool.py` with the updated config
- [ ] `CODE_PREFIXES` docstring in `classify_session.py` updated to match

## Notes

Quick fix — one-line change to `harness.yaml` plus a test assertion. Sequence before
any session that only touches scripts/ without also touching tests/.

## Resolution

(Fill in on close.)
