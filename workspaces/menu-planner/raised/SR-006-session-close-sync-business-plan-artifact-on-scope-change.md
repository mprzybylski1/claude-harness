---
id: SR-006
from: menu-planner
raised: S22 2026-07-03
title: "Add a session-close checklist step: if the session changed a workspace's business scope/strategy AND that workspace maintains an outward-facing business-plan artifact, sync the artifact before closing so it never drifts from the strategy docs. Menu Planner is the first instance (hosted one-page plan)."
severity: low
status: raised
harness_ticket:
resolved_in:
---

## Context

Menu Planner now maintains a standing **one-page business plan** as a hosted Artifact
(`https://claude.ai/code/artifact/0a56d3c3-1991-4460-b16e-4146ef6b338e`) — the single
glanceable, outside-reader-facing summary of the venture. When strategy changes (revenue
model, staged plan/timeline, MOQ, crowdfunder dates, distribution/email targets, the
preference-engine/creator/data layer, kill-criteria), the plan must be updated or it
misrepresents the business to a co-founder/investor.

A best-effort memory already exists (`feedback_menuplanner_business_plan_sync`), but the
operator asked for a firmer guarantee via the session-close checklist. Not blocking.

## Proposed change

Add a conditional step to the session-close skill (`.claude/skills/session-close/SKILL.md`),
kept generic so it serves any workspace, not just Menu Planner:

> **Business-plan sync (if applicable):** If this session changed the workspace's business
> scope/strategy AND the workspace maintains an outward-facing business-plan artifact, update
> that artifact before closing — `WebFetch` its URL to get the current HTML, edit, then
> redeploy via the `Artifact` tool with `url=<that URL>` (target the same artifact, don't mint
> a new one). Preserve the artifact's stated constraints (for Menu Planner: plain-language
> only, and the device-is-the-business calibration with the data layer kept additive/phase-2).

Where a workspace has such an artifact + its constraints could be recorded per-workspace (e.g.
workspace.yaml or the workspace CLAUDE.md) so the generic step knows what to sync. Menu
Planner's specifics live in `feedback_menuplanner_business_plan_sync` memory.

## Harness disposition

(Filled by harness on promotion or rejection.)
