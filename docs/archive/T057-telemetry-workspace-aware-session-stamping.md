---
id: T057
title: Telemetry hook stamps wrong session — global cache clobbered by harness/workspace callers
severity: medium
status: closed
phase: 2
layer: infra
opened: S12 2026-05-26
closed: S12 2026-05-26
---

## Problem

`scripts/hooks/log_tool_usage.py:41-62` (`_current_session()`) reads a single shared cache file `.git/CLAUDE_SESSION_ID` to stamp every telemetry record's `session` field. The cache is written by `scripts/tools/current_session.py:43-48` (`persist_session`) every time the tool is run — and the value written is whichever session number was just computed, regardless of which `--sessions` path was passed.

Result: when a session mixes workspace-aware and harness-root callers (e.g. `/session-start` calls `current_session.py --sessions <workspace>/sessions.md`; later a harness-root tool calls `current_session.py` with no flag), the cache flips between the two values. Telemetry records written before the flip are stamped with one number; records written after are stamped with the other.

Observed in this session (S12 2026-05-26):
- Entries 1–6 stamped `"session": "S3"` (scrabble-score next session)
- Entries 7+ stamped `"session": "S12"` (harness-root next session)

Grep-by-session on `session_tool_log.jsonl` is unreliable as a result, which defeats most of the point of telemetry. There is also no `workspace` field, so even with correct session numbers you cannot tell which workspace a tool call belongs to.

## Acceptance Criteria

- [x] Hook stops reading `.git/CLAUDE_SESSION_ID`; session derived from the right `sessions.md` based on detected workspace.
- [x] Workspace detection covers Edit/Write/Read/NotebookEdit (`file_path`) and Bash (path-like tokens in `command`); no match → harness root.
- [x] Every telemetry record includes a `"workspace"` field (slug or `""`).
- [x] `tests/test_telemetry.py` covers: file_path inside workspace repo, Bash command with workspace path, no-match → harness root, stale cache file ignored.
- [x] Manual smoke: `.git/session_tool_log.jsonl` tail shows correct, stable stamps for mixed harness/workspace tool calls.
- [x] Cache file `.git/CLAUDE_SESSION_ID` left intact for session-close; only the hook stops consuming it.

## Notes

- This is one of the three "workspace-blind tools" called out in [[feedback_session_numbering]].
- Path-token extraction for Bash should be permissive (any `/...` or `~/...` substring), but cheap — sessions.md is small and re-read per tool call is acceptable.
- Do not introduce in-process caching across hook invocations (each tool call is a new subprocess).

## Resolution

Telemetry now stamps each tool call with the correct workspace and session number, derived from the workspace's own sessions.md when the tool targets a workspace repo. The hook (scripts/hooks/log_tool_usage.py) detects the workspace by matching tool-input paths against every active workspace's declared repos; Edit/Write/Read/NotebookEdit use file_path, Bash extracts path-like tokens from the command. No match → harness root. Cache file .git/CLAUDE_SESSION_ID is no longer consulted by the hook (kept for session-close). Every record gains a workspace field. 8 new tests in tests/test_telemetry.py; 2 obsolete cache-based tests removed.

Closed S12 2026-05-26.
