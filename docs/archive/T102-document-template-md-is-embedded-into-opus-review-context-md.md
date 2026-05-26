---
id: T102
title: Document TEMPLATE.md is embedded into opus_review_context.md
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S19 2026-05-26
closed: S19 2026-05-26
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] TEMPLATE.md (or CLAUDE.md Configuration section) notes that it's embedded into the generated opus_review_context.md by prepare_opus_context.py
- [x] Note is brief (one line)

## Resolution
Added one HTML comment to docs/tickets/TEMPLATE.md noting that it's embedded verbatim into docs/opus_review_context.md by prepare_opus_context.py. Future editors now know where to look when the Opus-visible template needs to change.

Closed S19 2026-05-26.
