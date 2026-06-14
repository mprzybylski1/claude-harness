---
id: T163
title: rotate_opus_notes.py header pattern misses workspace opus_notes format — grows unbounded
severity: low
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-14
closed:
source: menu-planner/SR-003
---

## Problem

Promoted from menu-planner/SR-003.

`rotate_opus_notes.py` reports "0 sections — no rotation needed" for
`workspaces/menu-planner/internal/opus_notes.md` even though that file has 3
`# Opus Review S<N>` sections (S1/S2/S3). The section-header pattern the script
counts does not match this workspace's header format, so nothing is ever
archived and `opus_notes.md` grows unbounded across sessions.

## Context

Surfaced by the menu-planner workspace (S1 2026-06-11). Not blocking, but every
session appends a review section and none are ever rotated out, so the file —
and the context cost of reading it — grows without bound. Likely affects any
workspace whose opus_notes header format differs from the harness format the
regex was written against.

## Proposed change

Align the header-matching regex with the actual `# Opus Review S<N>` format
written into workspace opus_notes (confirm harness vs. workspace formats match,
or make the pattern tolerant of both). Keep the newest 2 sections, archive the
rest.

## Acceptance Criteria

- [ ] Header regex matches the `# Opus Review S<N>` format used in workspace opus_notes.md
- [ ] Running against menu-planner's 3-section file archives the oldest, keeping 2
- [ ] Test added: a workspace-format opus_notes.md with >2 sections rotates correctly
- [ ] Harness-format opus_notes.md still rotates correctly (no regression)

## Resolution
(Fill in on close.)
