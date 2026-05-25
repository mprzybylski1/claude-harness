---
id: T029
title: harness.yaml code_paths missing scripts/ — harness sessions misclassified
severity: medium
status: closed
phase: 2
layer: infra
opened: S5 2026-05-25
closed: S6 2026-05-25
---

## Problem

`harness.yaml` `code_paths` is configured as `[src/, lib/, tests/]` — none of which
match the harness's own production code in `scripts/tools/` and `scripts/hooks/`.

A session that touches only `scripts/tools/` (e.g. T020–T025 without test changes)
would be classified as "docs" and skip full Opus review. S5 was rescued only because
`tests/` were modified alongside the scripts.

Opus S5 finding #11.

## Acceptance Criteria

- [x] `harness.yaml` `code_paths` includes `"scripts/"` (covers both `scripts/tools/`
      and `scripts/hooks/`)
- [x] `classify_session.py` is verified to return "code" for a change to
      `scripts/tools/some_tool.py` with the updated config
- [x] `CODE_PREFIXES` docstring in `classify_session.py` updated to match

## Notes

Quick fix — one-line change to `harness.yaml` plus a test assertion. Sequence before
any session that only touches scripts/ without also touching tests/.

## Resolution

S6 2026-05-25: Added `"scripts/"` to `code_paths` in `harness.yaml`. Updated `classify_session.py` docstring to reflect current defaults. Test added in `TestHarnessYamlCodePaths` asserting `scripts/` prefix is present.

ACs:
- [x] `harness.yaml` `code_paths` includes `"scripts/"`
- [x] `classify_session.py` verified to return "code" for scripts/ changes (covered by T027 tests)
- [x] `CODE_PREFIXES` docstring updated
