---
id: SR-008
from: scrabble-score
raised: S11 2026-05-29
title: "create_ticket.py: ticket numbering is harness-global, not workspace-local"
severity: medium
status: resolved
harness_ticket: T135
resolved_in: S25
---

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

## Harness disposition

(Filled by harness on promotion or rejection.)
