---
id: T042
title: Add test for _is_closed_ticket path-component check
severity: low
status: open
phase: 2
layer: test
opened: S9 2026-05-26
closed:
---

## Problem

T034 (S8) tightened `_is_closed_ticket` in `regenerate_ticket_index.py` from a loose
substring match (`"/tickets/closed/" in file_path`) to a proper path-component walk
(`Path.parts`). This correctly rejects false positives like
`/foo/tickets-closed-archive/bar.md`. But there is no test exercising the new logic —
neither the happy path nor the false-positive rejection.

Flagged as S8 Finding #8.

## Acceptance Criteria

- [ ] Two parametrized test cases for `_is_closed_ticket` in
      `tests/test_workspace_path_flags.py` (or equivalent):
      1. Happy path: `docs/tickets/closed/T001.md` → `True`
      2. False-positive rejection: `/some/tickets-closed-archive/T001.md` → `False`
- [ ] Also cover workspace path: `workspaces/ws/internal/tickets/closed/T001.md` → `True`
- [ ] Tests import `_is_closed_ticket` directly from
      `scripts/hooks/regenerate_ticket_index`.
- [ ] All tests pass.

## Resolution
(Fill in on close.)
