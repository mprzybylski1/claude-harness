---
id: T163
title: rotate_opus_notes.py header pattern misses workspace opus_notes format — grows unbounded
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-14
closed: S30 2026-06-15
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

- [x] Header regex matches the `# Opus Review S<N>` format used in workspace opus_notes.md
      (separator before S<N> made optional + dash-variant tolerant). Verified: now
      detects all 6 sections in menu-planner's live file (was 0).
- [x] Running against the workspace file archives the oldest, leaving **1** section
      (correction: the tool keeps 1 *by design* — Opus appends its review immediately
      after, reaching the steady-state 2. SR-003's "keep 2" described that post-append
      state. The keep-1 mechanism is unchanged; only the regex was broken.)
- [x] Test added: a workspace-format (`# Opus Review S<N>`, no em-dash) opus_notes.md with >2 sections rotates correctly
- [x] Harness-format (em-dash) opus_notes.md still rotates correctly (no regression)

## Resolution
Root cause: _SECTION_RE required the em-dash separator ('# Opus Review — S26') but workspace opus_notes use no separator ('# Opus Review S1 2026-06-11'), so the regex matched 0 sections and never rotated — menu-planner grew to 6 sections. Made the separator optional and dash-variant tolerant: r'^#{1,2} Opus Review (?:[—–-] )?S(\d+)'. Verified it now detects all 6 menu-planner sections (was 0). The keep-1 design (Opus appends after → steady-state 2) is unchanged; corrected T163 AC#2 which mis-stated 'keep 2' (SR-003's framing of the post-append state). 3 tests added (no-em-dash rotate, single-section count, em-dash regression); all 13 rotate tests pass.

Closed S30 2026-06-15.
