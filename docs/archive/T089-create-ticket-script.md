---
id: T089
title: create_ticket.py script for ticket scaffolding
severity: medium
status: closed
phase: 2
layer: tooling
opened: S18 2026-05-26
closed: S18 2026-05-26
---

## Problem

Creating a new ticket today requires 5+ tool calls: scan `docs/archive/` to find the
last T-number, read an existing ticket to copy the frontmatter shape, then manually
`Write` the full YAML + AC skeleton, then run `generate_ticket_index.py`. This
recurs in every workflow-review and Opus-review-followup session.

S18 workflow-review finding #1.

## Acceptance Criteria

- [x] `create_ticket.py "Title" --severity high --phase 2` creates
      `docs/tickets/open/T<next>-title-slug.md` with correct frontmatter
      (id, title, severity, status=open, phase, layer=tooling, opened=<session> <date>,
      closed blank).
- [x] Auto-picks the next T-number by scanning `open/` and `archive/` for the
      highest existing ID.
- [x] `--ac "..."` (repeatable flag) adds `- [ ] <ac text>` bullets; if omitted,
      inserts a single `- [ ] (fill in)` placeholder.
- [x] `--workspace SLUG` routes to the workspace's `tickets/open/` directory.
- [x] Regenerates the appropriate `INDEX.md` after writing the file.
- [x] Prints the created file path on success.
- [x] Tests: happy path (file created, correct frontmatter), auto-ID (max+1),
      workspace routing, `--ac` flag.

## Resolution
Implemented scripts/tools/create_ticket.py: auto-picks next T-number across harness root + all workspace open/ and archive/ dirs, writes frontmatter template, supports --severity, --phase, --ac (repeatable), --workspace SLUG, regenerates INDEX.md, prints created path. 7 tests.

Closed S18 2026-05-26.
