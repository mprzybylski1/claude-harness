---
id: T006
title: Multi-repo workspace support
severity: medium
status: open
phase: 2
layer: infra
opened: S002 2026-05-25
closed:
---

## Problem
A workspace may contain multiple repos (e.g. backend + frontend for a single client
engagement). Scripts currently assume a single repo path. Multi-repo workspaces need
static analysis, Opus review, and commit sequences that span all declared repos.

## Acceptance Criteria
- [ ] Static analysis runs against all repos in the workspace (each repo's own `harness.yaml` overrides apply if present)
- [ ] Opus review: primary repo gets deep review; secondary repos get light review only if they have dirty changes in the session
- [ ] Per-repo commit detection: harness iterates workspace repos, detects dirty state per repo, commits in declaration order
- [ ] Ticket frontmatter supports optional `repo:` field (value = repo name from workspace.yaml) to indicate which repo a ticket targets; harness surfaces this in session-start briefing
- [ ] `workspace.py list` shows per-repo names alongside workspace name

## Notes
Depends on T001 (repos list in schema), T004 (per-repo commit sequence scaffolded there).

Single-repo workspaces are a degenerate case of this — no special handling needed once
multi-repo works.

Related: T001, T004, T005 (isolation must hold per-repo too).
