---
id: T048
title: Session brief carry-forward threshold mismatches Opus escalation cadence
severity: low
status: open
phase: 2
layer: tooling
opened: S9 2026-05-26
closed:
---

## Problem

`extract_session_brief.py` labels carry-forwards as "long-lived" only at >= 5 sessions.
Opus escalates carry-forwards starting at 2–3 sessions ("same complaint two sessions
running", "three sessions without a fix"). This session, the brief reported "None
(long-lived carry-forwards < 5 sessions)" while the Opus output listed 3 active
carry-forward items — a contradiction visible to anyone reading both outputs side-by-side.

The mismatch means the brief under-reports carry-forward urgency and users have to read
the raw Opus output to understand what's actually at risk.

Surfaced by workflow-review S9.

## Acceptance Criteria

- [ ] `extract_session_brief.py --with-carry-forwards` (or the session-start skill step)
      reports carry-forwards at a threshold consistent with Opus escalation:
      either lower threshold to 2+ sessions, or label by count ("2-session carry-forwards",
      "3-session carry-forwards") instead of a single binary "long-lived" cutoff.
- [ ] The session-start briefing no longer produces a "None" carry-forward result when
      Opus simultaneously lists active carry-forwards.
- [ ] Test: synthetic Opus output with 2-session carry-forwards → brief shows them.

## Resolution
(Fill in on close.)
