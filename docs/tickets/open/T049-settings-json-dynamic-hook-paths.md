---
id: T049
title: Replace hardcoded absolute paths in settings.json hook commands
severity: low
status: open
phase: 2
layer: infra
opened: S9 2026-05-26
closed:
---

## Problem

T039 fixed hook commands by switching to absolute paths, but hardcoded them to
`/home/marcin/PycharmProjects/claude-harness/`. If the repo is cloned elsewhere (or
this config is shared), all hooks silently stop working — same failure mode as the
original relative-path bug, just with a different root cause.

Surfaced by workflow-review S9.

## Acceptance Criteria

- [ ] Hook commands in `.claude/settings.json` resolve the harness root dynamically
      rather than using a hardcoded path. Options:
      (a) `bash -c 'cd "$(git -C "$(dirname "$0")" rev-parse --show-toplevel)" && python3 scripts/hooks/...'`
      (b) Each hook script self-resolves via `Path(__file__).resolve().parents[N]`
          (already the case inside scripts) — only the invocation path needs to be absolute.
          Use `$BASH_SOURCE[0]` or a wrapper that locates the script relative to a fixed
          anchor (e.g., settings.json's own directory via a pre-resolution step).
      (c) Document that settings.json must be updated after any repo move (lowest effort;
          acceptable for a single-user harness).
- [ ] Chosen option verified to work from a workspace cwd (the T039 scenario).
- [ ] Test or manual verification documented in Resolution.

## Notes

Option (c) is acceptable for a personal harness and may be the right call given
complexity. The ticket exists to make the decision explicit rather than leaving the
hardcoded path undocumented.

## Resolution
(Fill in on close.)
