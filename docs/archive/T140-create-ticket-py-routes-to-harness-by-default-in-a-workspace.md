---
id: T140
title: create_ticket.py routes to harness by default in a workspace session (no .active_workspace awareness)
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S25 2026-05-30
closed: S26 2026-05-31
---

## Problem

`create_ticket.py` writes ticket files via plain `open()`, so the PreToolUse
`check_cross_layer_writes` hook — which fires on Edit/Write only — cannot catch a
misrouted ticket. A bare invocation (no `--workspace`) always routed to the harness
layer, so running `create_ticket "X"` inside a declared workspace session silently
created a HARNESS ticket (wrong layer, wrong T-number from the harness counter), even
though the workspace↔harness separation rule says workspace sessions never create
harness tickets directly. (S25 spin-out; sibling of T136 which fixed the same
workspace-blindness in `generate_ticket_index.py`.)

## Acceptance Criteria

- [x] Bare create_ticket.py (no --workspace) in a declared-workspace session does not silently create a harness ticket
- [x] Mirror generate_ticket_index.py (T136): consult .claude/.active_workspace and fail closed (or route) for workspace/undeclared sessions; harness session unchanged; explicit --workspace always wins
- [x] Reuse workspace_config.read_session_state (added in T136) — do not re-derive session state

## Resolution
Bare create_ticket (no --workspace) now consults workspace_config.read_session_state (T136 mirror): harness session -> harness layer; workspace/undeclared -> exit 2 with recovery command. Chose fail-closed for cross-tool consistency + Invariant 3. Added explicit --harness flag (mutually exclusive with --workspace) for programmatic callers; promote_raised_concern.py passes it. See full rationale below.

Closed S26 2026-05-31.
A bare invocation now calls `_resolve_bare_layer()`, which reads
`workspace_config.read_session_state(ROOT)` and mirrors T136 exactly:
- `STATE_HARNESS` → harness layer (unchanged behavior)
- `STATE_WORKSPACE` → exit 2, error names the active slug and hands over the exact
  `--workspace <slug>` command
- `STATE_UNDECLARED` → exit 2, points at /session-start

Chose **fail-closed** over routing for cross-tool consistency with T136 (a user
shouldn't get silent routing from one ticket tool and a hard error from the other in
the same session) and to honor Invariant 3 (never silently default to a best guess).

**Scope addition beyond the ACs — `--harness` flag.** `promote_raised_concern.py`
shells out to `create_ticket.py` to create a harness ticket; under fail-closed it
broke (its tmp harness had no declared session). Rather than couple a programmatic
harness operation to ambient session state, I added an explicit `--harness` flag
(mutually exclusive with `--workspace`) that asserts harness intent and bypasses the
session check. `promote_raised_concern` now passes it. This is the explicit-intent
escape hatch the AC's "explicit --workspace always wins" gestures at, made symmetric:
`--workspace SLUG` and `--harness` are both explicit; only bare invocation consults
session state. More aligned with Invariant 3 (explicit over implicit) than requiring
the caller's session to happen to be `__harness__`.

Tests: 7 new in `TestSessionAwareRouting` (harness/workspace/undeclared/empty bare
cases, explicit-wins-over-state, `--harness` bypass declared+undeclared, mutual
exclusion). Existing `_setup` now declares `__harness__` (bare-invocation tests are
harness-session tests). 495 pass (incl. the 19 promote tests the change first broke,
now green via `--harness`).
