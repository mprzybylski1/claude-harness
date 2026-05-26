---
id: T093
title: Add --repo flag to create_ticket.py for workspace tickets
severity: low
status: closed
phase: 2
layer: tooling
opened: S19 2026-05-26
closed: S19 2026-05-26
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] create_ticket.py accepts --repo SLUG and emits repo: &lt;slug&gt; in frontmatter when provided
- [x] Omitting --repo leaves repo: commented out as today

## Resolution
Added --repo SLUG flag to create_ticket.py; emits 'repo: <slug>' in frontmatter when provided, leaves commented-out placeholder otherwise. Implemented alongside --layer (T092) and O_CREAT|O_EXCL write (T094) in the same create_ticket.py edit pass.

Closed S19 2026-05-26.
