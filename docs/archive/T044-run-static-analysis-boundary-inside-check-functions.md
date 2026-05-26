---
id: T044
title: S1 #3 — run_static_analysis boundary check inside check functions
severity: low
status: closed
phase: 2
layer: infra
opened: S9 2026-05-26
closed: S13 2026-05-26
---

## Problem

`scripts/tools/run_static_analysis.py:72-84` — `assert_workspace_boundary(primary, ws)` is
called once before `_run_checks_for_repo`. The check functions (`check_test_syntax`,
`check_no_utcnow`, etc., imported from `prepare_opus_context`) receive `scan_root` and walk
it internally via `rglob`. If any check function follows a symlink that escapes `scan_root`
(or constructs a relative path like `repo_root / ".." / "other"`), Invariant 5 is violated
silently.

First flagged S1 #3, still open at S8. Diff suggests check functions only use
`scan_root`-anchored `rglob`, making actual exploitation unlikely. Defense-in-depth item.

## Acceptance Criteria

- [x] Check functions in `prepare_opus_context.py` either:
      (a) anchor all file opens to `scan_root` and never construct paths outside it, OR
      (b) have an explicit boundary assertion before any file open. (`check_test_syntax` now uses `_is_within_root()` to skip out-of-boundary symlinks; others confirmed safe.)
- [x] OR: `_run_checks_for_repo` walks results and validates each file is under `scan_root`
      before including in output.
- [x] Integration test: workspace with a symlink to outside the repo → `run_static_analysis`
      exits 2 or skips the symlinked file. (8 tests in `test_static_analysis_symlink_boundary.py`)
- [x] All existing tests still pass.

## Notes

Low urgency: requires audit of all check functions in prepare_opus_context.py. Address
in a dedicated hardening pass. Do not mix with other carry-forward tickets.

## Resolution
Audited all check functions in prepare_opus_context.py. check_test_syntax was genuinely vulnerable — symlinks inside scan_root pointing outside were compiled without boundary check. Added _is_within_root() helper; check_test_syntax now skips out-of-boundary symlinks. check_utcnow (grep -r) and check_bash_blocks confirmed safe and documented. run_static_analysis.py annotated with per-function guarantees. 8 integration tests added in test_static_analysis_symlink_boundary.py.

Closed S13 2026-05-26.
