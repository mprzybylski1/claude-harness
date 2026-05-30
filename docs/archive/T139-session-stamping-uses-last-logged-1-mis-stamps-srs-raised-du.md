---
id: T139
title: Session stamping uses last-logged+1, mis-stamps SRs raised during session close
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S25 2026-05-30
closed: S25 2026-05-30
---

## Problem

Secondary item split from SR-011 / T138. `current_session.py` derives the session
as last-logged `S<N>` + 1. That is correct mid-session (the running session's Session
Log line is not written until close) but over-counts by one once the close protocol
appends that line (session-close Step 1, SKILL.md ~line 121). SR-011 was raised during
the S13 close, after the `S13` log line existed, so `raise_for_harness.py` stamped it
`raised: S14`.

No file-derived heuristic can fix this: both available in-file signals (last-logged,
and the Active Work `**S<N>**` header) collapse to "last closed session" in *both*
phases, and the close flows disagree on append-vs-raise order (normal close appends
then raises → needs +0; abandoned flow raises then appends → needs +1). The running
session must come from outside the file.

## Acceptance Criteria

- [x] raise_for_harness.py (and any session-stamping helper) stamps the *running* session, not last-logged+1 — added `--session S<N>`, used verbatim when supplied. Scope: `raise_for_harness` is the only *tracked-field* stamper exposed to this (it writes `raised:` frontmatter). `surface_workspace_concerns` warn-and-omits (commit-message only, lower stakes) — left unchanged. `create_ticket.py` runs mid-session (pre-append), so last+1 is correct there in practice; not modified.
- [x] Correctly stamps an SR raised during session close, after the session-log line has been appended (the S13→S14 off-by-one observed in SR-011) — `--session` bypasses the last+1 lookup entirely; `session-close/SKILL.md` now passes `--session S[CURRENT_SESSION]` (the value captured at Step 0, *before* the log line is appended), correct for both close flows.
- [x] Test covers the raise-during-close ordering case — `tests/test_raise_for_harness.py::TestExplicitSession::test_explicit_session_used_verbatim` (sessions.md last line already `S13` → `--session S13` stamps S13, not S14).

## Resolution
Added an optional `--session S<N>` flag to `raise_for_harness.py`. When supplied,
the value is validated (`^S\d+$`, else exit 2) and used verbatim, skipping the
`resolve_workspace_sessions_md` / `_current_session` last-logged+1 lookup. When
absent, behaviour is unchanged — including the Invariant-3 fail-closed (exit 2) on a
missing workspace `sessions.md`.

`session-close/SKILL.md` now passes `--session S[CURRENT_SESSION]` at the
raise-during-close invocation. `CURRENT_SESSION` is captured at close Step 0, BEFORE
Step 1 appends the running session's Session Log line, so the value is the true
running session regardless of close-flow append/raise ordering.

Why not a file-derived heuristic or a session-start pin: both in-file signals collapse
to "last closed session" in both lifecycle phases, and the two close flows disagree on
ordering, so no fixed +0/+1 rule works. A session-start pin only relocates the
staleness failure (a stale pin == last-logged is ambiguous with the during-close case).
An explicit caller-supplied value is the only source that is correct in all cases — and
it is NOT an Invariant-3 violation: it is a declared input, not a silent default.

Scope: `raise_for_harness` is the only tracked-field session stamper exposed to this
ordering bug. `surface_workspace_concerns` warn-and-omits (commit-message only);
`create_ticket.py` runs mid-session (pre-append) so last+1 is correct there. Neither
changed. Invariant greps still hold: `sessions_md is None` present (Inv 1 #2),
`sys.exit(2)` present 3× incl. the new validation (Inv 3).

Files: scripts/tools/raise_for_harness.py, .claude/skills/session-close/SKILL.md,
tests/test_raise_for_harness.py (+4 tests). 22 raise tests + 76 raise/concern-suite
tests pass.

Closed S25 2026-05-30.
