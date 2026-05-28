---
id: T129
title: prepare_opus_context.py: stale tests/test_prepare_opus_context.py reference in docstring + comment
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed: S23 2026-05-28
---

## Problem

Two references in `scripts/tools/prepare_opus_context.py` pointed at the no-longer-existing
`tests/test_prepare_opus_context.py`. The file was split during T124 into
`test_prepare_opus_context_workspace.py` (covers `_is_within_root` and the
static-analysis checks) and `test_prepare_opus_context_large_assets.py`
(covers `_LARGE_ASSET_EXTS` filtering). The stale paths misdirect anyone
following the "update tests when you change the check functions" guidance.

## Acceptance Criteria

- [x] Both occurrences in scripts/tools/prepare_opus_context.py (lines 19 and 230) updated to point at existing test files (tests/test_prepare_opus_context_workspace.py and tests/test_prepare_opus_context_large_assets.py) or removed

## Resolution
Updated two stale references to tests/test_prepare_opus_context.py (lines 19 docstring, ~230 inline comment) to point at the actual current test files: test_prepare_opus_context_workspace.py covers static-analysis checks + _is_within_root, and test_prepare_opus_context_large_assets.py covers the asset filtering. Comments-only change; no functional impact.

Closed S23 2026-05-28.
