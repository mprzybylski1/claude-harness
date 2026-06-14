---
id: T165
title: Ghost session: tickets stamped with an unlogged session number cause S<N> collisions
severity: medium
status: closed
phase: 2
layer: process
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-14
closed: S30 2026-06-15
---

## Problem

T157-T160 are stamped 'opened: S30 2026-06-02' but docs/sessions.md has no S30 Session Log entry (the log ends at S29 2026-06-01). current_session.py derives the active session from the last log line, so today's session (2026-06-14) ALSO resolves to S30 — a collision: two distinct work sessions share one S<N>. Root cause: a session opened tickets (stamping S30 via create_ticket) but never wrote a Session Log entry (no /session-close, or abandoned), so the number was never 'claimed' and the next session reuses it. This makes opened:/closed: audit references ambiguous within the harness layer — the same class of ambiguity Invariant 1 guards against across layers.

## Acceptance Criteria

- [x] Decide the claiming model → **keep log-derived** (S<N> is claimed when the
      Session Log line is written at `/session-close`). The reserve-at-session-start /
      auto-advance alternative was considered and rejected this session as too high-risk:
      it rewrites the core numbering algorithm every tool depends on, and a corrupted
      `.git/CLAUDE_SESSION_ID` could jump numbers. Add a detection guard instead.
- [x] Prevent recurrence → new advisory `check_session_continuity.py`, wired into
      `/session-start` (step 10), warns when the about-to-be-used S<N> is already stamped
      on open/archived tickets from a prior session. Prevents *silent* recurrence; the
      operator reconciles. (The "warn in create_ticket" alternative was unworkable — the
      current session never has its own log line at ticket-creation time, so it would be
      always-true noise.)
- [x] Decide re-stamp vs document → **document, do not re-stamp.** T157–T160 are closed
      and archived; rewriting their `opened:` stamps would itself mutate the audit trail.
      The conflation is recorded (see Resolution): the ghost session (2026-06-02, opened
      T157–T160) and this session S30 (2026-06-14/15) are distinct work-sessions that
      shared S30 under the old rule. Going forward the guard surfaces this at start.
- [x] Test covers the unlogged-session collision scenario (tests/test_check_session_continuity.py)

## Resolution
Added scripts/tools/check_session_continuity.py — an advisory session-start guard that derives the about-to-be-used S<N> (reusing current_session) and scans open+archived tickets for existing opened: S<N> stamps; any hit means a prior unlogged session already used N (the collision). Wired into /session-start as step 10 (with workspace-path variant) and a 'Session-number collision' briefing section. Kept the log-derived numbering model unchanged (rejected the riskier reserve/auto-advance redesign of core machinery). Dropped an initial date-based filter after a smoke test showed it false-flags a session's own tickets across midnight — an exact session-number match is correct because the intended caller runs before this session stamps any S<N>. Historical conflation documented, not re-stamped: the ghost session (2026-06-02, T157-T160) and this S30 (2026-06-14/15) shared a number under the old rule; archived stamps left intact. 5 tests added; full suite 594 green.

Closed S30 2026-06-15.
