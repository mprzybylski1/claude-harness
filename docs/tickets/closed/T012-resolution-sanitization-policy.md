---
id: T012
title: Define and enforce Resolution text sanitization policy for client progress
severity: medium
status: closed
phase: process
layer: process
opened: S1 2026-05-25
closed: S2 2026-05-25
---

## Problem

`scripts/tools/generate_client_progress.py` copies the first sentence of ticket `## Resolution`
verbatim into `client/progress.md`. Internal details — file paths, Slack handles, internal PR
links, internal jargon — leak to clients without any filtering. The session summary described
it as "sanitised client-facing output" but no sanitisation is actually applied.

## Acceptance Criteria

**Decision: Option A** — explicit policy, no code change. Revisit Option B when the first real client workspace is created.

Option A (explicit policy, no code change):
- [x] `docs/tickets/TEMPLATE.md` Resolution section is annotated: "First sentence is shown
  verbatim to clients — write as a user-facing statement."
- [x] `session-close/SKILL.md` notes the same constraint

## Notes

Opus S1 finding #4. Option A is safer for now — no complex regex sanitization that could
over-filter. Revisit when the first real client workspace is created.

## Resolution

Implemented Option A: annotated the `## Resolution` section in `docs/tickets/TEMPLATE.md` with a client-visible warning, and added a matching note to the "Generate client progress" step in `.claude/skills/session-close/SKILL.md`. No code changes — policy-only. Automated sanitization deferred until the first real client workspace is exercised.
