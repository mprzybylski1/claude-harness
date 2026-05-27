---
id: SR-001
from: scrabble-score
raised: S5 2026-05-27
title: Implement workspace↔harness separation tooling and guardrails
severity: high
status: promoted
harness_ticket: T104–T112
---

## Context

Today's harness has weak boundaries between root and workspaces. Tools accept
optional workspace flags and silently fall back to harness-root paths when a flag
is omitted — the failure mode that produced T103 (workspace data written into the
harness's own `docs/tickets/INDEX.md`). Beyond the specific bug, the harness has
been used as a dual-purpose system: scrabble work surfaces harness improvements,
which then get implemented inline from scrabble sessions. That was valuable for
bootstrapping the project-agnostic harness but is now the source of recurring
boundary leaks.

This concern requests the tooling and rules that establish strict separation
between layers, with one structured channel for workspace→harness handoff.

## Principle

Workspaces never write to harness state except into a single dedicated boundary
slot. Harness owns everything else, including status updates back into that slot.
Only harness-root sessions resolve harness concerns; workspace sessions can raise
them but cannot work on them.

No `--cross-layer` override flag exists in any tool. The friction of switching
session context is the enforcement; an override would create a second easier path
that erodes the first. If someone genuinely needs to bypass the rule they do it
with raw git outside the harness tooling — the harness itself never blesses a
violation.

## Boundary slot

Path: `workspaces/<slug>/raised/SR-NNN-<short-slug>.md`

- Lives in the harness repo, tracked in git (audit trail).
- Workspace creates the file with `status: raised`.
- Harness updates the same file twice over its lifetime: once on promotion, once
  on resolution. Workspace does not touch the file again after creation.
- The file is the single source of truth for the concern. No separate "status
  manifest" or join against archive — the `status:` field tells the whole story.

## File format

```yaml
---
id: SR-NNN
from: <workspace-slug>
raised: S<N> YYYY-MM-DD
title: <short description>
severity: low | medium | high | critical
status: raised | promoted | resolved | rejected
harness_ticket: T### | (empty until promoted)
resolved_in: S<N> | (empty until terminal)
---

## Context

(Why this matters, what workspace surfaced it, blocking yes/no.)

## Proposed change

(What the workspace thinks should happen. Harness may disagree.)

## Harness disposition

(Filled by harness on promotion or rejection. If rejected, the reason.
If promoted, links to the harness ticket and any caveats.)
```

## Status lifecycle

- `raised` — workspace just created the file.
- `promoted` — harness session has accepted the concern and opened a real harness
  ticket. `harness_ticket:` is filled.
- `resolved` — the promoted harness ticket has closed. `resolved_in:` is filled.
- `rejected` — harness reviewed and decided not to act. `resolved_in:` records
  the harness session that made the call. Body explains why.

`resolved` and `rejected` are terminal. There is no reopen path; if the concern
recurs, the workspace files a new SR-NNN.

## One-cycle visibility / auto-archive

Workspace session-start shows: all `raised` and `promoted` items (the active set)
plus any `resolved` / `rejected` items that landed since the last session-start.
After surfacing terminal items once, the session-start tool moves them to
`workspaces/<slug>/raised/archive/`. The operator sees the outcome exactly once;
the active view stays bounded.

## CLIs to build

All harness-root scripts:

1. **`scripts/tools/raise_for_harness.py`** — workspace-side wrapper that creates
   a properly-formatted SR-NNN file. Allocates the next sequence number by
   scanning `workspaces/<slug>/raised/` + `archive/`. Resolves `<slug>` from
   `workspace.yaml`. Refuses to run if no workspace context.

2. **`scripts/tools/list_raised_concerns.py`** — harness-side aggregator.
   Scans `workspaces/*/raised/*.md` across all workspaces, prints unresolved
   concerns grouped by workspace + severity. Invoked by session-start when no
   workspace is selected (harness-root session).

3. **`scripts/tools/promote_raised_concern.py <slug>/SR-NNN`** — harness-side.
   Reads the raised file, opens a new harness ticket via the existing ticket
   pipeline (`create_ticket.py`), copies title/severity/body into the new ticket,
   stamps the ticket frontmatter with `source: <slug>/SR-NNN`, and updates the
   raised file to `status: promoted, harness_ticket: T###`.

4. **`scripts/tools/reject_raised_concern.py <slug>/SR-NNN --reason "..."`** —
   harness-side. Updates the raised file to `status: rejected, resolved_in: S<N>`
   and appends the reason to the `## Harness disposition` section. Does not
   create a harness ticket.

5. **Close-the-loop integration in `close_ticket.py`** — when a harness ticket
   carries `source: <slug>/SR-NNN` frontmatter, closing it must also update the
   workspace's raised file to `status: resolved, resolved_in: S<N>`. Both writes
   happen in one transaction (stage together, commit together).

6. **Workspace-side surfacing in session-start** — read
   `workspaces/<my-slug>/raised/` directly. Surface active items in the briefing.
   Auto-archive terminal items after surfacing once.

## Guardrails

These belong in the existing PostToolUse / PreToolUse hook layer so the rule is
mechanical, not "remember the policy":

- `create_ticket.py` — refuse if active workspace context (cwd / WORKSPACE) does
  not match the target. Suggest `raise_for_harness.py` instead.
- `close_ticket.py` — refuse to close a harness ticket from inside a workspace
  context, and vice versa. The error message names the correct session type.
- A PostToolUse hook on writes to harness `docs/tickets/`, `docs/sessions.md`,
  `docs/opus_notes.md`, `docs/architecture_invariants.md`, etc. — block the
  write if the active session is a workspace session. The block is unconditional;
  no flag bypasses it.
- A symmetric PostToolUse hook on writes to `workspaces/*/internal/` from a
  harness-root session — also blocked. Harness writes to workspaces only via the
  boundary slot (status updates) and the close-the-loop integration above.

## Abandoned-session pattern

When a workspace session hits a mid-session harness blocker (cannot proceed,
cannot close cleanly):

1. Stage and commit in-progress work to a WIP branch:
   `git checkout -b wip/T### -m "WIP: blocked by SR-NNN"`.
2. Run `raise_for_harness.py` to create the SR-NNN.
3. Append a one-line note to the workspace session log marking the session
   abandoned, with the SR-NNN reference.
4. End the session. No regular session-close run — the workspace is in a
   "paused" state until the blocker resolves.
5. After harness resolves the SR-NNN, a new workspace session checks out the
   WIP branch and resumes.

This needs documentation in the workspace session-close skill and a
`session_status: abandoned` marker the workspace's sessions.md can record.

## Session-start integration

**Harness-root session-start** (no workspace selected) — add a section:

```
Pending raised concerns:
  scrabble-score:
    SR-001 (high) — Implement workspace↔harness separation tooling
    SR-002 (medium) — ...
  <other-workspace>:
    SR-003 (low) — ...
Triage: open with `python scripts/tools/promote_raised_concern.py <slug>/SR-NNN`
        or reject with `python scripts/tools/reject_raised_concern.py <slug>/SR-NNN --reason "..."`
```

**Workspace session-start** — add a section after Suggested Focus:

```
Your raised concerns:
  Active:
    SR-007 (promoted → T124) — Title; opened S5
    SR-009 (raised) — Title; opened S6
  Resolved since last session:
    SR-005 (resolved in T118 / S20) — Title
  Rejected since last session:
    SR-004 (rejected S19) — Title — reason: out of scope
```

The "since last session" set auto-archives after this surfacing.

## Acceptance criteria

- [ ] `raise_for_harness.py` exists and creates SR-NNN files in the boundary slot
- [ ] `list_raised_concerns.py` exists and is invoked by harness-root session-start
- [ ] `promote_raised_concern.py` exists, opens a harness ticket, and updates the
      raised file in one transaction
- [ ] `reject_raised_concern.py` exists and writes terminal `rejected` status
- [ ] `close_ticket.py` updates the source workspace's raised file on close when
      the harness ticket has a `source:` frontmatter field
- [ ] Workspace session-start surfaces own raised concerns, auto-archives
      terminal items after one-cycle visibility
- [ ] PostToolUse hook blocks workspace sessions from writing to harness state
      outside the boundary slot
- [ ] PostToolUse hook blocks harness sessions from writing to workspace
      internal state outside the close-the-loop path
- [ ] Abandoned-session pattern is documented in session-close SKILL.md with a
      `session_status: abandoned` convention
- [ ] No `--cross-layer` or equivalent override flag is added to any tool
- [ ] Regression tests cover: workspace→harness write refused; harness→workspace
      write refused; promote+close round-trip correctly mutates both files

## Harness disposition

Promoted S20 2026-05-27. Accepted in full. Broken into 9 implementation tickets:

- T104 — `raise_for_harness.py` (workspace-side SR creation)
- T105 — `list_raised_concerns.py` (harness aggregator)
- T106 — `promote_raised_concern.py` (accept SR → harness ticket)
- T107 — `reject_raised_concern.py` (reject SR, terminal status)
- T108 — `close_ticket.py` close-the-loop (resolve SR on ticket close)
- T109 — Harness-root session-start raised concerns section
- T110 — Workspace session-start surfacing + auto-archive
- T111 — PostToolUse cross-layer write guards (hooks)
- T112 — Abandoned-session pattern docs

T111 (hooks) is the riskiest; implement last after the round-trip scripts are
proven. SR-001 resolves when all 9 tickets are closed.

## Related

- T103 (closed S20 2026-05-27): defensive filter for TEMPLATE.md / T000 sentinel
  + `--output` flag in session-close. That fix patched one symptom of the weak
  boundary; this concern requests the systemic fix.
