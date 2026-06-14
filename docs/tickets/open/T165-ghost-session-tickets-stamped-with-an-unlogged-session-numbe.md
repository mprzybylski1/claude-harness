---
id: T165
title: Ghost session: tickets stamped with an unlogged session number cause S<N> collisions
severity: medium
status: open
phase: 2
layer: process
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-14
closed:
---

## Problem

T157-T160 are stamped 'opened: S30 2026-06-02' but docs/sessions.md has no S30 Session Log entry (the log ends at S29 2026-06-01). current_session.py derives the active session from the last log line, so today's session (2026-06-14) ALSO resolves to S30 — a collision: two distinct work sessions share one S<N>. Root cause: a session opened tickets (stamping S30 via create_ticket) but never wrote a Session Log entry (no /session-close, or abandoned), so the number was never 'claimed' and the next session reuses it. This makes opened:/closed: audit references ambiguous within the harness layer — the same class of ambiguity Invariant 1 guards against across layers.

## Acceptance Criteria

- [ ] Decide the claiming model: is S<N> reserved at first use (e.g. first ticket/commit) or only when the Session Log entry is written?
- [ ] Prevent recurrence: either reserve the number at session-start, or have create_ticket warn when it stamps a session with no corresponding log entry
- [ ] Decide whether to re-stamp or document the existing T157-T160 (now archived) S30 stamps vs today's S30
- [ ] Test covers the unlogged-session collision scenario

## Resolution
(Fill in on close.)
