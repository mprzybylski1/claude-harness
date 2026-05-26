---
id: T045
title: close_ticket.py — single-command ticket closure
severity: medium
status: open
phase: 2
layer: tooling
opened: S9 2026-05-26
closed:
---

## Problem

Every ticket close runs the same 5-step procedure manually: edit frontmatter (`status`,
`closed:` date), append Resolution section, `mv` to archive, regenerate index, prepare
commit message. With 4 closures this session that was 20 mechanical Edit/Bash calls,
and the correct order has to be re-derived each time (especially after a session restart).

Surfaced by workflow-review S9.

## Acceptance Criteria

- [ ] `scripts/tools/close_ticket.py <T###>` script accepts a ticket ID.
- [ ] Locates the ticket file in `tickets/open/` (workspace-aware: checks `<INTERNAL>/tickets/open/` when a workspace is active).
- [ ] Updates frontmatter: `status: open` → `status: closed`, `closed:` → `S<N> YYYY-MM-DD`
      using `current_session.py` to derive S<N>.
- [ ] Appends or replaces the `## Resolution` section: reads existing placeholder
      `(Fill in on close.)` and prompts for replacement text (accepts `--resolution "..."` flag
      for non-interactive use; otherwise prints the current Resolution and asks the user to
      edit and confirm).
- [ ] Refuses closure if any `- [ ]` AC checkbox remains unchecked (exits with an error
      listing the unchecked items). Override with `--force`.
- [ ] Moves file from `tickets/open/` to `archive/` (workspace-aware).
- [ ] Calls `generate_ticket_index.py` (workspace-aware flags).
- [ ] Prints a suggested `git commit` one-liner.
- [ ] Test: round-trip a synthetic ticket through the script, assert each step.
- [ ] Existing manual close procedure in session-close/SKILL.md updated to reference this script.

## Notes

Resolution text can be long — favour `--resolution-file <path>` as an alternative to
`--resolution "..."` for multi-paragraph resolutions. The `(Fill in on close.)` placeholder
must be replaced, not merely appended to.

## Resolution
(Fill in on close.)
