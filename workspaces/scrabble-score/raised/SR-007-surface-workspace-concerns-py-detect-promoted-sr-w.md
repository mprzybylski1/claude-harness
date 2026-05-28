---
id: SR-007
from: scrabble-score
raised: S10 2026-05-28
title: "surface_workspace_concerns.py: detect promoted-SR with all linked tickets closed"
severity: low
status: raised
harness_ticket:
resolved_in:
---

## Context

`surface_workspace_concerns.py` surfaces SR items grouped by status
(`Active: raised`, `Active: promoted`, `Resolved since last session`).
"Active: promoted" means the harness opened a real ticket and is working
on it — the workspace will see "Resolved since last session" once the
last linked ticket closes (via `close_ticket.py` close-the-loop
integration writing `status: resolved` back to the SR file).

**Detection gap:** if the close-the-loop integration *never fires* for a
promoted SR (e.g., the linked tickets don't carry `source: <slug>/SR-NNN`
frontmatter so `close_ticket.py` doesn't know to write back), the SR
sits in `Active: promoted` forever. The tool has no cross-reference
mechanism that asks "is this SR still active, given that all its named
tickets are closed?"

S9 hit this with SR-001 (the bootstrap concern that built the SR system
itself). All 9 implementation tickets (T104–T112) closed in S20–S21, but
SR-001's `status:` field stayed `promoted` because the bootstrap tickets
predated the `promote_raised_concern.py` script that would have stamped
their frontmatter. The workspace operator spotted the mismatch manually
at session-start; the tool surfaced no signal.

Low severity because SR-001 is the only known case — every future SR
*should* go through `promote_raised_concern.py` and get the source stamp
properly. But the gap is real for any future SR that gets promoted
manually (e.g., bootstrap migrations, batch-promoted families) or for
any SR whose source stamp got lost in a refactor.

## Proposed change

Two layers:

1. **One-off:** harness operator should manually resolve SR-001 in the
   next harness-root session (write `status: resolved` + `resolved_in: S<N>`
   to the SR file; commit). Not in scope here — that's a harness data
   fix, not tooling.

2. **Tooling:** when `surface_workspace_concerns.py` reads each
   `Active: promoted` SR, parse the `harness_ticket:` frontmatter field
   (which may be a single ID or a range like `T104–T112`), check each
   linked ticket's archive status (file exists in `docs/archive/T###*.md`
   AND has `status: closed`). If **all** linked tickets are closed but
   the SR is still `promoted`, surface as `Stuck (promoted, all linked
   tickets closed)` under a new section heading. Highlights mismatches
   for human review without auto-modifying SR files.

   Adds ~15 lines to the script. No false-positive cost — the heuristic
   is conservative.

## Harness disposition

(Filled by harness on promotion or rejection.)
