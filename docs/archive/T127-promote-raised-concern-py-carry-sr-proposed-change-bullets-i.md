---
id: T127
title: promote_raised_concern.py: carry SR Proposed change bullets into harness ticket ACs
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed: S23 2026-05-28
---

## Problem

`promote_raised_concern.py` copies the SR's `## Context` and `## Proposed change`
sections into the harness ticket's `## Problem` body, but the ticket's
`## Acceptance Criteria` always lands as the default `- [ ] (fill in)`
placeholder. When the SR author already enumerated concrete steps as a bullet
or numbered list (which is the recommended SR shape), the operator has to
retype them into the ticket. Promotion should carry that structure across.

## Acceptance Criteria

- [x] Parse bullet or numbered list items from the SR's ## Proposed change section and emit one - [x] <text> AC per item into the new harness ticket
- [x] Fall back to today's - [x] (fill in) placeholder if no parseable list is found
- [x] Operator can still hand-edit before close (ACs are pre-populated, not locked)
- [x] Tests cover: bullet list parsed, numbered list parsed, prose-only fallback, mixed bullets-and-prose

## Resolution
Added _extract_proposed_change_acs(text) which parses bullet (-/*) and numbered (1./1)) list items from the SR's ## Proposed change section, with H2-boundary handling that mirrors _extract_body. main() forwards each item as a separate --ac flag to create_ticket.py. Prose-only sections produce zero items and create_ticket.py keeps its default '- [ ] (fill in)' placeholder; mixed bullets+prose extracts only the bullets. ACs are pre-populated, not locked — operator can still hand-edit before close. 4 new TestProposedChangeACs tests: bullets, numbered, prose-only fallback, mixed bullets+prose. All 23 promote tests pass.

Closed S23 2026-05-28.
