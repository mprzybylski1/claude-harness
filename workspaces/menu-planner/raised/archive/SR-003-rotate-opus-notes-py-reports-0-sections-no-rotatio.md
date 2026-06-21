---
id: SR-003
from: menu-planner
raised: S4 2026-06-13
title: rotate_opus_notes.py reports '0 sections — no rotation needed' for workspaces/menu-planner/internal/opus_notes.md even though it has 3 '# Opus Review S<N>' sections (S1/S2/S3). It should archive the oldest to keep 2. The header pattern it counts likely doesn't match this workspace's format, so opus_notes grows unbounded across sessions.
severity: low
status: resolved
harness_ticket: T163
resolved_in: S30
---

## Context

(Why this matters, what workspace surfaced it, blocking yes/no.)

## Proposed change

(What the workspace thinks should happen. Harness may disagree.)

## Harness disposition

(Filled by harness on promotion or rejection.)
