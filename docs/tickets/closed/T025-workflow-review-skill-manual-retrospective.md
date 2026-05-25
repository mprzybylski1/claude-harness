---
id: T025
title: workflow-review skill — manual session retrospective
severity: medium
status: closed
phase: 1
layer: infra
opened: S5 2026-05-25
closed: S5 2026-05-25
---

## Problem

There is no structured way to capture workflow friction and turn it into harness
improvements. When a session is slow, requires workarounds, or reveals gaps in the
harness (e.g. a script ignoring workspace paths), the insight lives only in the
conversation and is never acted on systematically. The session-close Opus review
catches code quality issues but not workflow process issues.

## Acceptance Criteria

- [x] New skill at `.claude/skills/workflow-review/SKILL.md`.
- [x] Skill prompts Claude to reflect on the current session's workflow: what
      scripts were called multiple times, what workarounds were needed, what
      tool calls failed or required retries, what friction was felt during
      session-start / implementation / session-close.
- [x] Output is structured: **Friction points** (what was slow or awkward),
      **Root causes** (why each friction point exists), **Suggested improvements**
      (concrete harness changes), **Proposed tickets** (one per actionable finding).
- [x] For each proposed ticket, Claude drafts the ticket in full (id, title, severity,
      problem, ACs) and asks the user to confirm before writing to disk.
- [x] Skill is callable standalone (`/workflow-review`) and as an optional step
      within `/session-close` (noted in session-close SKILL.md as "Step X — optional
      workflow review").
- [x] All existing tests still pass.

## Notes

Option C from the workflow observability design discussion. Relies on Claude's
in-session memory rather than hard telemetry data — lower fidelity than T026 but
zero infrastructure cost and immediately useful.

Pairs with T026 (hook-logged telemetry) which will eventually provide hard numbers
to complement the qualitative retrospective.

## Resolution

Created `.claude/skills/workflow-review/SKILL.md` in S5. Five-step structure: gather session context, systematic reflection across 5 categories (script friction, SKILL gaps, workspace/path issues, missing automation, cross-session signals), structured retrospective output, ticket proposal loop with per-ticket confirmation, optional sessions.md note. Added `/workflow-review` pre-check prompt to session-close SKILL.md alongside the existing `/implementation-review` pre-check.
