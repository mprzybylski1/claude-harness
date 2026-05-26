---
id: T083
title: Sweep the 4-session Opus carry-forwards in one commit
severity: low
status: closed
phase: process
layer: process
opened: S17 2026-05-26
closed: S17 2026-05-26
---

## Problem

Three trivial issues have been deferred across at least 4 sessions (S11–S16) without
explanation, generating ~500 tokens of Opus review noise every session:

1. `scripts/tools/close_ticket.py:34` — `_ws_internal_dir` unused import (dead code since
   the T075 refactor moved that logic into `workspace_config`).
2. `scripts/hooks/log_tool_usage.py:108` — `Path(path)` not expanded before workspace
   matching; Bash `~/…` tokens are silently stamped as harness-root instead of the correct
   workspace. S16 fixed `.expanduser()` at the token-extraction site but not at the
   workspace-match call site.
3. `scripts/tools/close_ticket.py` — `_replace_resolution`'s re.sub injection risk (if
   resolution text contains regex metacharacters) and permissive-fallback content
   truncation have no tests. Flagged S11 #5/#6, carried forward each session since.

Each is ≤10 LoC. Cumulative deferral cost exceeds fix cost.

## Acceptance Criteria

- [x] `_ws_internal_dir` import deleted from `close_ticket.py` (or confirmed still used,
      with a comment explaining why). — Confirmed absent; already removed by T075.
- [x] `log_tool_usage.py:108` workspace-match call uses `Path(path).expanduser()`.
      — Already fixed in T073 (line 117 in current code).
- [x] At least 2 tests added for `_replace_resolution`: one with special-char input
      (e.g. `resolution` containing `\n`, `(`, `)`) and one verifying permissive-fallback
      preserves content before and after the placeholder.
      — 4 tests already exist in TestCloseTicketT054 (test_workspace_path_flags.py:947+).
- [x] All existing tests pass.

## Notes

Opus carry-forward references: S11 #4, S11 #5/#6, S12 #15, S13, S14, S15, S16.
S16 Opus explicitly said "Three sessions of deferral on trivial items is a process smell."
This ticket closes that smell.

## Resolution

All three carry-forwards were already resolved by earlier sessions: (1) _ws_internal_dir import is absent from close_ticket.py — removed during T075 refactor; (2) Path(path).expanduser() is already at log_tool_usage.py:117 — fixed in T073; (3) four _replace_resolution tests (strict, permissive-fallback, regex-metachar, no-placeholder) already exist in TestCloseTicketT054. The Opus carry-forward tracking was stale. No code changes needed.

Closed S17 2026-05-26.
