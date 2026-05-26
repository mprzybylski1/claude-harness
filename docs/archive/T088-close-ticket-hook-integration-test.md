---
id: T088
title: Add close_ticket + commit-hook end-to-end integration test
severity: low
status: closed
phase: 2
layer: tooling
opened: S18 2026-05-26
closed: S18 2026-05-26
---

## Problem

There is no test that drives the full seam: `close_ticket.py --files foo.py` followed
by running the fix-commit through `check_fix_commit_has_code.py`. Changes to either
tool can regress the other silently.

(Opus S17 Concern #4 / Test Gap)

## Acceptance Criteria

- [x] One integration test drives `close_ticket.py T999 --resolution X --files foo.py`
      in a real git repo, then passes the suggested commit command through the hook.
- [x] The hook allows the commit (exit 0) — proving code is staged correctly.
- [x] A second test drives `close_ticket.py T999 --resolution X` (no --files) in a
      repo that has no other staged code, then passes the suggested commit through
      the hook and asserts it is blocked (exit non-zero).

## Resolution
Added tests/test_close_ticket_hook_integration.py with 2 integration tests: (1) close_ticket --files stages code, hook allows the fix commit; (2) close_ticket without --files leaves no code staged, hook blocks the commit.

Closed S18 2026-05-26.
