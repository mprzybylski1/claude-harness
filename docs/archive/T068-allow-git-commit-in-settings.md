---
id: T068
title: Pre-allow Bash(git commit *) in settings.json
severity: medium
status: closed
phase: process
layer: process
opened: S13 2026-05-26
closed: S14 2026-05-26
---

## Problem

`Bash(git commit *)` is not in the `permissions.allow` list in `.claude/settings.json`.
When subagents or Claude itself tries to commit, the user gets a permission prompt.
In S13, all agent commits had to be done manually because agents were denied `git commit`
by the sandbox. This added friction and slowed down multi-ticket sessions.

`git commit` is a safe, reversible operation (commits can be undone with `git reset`).
Pre-allowing it removes a friction point without opening a meaningful attack surface.

The existing allow list already includes `Bash(git add *)` which is arguably more
dangerous (adds files not reviewed). Adding `git commit` is consistent with this posture.

## Acceptance Criteria

- [x] `"Bash(git commit *)"` is added to the `permissions.allow` list in
  `.claude/settings.json`.
- [x] `tests/test_config.py` passes with no changes (the new entry should not introduce
  hardcoded paths).
- [x] Verified that a `git commit` executed by an agent no longer triggers a permission
  prompt.

## Notes

Found during S13 workflow review. Low risk: commits are reversible, and commit discipline
(one per ticket) is already documented in CLAUDE.md. This is consistent with the existing
`Bash(git add *)` allow entry.

Related: T067 (worktree isolation strategy affects whether agents commit or not).

## Resolution

Added "Bash(git commit *)" to permissions.allow in .claude/settings.json, adjacent to the existing git add entry. test_config.py passes unchanged. S14.

Closed S14 2026-05-26.
