---
id: T009
title: Hooks workspace scoping — session log and ticket hooks
severity: medium
status: closed
phase: 2
layer: infra
opened: S002 2026-05-25
closed: S002 2026-05-25
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
- [x] `check_session_log.py` detects active workspace (via `workspace_config.active_workspace_dir()`)
  and reads `workspaces/<slug>/internal/sessions.md` instead of `docs/sessions.md`
- [x] `check_ticket_acs.py` validates tickets in the workspace `internal/tickets/open/` path
  when a workspace ticket is being moved
- [x] `regenerate_ticket_index.py` detects whether the written ticket is under
  `workspaces/<slug>/internal/tickets/` and regenerates the workspace INDEX at that path
- [x] All three hooks fall back to harness-root paths when no workspace is active (no regression)
- [x] Tests: existing hook behaviour unchanged for non-workspace sessions

## Notes
Surfaced as a gap during T005 implementation — AC deferred to this ticket.
`workspace_config.active_workspace_dir()` is the detection mechanism (checks CWD against
`workspaces/` base).

Related: T005 (isolation enforcement), T003 (session-start), T004 (session-close).

## Resolution

S002 2026-05-25: Added workspace detection to all three hooks using `active_workspace_dir()`. Each hook
uses harness-root paths when the function returns `None` and workspace-scoped paths when it returns a
workspace directory. `generate_ticket_index.py` gained `--tickets-dir`, `--output`, and `--sessions-file`
CLI args so `regenerate_ticket_index.py` can pass workspace paths to it as a subprocess. Detection in
`regenerate_ticket_index.py` is based on the written file's path (via `workspaces_base()`), not CWD,
since PostToolUse receives the file path directly. Tests in `tests/test_hooks_workspace_scoping.py`
cover all six detection scenarios with `patch.object` to mock workspace context.
