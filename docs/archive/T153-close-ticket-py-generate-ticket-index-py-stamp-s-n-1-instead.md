---
id: T153
title: close_ticket.py / generate_ticket_index.py stamp S<N+1> instead of S<N> for workspace sessions
severity: medium
status: closed
phase: 2
layer: tooling
opened: S29 2026-06-01
closed: S29 2026-06-01
source: sub-tracker/SR-001
---

## Problem

Promoted from sub-tracker/SR-001.

## Context

Surfaced in sub-tracker S1 (first workspace session). `close_ticket.py` stamped the closed ticket with `closed: S2 2026-06-01` and `generate_ticket_index.py` wrote "Generated S2 2026-06-01" — but the session was S1. The S1 log line was already appended to `sessions.md` before `close_ticket.py` ran, so `current_session.py` read it as "last logged = S1, therefore current = S2". Not blocking, but corrupts audit trail: T001 looks like it spanned two sessions when it opened and closed in S1. Will recur on every workspace close. Fixed manually this session (archive + INDEX corrected in-place since internal/ is not git-tracked).

## Proposed change

`close_ticket.py` (and `generate_ticket_index.py --session`) should accept an explicit `--session S<N>` flag that overrides the `current_session.py` lookup, so the caller can pass the session ID determined at session-start (before the log line is appended) rather than re-deriving it at close time. Alternatively, `current_session.py` could have a `--before-append` mode that returns the session currently being closed rather than the next one.
## Root Cause

Session-close writes the `S<N>` Session Log line to `sessions.md` (Step 1) before
closing tickets (Step 2). When `close_ticket.py` runs, `current_session.py` reads
that just-written entry and returns `S<N+1>`. Both symptoms originate here:

1. `close_ticket.py:_current_session()` (line ~798) stamps `closed: S<N+1>` in frontmatter.
2. `close_ticket.py:_regenerate_index()` (line ~385) calls `generate_ticket_index.py`
   with `--sessions` (file path) but no `--session` (number override), so the index
   script re-derives `int(matches[-1]) + 1` and writes `Generated S<N+1>`.

The fix is single-site: once `close_ticket.py` has the correct session number, both
the frontmatter stamp and the INDEX regen (via `--session` passthrough) resolve.

## Acceptance Criteria

- [x] When `sessions.md` already contains an `S<N>` log entry, `close_ticket.py` stamps `closed: S<N>` (not `S<N+1>`) in the archived ticket's frontmatter
- [x] When `sessions.md` already contains an `S<N>` log entry, the regenerated INDEX.md reads `Generated S<N>` (not `S<N+1>`)
- [x] Regression test: closing a ticket after the session log line is appended produces the correct session stamp
- [x] Existing behavior when no log line exists yet (mid-session close before session-close) is unchanged

## Resolution

Added --session flag to close_ticket.py. When provided, it overrides the current_session.py lookup — preventing the off-by-one when the session log line is already written. The flag normalizes input (accepts S8 or 8, rejects garbage), passes the session number through to _regenerate_index (which forwards it as --session to generate_ticket_index.py), and the session-close SKILL now documents passing --session S<N> in Step 2. Remaining vector: the PostToolUse regenerate_ticket_index hook still self-derives the session from sessions.md — not currently triggerable during the close flow (close_ticket.py uses open(), not Edit/Write), but noted for future hardening.

Closed S29 2026-06-01.
