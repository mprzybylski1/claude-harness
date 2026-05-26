---
id: T054
title: S10 — close_ticket.py remaining correctness issues (atomic move, resolution regex, stamp regex, silent parse failure)
severity: medium
status: closed
phase: 2
layer: infra
opened: S10 2026-05-26
closed: S11 2026-05-26
---

## Problem

Four correctness issues in `scripts/tools/close_ticket.py` surfaced or re-confirmed by S10 Opus review:

**1. Non-atomic move still possible (S10 Finding #1 / S9 #2)**
`dest.write_text(content); ticket_path.unlink()` fixes the original write-failure case but
not the unlink-failure case: if `ticket_path.unlink()` fails, the ticket exists in BOTH
`tickets/open/` (with already-modified frontmatter) AND `archive/`. Next run hits "already
exists in archive" and exits 2. Suggested fix: write to a same-directory tempfile in
`archive/`, then `os.replace(tempfile, dest)`, then `ticket_path.unlink()`.

**2. `_replace_resolution` too strict (S9 #1 — not addressed in S10)**
Exits 2 with "ticket format unexpected" when the placeholder doesn't match exactly. Users
get stuck mid-closure after AC validation already passed. Fix: add a permissive fallback
pass that replaces a bare `(Fill in on close` anywhere in the Resolution section, warning
on fallback.

**3. Session-stamp regex over-matches (S9 #2 — not addressed in S10)**
`re.search(r"\bS\d+\b.*\d{4}-\d{2}-\d{2}", resolution)` false-positives on any resolution
mentioning a historical session (e.g. "Reverted the S5 2026-01-01 commit") and suppresses
the `Closed S10 …` stamp. Fix: anchor to end-of-string or use a more specific pattern.

**4. Silent workspace.yaml parse failure (S10 Finding #5)**
`_docs_paths()` calls `load_workspace(ws_dir)` which returns `None` on parse failure.
Silently falls back to `internal/tickets/open/` — user gets "ticket not found" with no
indication that one workspace failed to load. Fix: warn to stderr when `load_workspace`
returns `None` but `workspace.yaml` exists.

## Acceptance Criteria

- [x] Move uses `os.replace(tmp, dest)` pattern so write and rename are atomic; `unlink` on
      open copy is outside the critical window.
- [x] `_replace_resolution` has a permissive fallback; warns on stderr when fallback fires.
- [x] Session-stamp regex does not match a historical session mention mid-resolution text.
- [x] `_docs_paths` warns to stderr when `workspace.yaml` exists but `load_workspace` returns None.
- [x] Tests cover: unlink-after-write failure leaves archive clean; permissive fallback; stamp
      not suppressed by historical mention; workspace-parse-failure warning.
- [x] All existing tests still pass.

## Notes

S10 session log incorrectly claimed S9 #1 and S9 #2 were fixed under T051 — only S9 #3
(atomic write reorder) was actually fixed. Issue 1 here is an improvement over the old
behavior but still not the recommended `os.replace` approach.

## Resolution
Implemented all four fixes in scripts/tools/close_ticket.py: (1) extracted _atomic_move helper using os.replace for atomic archive write — eliminates partial-write window; (2) added permissive fallback in _replace_resolution for non-standard placeholder placement, warns to stderr on fallback; (3) tightened stamp-suppression regex from broad S\d+.*date to specific 'Closed S\d+ date' pattern to avoid false-positive on historical session mentions in resolution text; (4) wrapped load_workspace call in _docs_paths with try/except — warns to stderr when workspace.yaml exists but fails to parse rather than crashing or silently skipping. Also fixed a pre-existing re.sub injection bug in _replace_resolution where backslashes in resolution text were misinterpreted as regex escapes (switched to lambda replacement). 7 new tests added to TestCloseTicketT054. All 113 existing close_ticket / telemetry / hooks tests pass.

Closed S11 2026-05-26.
