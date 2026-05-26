---
id: T058
title: log_tool_usage workspace detection — ~/ expansion, silent inner-except, =-chain
severity: medium
status: open
phase: 2
layer: infra
opened: S12 2026-05-26
closed:
---

## Problem

S12 Opus review (Concerns #1, #2, #3, #8, #9, #10) surfaced three robustness gaps in the workspace-detection path added for T057:

1. **`~/` paths in Bash commands never match workspaces** (Concrete bug — REGRESSION introduced this session). `_candidate_paths` accepts tokens starting with `~/`, but `Path("~/foo")` doesn't expand the tilde. Workspaces declare absolute paths, so a Bash command like `cat ~/Documents/Projects/ScrabbleScore/foo.swift` gets stamped as harness-root instead of `scrabble-score`.
2. **`_detect_workspace` inner `except Exception: continue` silently masks cfg errors**. A malformed `workspace.yaml` that makes `is_within_workspace` raise causes the loop to skip that workspace with no log. If all workspaces raise, the call is stamped harness-root with no error trail.
3. **`=`-value extractor mishandles chained `=`**. For `KEY=val=/path`, LHS-strip yields `val=/path` which fails the `startswith("/")` check and gets dropped.
4. **Test gaps**: `=`-stripping has no direct tests; `_detect_workspace` inner-except branch is uncovered; `test_record_includes_workspace_field` only covers workspace match, not harness-root.

## Acceptance Criteria

- [ ] `_candidate_paths` (or its callers) expands `~/` via `Path(path).expanduser()` before passing to `is_within_workspace`. Path-with-tilde Bash commands match their workspace.
- [ ] `_detect_workspace` inner-except calls `_log_error` (subject to T059 rate-limit when that lands) instead of silent `continue`.
- [ ] `=`-value extractor in `_candidate_paths` uses `rsplit("=", 1)` so the right-hand path survives chained `=` tokens; OR document the limitation and accept it.
- [ ] New tests: `--sessions=/path/file` extracted correctly, `KEY=val=/path` extracted correctly, `_detect_workspace` with cfg that raises logs and continues, `test_record_includes_workspace_field` covers harness-root case.

## Notes

All concerns live in `scripts/hooks/log_tool_usage.py` (one file). Bundles cleanly with T059. S12 Opus review #1, #2, #3, #8, #9, #10.

## Resolution

(Fill in on close.)