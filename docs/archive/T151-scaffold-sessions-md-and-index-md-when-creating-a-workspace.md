---
id: T151
title: Scaffold sessions.md and INDEX.md when creating a workspace
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S29 2026-06-01
closed: S29 2026-06-01
---

## Problem

workspace.py create creates the directory but leaves sessions.md and tickets/INDEX.md for the user to write by hand. The first session writes them in formats the tooling does not accept (markdown tables, missing Current Phase and Status section). This caused two errors during sub-tracker S1: extract_session_brief.py failed on missing section, then current_session.py failed on table format.

## Acceptance Criteria

- [x] workspace.py create writes sessions.md containing Current Phase and Status, Active Work, and Session Log sections plus an initial S0 YYYY-MM-DD: workspace created log line
- [x] workspace.py create writes an empty tickets/INDEX.md matching the format generate_ticket_index.py produces
- [x] extract_session_brief.py succeeds against a freshly-created workspace with no further edits
- [x] Test: create a temp workspace, run extract_session_brief.py and current_session.py against it without errors

## Resolution
Updated _write_initial_files to produce sessions.md with S0 YYYY-MM-DD: workspace created entry and INDEX.md matching render_index output byte-for-byte. Both extract_session_brief.py and current_session.py succeed against scaffolded workspace.

Closed S29 2026-06-01.
