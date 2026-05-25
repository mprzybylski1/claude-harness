---
id: T012
title: Define and enforce Resolution text sanitization policy for client progress
severity: medium
status: open
phase: process
layer: process
opened: S1 2026-05-25
closed:
---

## Problem

`scripts/tools/generate_client_progress.py` copies the first sentence of ticket `## Resolution`
verbatim into `client/progress.md`. Internal details — file paths, Slack handles, internal PR
links, internal jargon — leak to clients without any filtering. The session summary described
it as "sanitised client-facing output" but no sanitisation is actually applied.

## Acceptance Criteria

Option A (explicit policy, no code change):
- [ ] `docs/tickets/TEMPLATE.md` Resolution section is annotated: "First sentence is shown
  verbatim to clients — write as a user-facing statement."
- [ ] `session-close/SKILL.md` notes the same constraint

Option B (automated sanitisation):
- [ ] `generate_client_progress.py` filters internal-pattern strings (absolute paths,
  @-handles, http://internal.*, T\d+ ticket refs) before writing to `client/progress.md`
- [ ] Test: Resolution containing `/home/user/...` is not written to client output

Pick one option and document the decision.

## Notes

Opus S1 finding #4. Option A is safer for now — no complex regex sanitization that could
over-filter. Revisit when the first real client workspace is created.

## Resolution
