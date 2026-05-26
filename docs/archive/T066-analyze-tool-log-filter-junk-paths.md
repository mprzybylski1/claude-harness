---
id: T066
title: analyze_tool_log.py top-edited shows junk Bash tokens
severity: low
status: closed
phase: process
layer: process
opened: S13 2026-05-26
closed: S14 2026-05-26
---

## Problem

`analyze_tool_log.py --session SNN` shows a "Top edited files" table that includes
false positives from Bash command substrings. For example, `foo.py` appeared 6 times
in the S13 report because it matched as a substring in multiple Bash commands that
contained `foo.py` as a parameter (not a file path being edited).

The path extraction for Bash commands in `log_tool_usage.py` returns tokens that start
with `/` or `~/`, which is correct. But `analyze_tool_log.py` counts the `path` field
for all tool types uniformly — for Bash rows, that field holds the first 120 characters
of the command string, not a file path. The `path` column is a heterogeneous mix of
real file paths (Edit/Write/Read) and raw command snippets (Bash/Agent).

The fix is to filter the "Top edited files" section to only count rows where `tool` is
in `{Edit, Write, NotebookEdit}`, excluding Bash and Agent rows entirely.

## Acceptance Criteria

- [x] `analyze_tool_log.py` "Top edited files" section only counts rows where `tool` is
  `Edit`, `Write`, or `NotebookEdit`.
- [x] Bash and Agent rows are excluded from this table (they may still appear in other
  sections like "Tool call counts").
- [x] Existing output format is preserved for all other sections.
- [x] A test or manual verification confirms `foo.py` no longer appears as a top-edited
  file when only present as a Bash command substring.

## Notes

Found during S13 workflow review. Low urgency — cosmetic, doesn't affect session
tracking correctness.

## Resolution

Investigation in S14 found the filter was already implemented from the initial commit (T026): _top_files filters by edit_tools={'Edit','Write','NotebookEdit'}. Added test_bash_paths_excluded_from_top_edited_files to confirm the behavior is correct and protected against regression.

Closed S14 2026-05-26.
