---
id: T155
title: prepare_opus_context.py --base flag for fresh workspace repos
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S29 2026-06-01
closed: S30 2026-06-14
---

## Problem

Workspace repos that have never received a session-close commit produce a 0-line diff because the anchor git log --grep finds nothing and the main...HEAD fallback is also empty on a single-branch repo. Operator had to hand-write a diff-injection script for /implementation-review.

## Acceptance Criteria

- [x] --base SHA flag explicitly sets the diff base
- [x] Without --base and with no session-close anchor, fall back to the initial
      commit (empty-tree diff) so a fresh repo still produces a non-empty diff
- [x] Warning message updated to point at the new --base flag

### Scope note (S30)

The original AC2 — "fall back to first commit after the timestamp of the last
sessions.md log line" — was dropped. During session-close, Step 1 appends the
*current* session's log line before Step 5 runs this script, so the last log line
is today's date; using it as the diff base selects HEAD and yields an empty diff,
defeating the purpose. The sessions.md-timestamp heuristic is also brittle
(date-only granularity, same-day sessions). Replaced by the deterministic
`--base` flag plus the initial-commit fallback, which fully covers the real pain
(SR-001: a workspace's *first* session, where "diff the whole history" is correct).

## Resolution
Closed together with T157 — same implementation. --base flag + initial-commit fallback added to prepare_opus_context.py. The original sessions.md-timestamp fallback (AC2) was dropped: session-close Step 1 writes the current session's log line before Step 5 runs this script, so the last log date is today and would select HEAD (empty diff). See the Scope note in this ticket. Tests in tests/test_prepare_opus_context_base.py.

Closed S30 2026-06-14.
