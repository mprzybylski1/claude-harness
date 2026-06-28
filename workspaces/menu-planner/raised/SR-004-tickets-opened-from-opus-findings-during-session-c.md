---
id: SR-004
from: menu-planner
raised: S15 2026-06-28
title: "Tickets opened from Opus findings during /session-close are stamped opened: S<N+1>, colliding with the next session"
severity: low
status: raised
harness_ticket:
resolved_in:
---

## Context

Surfaced in menu-planner two sessions running. During `/session-close` Step 5, the
post-session Opus review produces follow-up tickets, which I create with
`create_ticket.py`. By that point Step 1 has already appended the closing session's
Session Log line, so `create_ticket` derives the session as last-logged + 1 and stamps
the new tickets `opened: S<N+1>`. The *next* session is also S<N+1>, so
`check_session_continuity.py` flags a collision at the next session-start, and I have to
relabel the tickets by hand:

- S13 close opened T097/T098 → mis-stamped `opened: S14` → relabeled to S13 at S14 start.
- S14 close opened T101/T102 → mis-stamped `opened: S15` → relabeled to S14 at S15 start.

Not blocking (the continuity check catches it and the manual `sed` relabel is quick), but
it recurs every code-session close that opens review tickets, and a missed relabel would
silently corrupt `opened:` attribution. Same off-by-one class as the `--session` flag that
`close_ticket.py` already takes (T139).

## Proposed change

Give `create_ticket.py` a `--session S<N>` flag (mirroring `close_ticket.py`) and have
`/session-close` Step 5 pass the current session when opening Opus-finding tickets, so they
are stamped with the closing session rather than last-logged + 1. Alternatively,
`create_ticket.py` could detect that the latest Session Log line belongs to the in-progress
close and not add 1 — but an explicit `--session` flag is the least surprising and matches
the existing `close_ticket.py` precedent. Harness may prefer to fold this into the
session-close skill docs (always pass `--session`) the way the abandoned-session path
already mandates for `raise_for_harness.py`.

## Harness disposition

(Filled by harness on promotion or rejection.)
