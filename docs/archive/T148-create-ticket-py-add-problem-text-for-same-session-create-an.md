---
id: T148
title: create_ticket.py: add --problem TEXT for same-session create-and-close
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S27 2026-05-31
closed: S27 2026-05-31
source: scrabble-score/SR-013
---

## Problem

Promoted from scrabble-score/SR-013.

## Context

`create_ticket.py` accepts `--ac TEXT` (repeatable) to pre-fill acceptance
criteria, but has no symmetric flag for the Problem section of the body. For
same-session create-and-close flows — common when a previous session's work was
left untracked and must be ticketed retroactively — this forces an intermediate
`Edit` to populate the Problem body (and to replace the placeholder `- [ ] (fill
in)` AC) before `close_ticket.py` will run (it refuses on unchecked ACs without
`--force`). Not blocking. Low severity — pure ergonomics.

Surfaced: S14 / T027 (scrabble-score) — retroactively ticketing the prior
session's untracked Turn N work required an extra Edit to fill Problem + check
ACs before close.

## Proposed change

Add `--problem TEXT` to `create_ticket.py`, mirroring the existing `--ac` shape:
the text is written into the body's `## Problem` section in place of the
`(Describe the problem here.)` placeholder. Combined with `--ac`, a single
`create_ticket.py` invocation then produces a close-ready ticket (no intermediate
Edit needed).

## Acceptance Criteria

- [x] `create_ticket.py "title" --problem "..."` writes the text into the ## Problem section
- [x] Without `--problem`, the current placeholder behavior is preserved
- [x] Combined with `--ac`, a single create invocation produces a close-ready ticket (no placeholder residue)

## Resolution
Added --problem TEXT flag to create_ticket.py. Replaces the placeholder in ## Problem. Combined with --ac, produces a close-ready ticket with no placeholder residue.

Closed S27 2026-05-31.
