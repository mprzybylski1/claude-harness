---
id: T024
title: document workspace-awareness matrix for harness scripts
severity: low
status: open
phase: 1
layer: infra
opened: S4 2026-05-25
closed:
---

## Problem

After T020-T023 land, the workspace-awareness state of every script in
`scripts/tools/` should be documented. Today a reader of
`.claude/skills/session-start/SKILL.md` or `session-close/SKILL.md` has no way to know
which scripts honor the documented workspace flags and which silently fall back to
harness-root defaults — leading to the kind of confusion seen in scrabble-score S1.

## Acceptance Criteria

- [ ] Add a section to `scripts/tools/README.md` (create if absent) listing every script in `scripts/tools/`, with columns: `script | workspace-aware? | flags supported`.
- [ ] Alternative or supplement: add a `# workspace: aware | blind` comment at the top of each script for inline discoverability.
- [ ] The matrix is current as of the time T024 closes (treat it as a snapshot, not a perpetual contract — future scripts must be added when introduced).

## Notes

Should land after T020-T023 so the matrix reflects the post-fix state, not the
broken-on-arrival state.

## Resolution

(Fill in on close.)
