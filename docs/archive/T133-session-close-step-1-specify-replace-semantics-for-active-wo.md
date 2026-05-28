---
id: T133
title: session-close Step 1: specify 'replace' semantics for Active Work; repair S22 orphan content
severity: medium
status: closed
phase: 2
layer: process
# repo: <name from workspace.yaml repos list>
opened: S23 2026-05-28
closed: S23 2026-05-28
---

## Problem

S23 session-start surfaced `extract_session_brief.py` warning: "Active Work contains
'Tickets closed:' 2 times — section may not have been fully replaced (orphan content
from prior session)". Inspection confirmed `docs/sessions.md` Active Work had S22's
content followed by an orphan S21 block. Root cause: `.claude/skills/session-close/SKILL.md`
Step 1 says "Update Active Work" without specifying replace-vs-prepend; the model has
interpreted "update" as "prepend" across multiple sessions, silently growing the
section.

## Acceptance Criteria

- [x] .claude/skills/session-close/SKILL.md Step 1 explicitly states: Replace everything between '## Active Work' and the next '---' with new content. Do not prepend.
- [x] The current orphan S21 block in docs/sessions.md Active Work is removed
- [x] No new script (prose/data fix only)

## Resolution
session-close SKILL.md Step 1 now leads with an explicit 'Replace everything between ## Active Work and the next --- horizontal rule' instruction and a post-save verification line pointing at the extract_session_brief.py warning. The orphan S21 block was removed from docs/sessions.md Active Work; extract_session_brief.py runs clean (no orphan warning). Pairs with T134 which adds Stop-hook validation as defense-in-depth.

Closed S23 2026-05-28.
