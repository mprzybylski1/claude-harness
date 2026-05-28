---
id: T128
title: Consolidate _current_session + _workspace_sessions_md into shared session_lookup module
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed: S23 2026-05-28
---

## Problem

Five tools (`raise_for_harness.py`, `surface_workspace_concerns.py`,
`reject_raised_concern.py`, `create_ticket.py`, `close_ticket.py`) each kept a
local `_current_session` helper, and two of them additionally duplicated a
`_workspace_sessions_md` resolver. T132 surfaced the cost of this duplication:
the twin helpers had silently diverged in fail-closed semantics (one would
contaminate the workspace audit trail, the other wouldn't), and the name
collision made it impossible to tell which behaviour you were getting without
opening the file. Consolidation must preserve each caller's distinct None /
subprocess-error policy — fail-closed for tracked-field writes, warn-and-omit
for commit-message use, harness-fallback for ticket creation.

## Acceptance Criteria

- [x] New scripts/tools/session_lookup.py exposes one public function each (resolve_workspace_sessions_md, resolve_current_session); used by all 5 callers
- [x] Existing tests for raise_for_harness, surface_workspace_concerns, reject_raised_concern, create_ticket, close_ticket pass unchanged
- [x] No behavioural change in any caller (CalledProcessError handling, fallback semantics preserved per caller)
- [x] Net diff is LoC-negative across the touched files

## Resolution
Created scripts/tools/session_lookup.py with two thin primitives: resolve_workspace_sessions_md(slug, root) and call_current_session(sessions_md, root). All 5 callers now route through it. Each caller keeps its own None-case and CalledProcessError policy at the call site (fail-closed exit 2 for raise_for_harness — preserves T132; warn-and-omit/return-None for surface_workspace_concerns — preserves T126; harness-fallback for create/close/reject — preserves existing behaviour). Two-thin-functions design chosen over a single on_missing enum so the per-call-site policy stays visible — exactly the kind of name-collision-hiding-semantics that motivated T132. resolve_workspace_sessions_md uses the more discriminating exception handling (ImportError/OSError/yaml.YAMLError separated) from the surface_workspace_concerns baseline rather than the broader Exception catch. LoC: new module 47 lines; existing callers -52 net; total net -5 (AC #4 satisfied). All 115 affected tests + 440 in the full suite pass with no behavioural change.

Closed S23 2026-05-28.
