---
id: T019
title: Workspace scaffold must not silently overwrite existing docs files
severity: medium
status: closed
phase: 2
layer: tools
opened: S4 2026-05-25
closed: S4 2026-05-25
---

## Problem

`workspace.py _scaffold` + `_write_initial_files` use `write_text` without an overwrite
check. If the user specifies a docs_path that already contains sessions.md, tickets/,
or opus_notes.md (e.g. migrating an existing workspace), those files are silently
overwritten with empty templates — data loss with no warning.

## Acceptance Criteria

- [x] Before writing any initial file, check if it already exists at docs_path
- [x] If existing files are found, print a clear error message and abort (do not
  overwrite without explicit confirmation)
- [x] Test: create with existing sessions.md at docs_path is rejected
- [x] All existing tests still pass

## Resolution

S4 2026-05-25: Workspace create now refuses to scaffold over an existing docs_path directory that already contains workspace files.

Added a pre-check in `cmd_create` before `ws_dir.mkdir()`: if docs_path already has `sessions.md`, `opus_notes.md`, or `tickets/INDEX.md`, exits 1 with a message listing the conflicting files. 1 new test; 70/70 pass.
