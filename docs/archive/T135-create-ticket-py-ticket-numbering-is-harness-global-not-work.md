---
id: T135
title: create_ticket.py: ticket numbering is harness-global, not workspace-local
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S24 2026-05-30
closed: S25 2026-05-30
source: scrabble-score/SR-008
---

## Problem

Promoted from scrabble-score/SR-008.

## Context

Surfaced in scrabble-score S11 while opening the dictionary-hardening ticket.

`create_ticket.py --workspace scrabble-score` produced **T135**, but the
scrabble-score workspace numbers its own tickets locally: T001–T018 closed,
T017 open. The expected next number was **T019**.

Root cause — `_next_id()` (`scripts/tools/create_ticket.py:42`) scans *every*
ticket location at once: harness `docs/tickets/{open,closed}`, `docs/archive`,
**and** every workspace's `internal/tickets/open` + `archive`, then returns the
global `max + 1`. Because the harness root already has tickets up to T134, the
workspace got T135. The `--workspace` flag only routes the *destination dir* and
frontmatter; it does not scope the counter.

This is the same workspace-blind class of defect already noted for session
numbering (three harness tools are workspace-blind; see harness memory
`feedback_session_numbering`). It also sits adjacent to Invariant 1
(workspace↔harness session-number separation) — the same separation principle
arguably applies to ticket IDs: a global counter means a workspace's ticket
sequence has unpredictable gaps driven by unrelated harness/other-workspace
activity, which breaks the "T-number = this workspace's Nth ticket" mental model
and makes cross-references ambiguous.

Not blocking — worked around this session by manually renaming the file
T135 → T019, fixing the `id:` frontmatter, and regenerating the workspace
INDEX.md. But it recurs on every ticket created in any workspace, and the manual
rename is exactly the kind of audit-trail-fragile step the harness tooling exists
to prevent.

## Proposed change

Scope `_next_id()` to the target location's own counter:

- When `--workspace SLUG` is given, scan **only** that workspace's
  `internal/tickets/{open}` + `archive` (and any `docs_path` override) for the
  max T-number, ignoring harness root and other workspaces.
- When no workspace is given (harness-root ticket), scan **only** the harness
  `docs/tickets/{open,closed}` + `docs/archive`.

This mirrors how `current_session.py --sessions PATH` already scopes the session
counter per layer. Consider whether `generate_ticket_index.py` and any other
T-number consumer share the same global-scan assumption and need the same fix.

Verification after change: `create_ticket.py --workspace scrabble-score <title>`
should yield T019 (next after T018), not a harness-global number.

### Sibling fix: `generate_ticket_index.py` is workspace-blind in the same way

Surfaced in the same session while regenerating the workspace INDEX after the
T135 → T019 rename. `generate_ticket_index.py` accepts `--tickets-dir`,
`--output`, and `--sessions-file` as three independent path flags but has **no
`--workspace SLUG` shortcut**. The workspace-internal regen therefore requires
three absolute paths constructed by hand:

```
python scripts/tools/generate_ticket_index.py \
  --tickets-dir <ws-internal>/tickets \
  --output     <ws-internal>/tickets/INDEX.md \
  --sessions-file <ws-internal>/sessions.md
```

Proposed: add `--workspace SLUG` to `generate_ticket_index.py` mirroring the
`create_ticket.py` fix above. When `--workspace` is given, the three paths
resolve from `workspace_internal_path.py` and the other three flags become
optional overrides. This is a one-flag UX change in the same script family;
ideally lands in the same harness ticket promoted from this SR so the
"workspace-blind tooling" sweep is coherent.

Note for harness disposition: a `regenerate_ticket_index.py` hook already
exists in `scripts/hooks/` — check whether it is also workspace-blind (it
likely is) and fix it in the same pass.
## Acceptance Criteria

- [x] When `--workspace SLUG` is given, scan **only** that workspace's tickets/{open,closed} + archive — `_next_id(internal)` scopes the scan to the workspace's own layer. Verified: `--workspace scrabble-score` → T027 (its own next), not a harness-global number.
- [x] When no workspace is given (harness-root ticket), scan **only** the harness docs/tickets/{open,closed} + docs/archive — `_next_id(None)` → T140.

## Coordination

Part of the workspace-blind tooling sweep (SR-007 family): **T135 (SR-008) →
T136 (SR-009) → T137 (SR-010)**, triaged S24 as "3 tickets, helper-first".

- **This ticket is the foundation.** Build the shared `workspace_context.py`
  helper here — a single resolver returning `(slug, internal_path, sessions_md)`
  or `None` from `.claude/.active_workspace` — so T136 and T137 consume it rather
  than each re-deriving workspace scope. All three SRs independently proposed this
  helper; centralise it in T135.
- **`generate_ticket_index.py` overlaps with T136.** SR-008's sibling fix (add
  `--workspace SLUG` to `generate_ticket_index.py`, and check the
  `regenerate_ticket_index.py` hook) touches the same script T136 makes
  fail-closed. Do the `generate_ticket_index.py` changes once, in whichever of
  T135/T136 lands first, and have the other reference it — do not let both
  tickets edit that script independently.

## Resolution
Scoped `create_ticket._next_id()` to the target layer. It now takes the resolved
`internal` dir (None for harness) and scans only that layer:
- harness: docs/tickets/{open,closed} + docs/archive
- workspace: <internal>/tickets/{open,closed} + <internal>/archive
The previous global scan (harness + every workspace, max+1) is gone, so a
workspace ticket continues its own sequence. Verified against live data:
`--workspace scrabble-score` → T027 (workspace max T026), harness → T140. The
scan also now includes the workspace's own tickets/closed/, which the original
workspace scan omitted (it only looked at open + archive).

Scope decisions (deferred deliberately, with trail — see T136):
- Shared workspace resolver NOT built here. T135 has no consumer: it gets the
  slug from explicit --workspace and reuses _resolve_internal, so building a
  `.active_workspace`-based resolver now would mean designing an interface with
  no caller to validate it. Deferred to T136 (its first real consumer), and the
  resolver should EXTEND workspace_config.py rather than spawn a parallel
  workspace_context.py module (a second overlapping module is its own divergence).
  Noted in T136.
- `generate_ticket_index.py --workspace SLUG` sibling fix NOT done here. It is
  prose in this SR, not a T135 AC, and T136 *is* generate_ticket_index — its
  natural home. Deferred to T136. (The coordination note's "check whether the
  regenerate_ticket_index.py hook is also workspace-blind" — it is NOT: the hook
  already routes by the written file's path via _detect_workspace_from_path.
  Recorded so T136 doesn't re-investigate.)

Cross-layer ID collision (now reachable for new tickets, e.g. a future workspace
starting at T001 vs harness legacy T001): close_ticket.py fails closed — _find_ticket
collects all matches across layers and exits demanding --workspace when >1 OPEN
ticket shares a bare ID. It does not silently grab the wrong layer. The --workspace
disambiguator is real and functional. Not a regression; the duplication already
exists historically (scrabble T001-T026 mirror harness T001-T026) — this fix only
makes numbering consistent with that per-layer reality.

Files: scripts/tools/create_ticket.py, tests/test_create_ticket.py (+3 tests:
both isolation directions + workspace closed-dir inclusion). 15 create_ticket
tests + 472 suite tests pass.

Closed S25 2026-05-30.
