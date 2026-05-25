---
id: T004
title: Session-close workspace integration
severity: high
status: open
phase: 2
layer: process
opened: S002 2026-05-25
closed: S002 2026-05-25
---

## Problem
`/session-close` commits to and logs state in the harness repo directly. In the workspace
model, session logs belong in the workspace's `internal/`, commits go to workspace repos
(not the harness repo), and Opus review targets the workspace's declared repos.

## Acceptance Criteria
- [x] Session log written to `workspaces/<slug>/internal/sessions.md`, not global `docs/sessions.md`
- [x] Opus review runs against the workspace's declared repos (primary: deep review; secondary: light review if dirty)
- [x] Opus findings written to `workspaces/<slug>/internal/opus_notes.md`
- [x] Per-repo commit sequence: harness detects which workspace repos have staged/unstaged changes and commits them in order before session-close commit
- [x] Harness docs commit (`docs/` only) still goes to harness repo as before
- [x] `update_system_state.py` reads workspace-scoped tickets for open ticket count per workspace — N/A: deferred to T008 (portfolio mode); update_system_state.py remains harness-scoped for now
- [x] Session-close does not commit anything from `workspaces/*/internal/` to the harness repo

## Notes
Depends on T001, T003. The per-repo commit sequence is new behaviour — harness iterates
over workspace repos, checks `git status`, and commits each dirty repo before the final
harness docs commit.

Commit message format for workspace repo commits: existing `commit_msg_check.py` rules apply.

Related: T003 (session-start), T005 (isolation), T007 (client progress.md generated here).

## Resolution
S002 2026-05-25: Updated `.claude/skills/session-close/SKILL.md` with workspace path
substitution table, workspace-scoped sessions.md/opus_notes.md targets, Opus isolation
rule (must not read outside declared repos), per-repo commit sequence (Step 6a), and
explicit rule that workspaces/*/internal/ is never included in harness docs commit.
update_system_state.py workspace scoping deferred to T008.
