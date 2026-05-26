---
id: T043
title: S3 #3 — reduce N YAML loads per hook call in regenerate_ticket_index.py
severity: low
status: open
phase: 2
layer: perf
opened: S9 2026-05-26
closed:
---

## Problem

`scripts/hooks/regenerate_ticket_index.py:55-68` — `_detect_workspace_from_path`'s slow
path iterates ALL workspace directories and loads each `workspace.yaml` on every hook
invocation. The hook fires on every Edit/Write. With many workspaces, this is
O(edits × workspaces) YAML loads per session. Additionally, `_is_ticket_file` sends any
path containing `/tickets/` through the slow path, including false positives like
`/some/dir/tickets/random.md`.

First flagged S3 #3, still open at S8.

Currently only one workspace exists (scrabble-score), so perf impact is minimal. Accept
as a low-priority cleanup.

## Acceptance Criteria

- [ ] `_detect_workspace_from_path` fast path filters by prefix before entering
      workspace iteration loop (e.g. check if `file_path` starts with any
      workspace `docs_path` or `ws_base` prefix before loading YAML).
- [ ] OR: cache the docs_path→ws_dir mapping at module load time.
- [ ] No behaviour change — same workspace detection results.
- [ ] Existing tests still pass.

## Notes

Low urgency: only one workspace currently. Address when backlog permits.

## Resolution
(Fill in on close.)
