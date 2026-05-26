---
id: T054
title: S10 — close_ticket.py remaining correctness issues (atomic move, resolution regex, stamp regex, silent parse failure)
severity: medium
status: open
phase: 2
layer: infra
opened: S10 2026-05-26
closed:
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

- [ ] Move uses `os.replace(tmp, dest)` pattern so write and rename are atomic; `unlink` on
      open copy is outside the critical window.
- [ ] `_replace_resolution` has a permissive fallback; warns on stderr when fallback fires.
- [ ] Session-stamp regex does not match a historical session mention mid-resolution text.
- [ ] `_docs_paths` warns to stderr when `workspace.yaml` exists but `load_workspace` returns None.
- [ ] Tests cover: unlink-after-write failure leaves archive clean; permissive fallback; stamp
      not suppressed by historical mention; workspace-parse-failure warning.
- [ ] All existing tests still pass.

## Notes

S10 session log incorrectly claimed S9 #1 and S9 #2 were fixed under T051 — only S9 #3
(atomic write reorder) was actually fixed. Issue 1 here is an improvement over the old
behavior but still not the recommended `os.replace` approach.

## Resolution
(Fill in on close.)
