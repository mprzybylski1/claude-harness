---
id: T075
title: close_ticket.py clobbers harness INDEX.md from workspace context
severity: high
status: closed
phase: 2
layer: process
opened: S16 2026-05-26
closed: S16 2026-05-26
---

## Problem

`close_ticket.py T009 --workspace scrabble-score` rewrites `<harness>/docs/tickets/INDEX.md`
with workspace-scoped values (e.g. "Generated S4", workspace ticket ages). This is silent
corruption of a tracked harness file — it happens every workspace ticket close and requires
a manual `git restore docs/tickets/INDEX.md` before committing.

**Root cause:** `close_ticket.py` invokes `generate_ticket_index.py` post-close but does
not pass the workspace context, so the index generator defaults to harness-root paths.
Same workspace-blind class of bug as T072 (git staging to wrong repo).

**Fix:** Thread `--workspace` (or auto-detect from the ticket file's path) through to the
inner `generate_ticket_index.py` call so it writes to the workspace INDEX, not harness root.

## Acceptance Criteria

- [x] `close_ticket.py T<N> --workspace <slug>` writes the regenerated INDEX to
  `<workspace internal>/tickets/INDEX.md`, not `<harness>/docs/tickets/INDEX.md`.
- [x] Harness-root invocations (`close_ticket.py T<N>` without `--workspace`) continue
  to write to `<harness>/docs/tickets/INDEX.md`.
- [x] Test covering the workspace case: after closing a workspace ticket, harness INDEX
  is unchanged and workspace INDEX is updated.

## Notes

Related to T074 — both are workspace-path-handling gaps in the ticket-index pipeline.
See `docs/workflow_review_S4_findings.md` finding #2. High priority: this is silent
file corruption that happens on every workspace ticket close.

## Resolution

Fixed in close_ticket.py _regenerate_index(): when internal is not None (workspace context), now passes --tickets-dir and --output pointing to the workspace internal path, in addition to --sessions. The index generator no longer defaults to harness-root paths. One test added: closing a workspace ticket leaves harness INDEX.md unchanged and updates workspace INDEX.md.

Closed S16 2026-05-26.
