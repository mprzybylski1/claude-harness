---
id: SR-001
from: sub-tracker
raised: S1 2026-06-01
title: close_ticket.py / generate_ticket_index.py stamp S<N+1> instead of S<N> for workspace sessions
severity: medium
status: raised
harness_ticket:
resolved_in:
---

## Context

Surfaced in sub-tracker S1 (first workspace session). `close_ticket.py` stamped the closed ticket with `closed: S2 2026-06-01` and `generate_ticket_index.py` wrote "Generated S2 2026-06-01" — but the session was S1. The S1 log line was already appended to `sessions.md` before `close_ticket.py` ran, so `current_session.py` read it as "last logged = S1, therefore current = S2". Not blocking, but corrupts audit trail: T001 looks like it spanned two sessions when it opened and closed in S1. Will recur on every workspace close. Fixed manually this session (archive + INDEX corrected in-place since internal/ is not git-tracked).

## Proposed change

`close_ticket.py` (and `generate_ticket_index.py --session`) should accept an explicit `--session S<N>` flag that overrides the `current_session.py` lookup, so the caller can pass the session ID determined at session-start (before the log line is appended) rather than re-deriving it at close time. Alternatively, `current_session.py` could have a `--before-append` mode that returns the session currently being closed rather than the next one.

## Harness disposition

(Filled by harness on promotion or rejection.)
