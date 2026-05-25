---
id: T004
title: Session-close workspace integration
severity: high
status: open
phase: 2
layer: process
opened: S002 2026-05-25
closed:
---

## Problem
`/session-close` commits to and logs state in the harness repo directly. In the workspace
model, session logs belong in the workspace's `internal/`, commits go to workspace repos
(not the harness repo), and Opus review targets the workspace's declared repos.

## Acceptance Criteria
- [ ] Session log written to `workspaces/<slug>/internal/sessions.md`, not global `docs/sessions.md`
- [ ] Opus review runs against the workspace's declared repos (primary: deep review; secondary: light review if dirty)
- [ ] Opus findings written to `workspaces/<slug>/internal/opus_notes.md`
- [ ] Per-repo commit sequence: harness detects which workspace repos have staged/unstaged changes and commits them in order before session-close commit
- [ ] Harness docs commit (`docs/` only) still goes to harness repo as before
- [ ] `update_system_state.py` reads workspace-scoped tickets for open ticket count per workspace
- [ ] Session-close does not commit anything from `workspaces/*/internal/` to the harness repo

## Notes
Depends on T001, T003. The per-repo commit sequence is new behaviour — harness iterates
over workspace repos, checks `git status`, and commits each dirty repo before the final
harness docs commit.

Commit message format for workspace repo commits: existing `commit_msg_check.py` rules apply.

Related: T003 (session-start), T005 (isolation), T007 (client progress.md generated here).
