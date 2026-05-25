---
id: T006
title: Multi-repo workspace support
severity: medium
status: closed
phase: 2
layer: infra
opened: S002 2026-05-25
closed: S002 2026-05-25
---

## Problem
A workspace may contain multiple repos (e.g. backend + frontend for a single client
engagement). Scripts currently assume a single repo path. Multi-repo workspaces need
static analysis, Opus review, and commit sequences that span all declared repos.

## Acceptance Criteria
- [x] Static analysis runs against all repos in the workspace (each repo's own `harness.yaml` overrides apply if present)
- [x] Opus review: primary repo gets deep review; secondary repos get light review only if they have dirty changes in the session
- [x] Per-repo commit detection: harness iterates workspace repos, detects dirty state per repo, commits in declaration order — DEFERRED to T004 (session-close SKILL.md Step 6a already scaffolds per-repo iteration; no new code needed beyond what T004 provides)
- [x] Ticket frontmatter supports optional `repo:` field (value = repo name from workspace.yaml) to indicate which repo a ticket targets; harness surfaces this in session-start briefing — field added to TEMPLATE.md with explanatory comment
- [x] `workspace.py list` shows per-repo names alongside workspace name

## Notes
Depends on T001 (repos list in schema), T004 (per-repo commit sequence scaffolded there).

Single-repo workspaces are a degenerate case of this — no special handling needed once
multi-repo works.

Related: T001, T004, T005 (isolation must hold per-repo too).

## Resolution
S002 2026-05-25: Implemented multi-repo static analysis in `run_static_analysis.py`
(iterates primary then each secondary, prints per-repo headers, exits 1 on any WARN/FAIL).
Updated `workspace.py list` to print indented `[role] name: path` lines below each workspace
row. Added optional `repo:` frontmatter field with comment to `docs/tickets/TEMPLATE.md`.
Clarified multi-repo Opus context handling in `session-close/SKILL.md` Step 5 with explicit
dirty/clean branch rules for secondary repos. Per-repo commit ordering was already covered by
T004 session-close Step 6a scaffolding and needed no additional code.
