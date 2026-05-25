---
id: T009
title: Hooks workspace scoping — session log and ticket hooks
severity: medium
status: open
phase: 2
layer: infra
opened: S002 2026-05-25
closed:
---

## Problem
Four hooks still operate on harness-root paths and have no concept of workspaces:

- `check_session_log.py` (Stop) — validates `docs/sessions.md`; should validate
  `workspaces/<slug>/internal/sessions.md` when a workspace session is active
- `check_ticket_acs.py` (PreToolUse) — validates tickets in `docs/tickets/open/`; should
  also cover `workspaces/<slug>/internal/tickets/open/`
- `regenerate_ticket_index.py` (PostToolUse) — regenerates `docs/tickets/INDEX.md`; should
  regenerate the workspace INDEX when a workspace ticket is written
- `check_skill_bash_blocks_hook.py` (PostToolUse) — already global (SKILL.md files), no
  change needed

Without this, the Stop hook cannot enforce closed-ticket attribution for workspace sessions,
and the PreToolUse AC check does not protect workspace tickets.

## Acceptance Criteria
- [ ] `check_session_log.py` detects active workspace (via `workspace_config.active_workspace_dir()`)
  and reads `workspaces/<slug>/internal/sessions.md` instead of `docs/sessions.md`
- [ ] `check_ticket_acs.py` validates tickets in the workspace `internal/tickets/open/` path
  when a workspace ticket is being moved
- [ ] `regenerate_ticket_index.py` detects whether the written ticket is under
  `workspaces/<slug>/internal/tickets/` and regenerates the workspace INDEX at that path
- [ ] All three hooks fall back to harness-root paths when no workspace is active (no regression)
- [ ] Tests: existing hook behaviour unchanged for non-workspace sessions

## Notes
Surfaced as a gap during T005 implementation — AC deferred to this ticket.
`workspace_config.active_workspace_dir()` is the detection mechanism (checks CWD against
`workspaces/` base).

Related: T005 (isolation enforcement), T003 (session-start), T004 (session-close).
