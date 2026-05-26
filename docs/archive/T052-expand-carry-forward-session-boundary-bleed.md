---
id: T052
title: expand_carry_forward.py — session boundary bleed (S9 #4)
severity: high
status: closed
phase: 2
layer: tooling
opened: S10 2026-05-26
closed: S10 2026-05-26
---

## Problem

`scripts/tools/expand_carry_forward.py:_extract_findings` — end-of-finding boundary only
considers `_ANY_FINDING_HEAD` positions, not session head positions. If the matched finding
is the LAST numbered finding in its session block, the extracted text bleeds into whatever
follows — potentially the next session's header, intro paragraph, and any prose until the
next finding head, which could be 50+ lines away in the next review.

The `[From: <file> — S<N>]` label is correct but the trailing content is wrong.

First flagged S9 #4.

## Acceptance Criteria

- [ ] `_extract_findings` includes `_SESSION_HEAD` positions in the end-boundary
      computation: `end = min(next_finding_head, next_session_head)`.
- [ ] Parametrised test: two consecutive sessions, each with one finding — expanding the
      first session's finding must not include text from the second session.
- [ ] All existing tests still pass.

## Notes

One-line fix + one test. Primary tool for carry-forward archaeology — boundary bleed
degrades output quality directly.

## Resolution

Fixed end-of-finding boundary in expand_carry_forward.py:_extract_findings. Combined head_positions (finding heads) and session head positions into a single sorted 'boundaries' list. end = next boundary after start, not just next finding head — so the last finding in a session block stops at the next session header instead of bleeding into it. Added regression test: two consecutive sessions, expanding S5#1 must not include S6 content.

Closed S10 2026-05-26.
