---
id: T134
title: Extend check_session_log.py Stop hook to validate single S<N> header in Active Work
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S23 2026-05-28
closed: S23 2026-05-28
---

## Problem

T133 fixed the SKILL prose for session-close Active Work replacement but
relied on the model following the new instruction. Defense-in-depth: the
Stop hook should validate the section's integrity at session end and block
exit if drift is detected. The S22 regression (one S<N> header + orphan
"Tickets closed:" line from S21) was caught at S23 session-start by
`extract_session_brief.py`'s warning, but nothing acted on it — the warning
was just printed. Stop-hook enforcement closes that gap.

## Acceptance Criteria

- [x] scripts/hooks/check_session_log.py greps Active Work between '## Active Work' and '---'; fails non-zero if more or fewer than one '**S<N> — ...**' header found
- [x] Hook test added covering clean single-header passes, two-header fails, zero-header fails
- [x] Hook test added covering the regression case from S22→S23 (orphan prior-session block)

## Resolution
Added run_active_work_check + _extract_active_work_section to check_session_log.py, wired as Check 1b before the existing session-log check. Validates Active Work has exactly one **S<N> — ...** header AND at most one 'Tickets closed:' line. Broader than the literal AC ('S<N> header count'): also catches the actual S22 regression mode where the new header was written but prior-session 'Tickets closed:' content was left below it (one header, two ticket-closed lines). The dual check mirrors extract_session_brief.py's existing orphan-detection logic. 7 new TestActiveWorkIntegrity tests including the S22→S23 regression case. Smoke-tested against a synthetic S22 state: hook returns blocking error (headers=1, tickets_closed=2, would_block=True). All 38 hook tests + 455-test full suite pass.

Closed S23 2026-05-28.
