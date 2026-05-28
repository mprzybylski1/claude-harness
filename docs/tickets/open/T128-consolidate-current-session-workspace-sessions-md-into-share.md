---
id: T128
title: Consolidate _current_session + _workspace_sessions_md into shared session_lookup module
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed:
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [ ] New scripts/tools/session_lookup.py exposes one public function each (resolve_workspace_sessions_md, resolve_current_session); used by all 5 callers
- [ ] Existing tests for raise_for_harness, surface_workspace_concerns, reject_raised_concern, create_ticket, close_ticket pass unchanged
- [ ] No behavioural change in any caller (CalledProcessError handling, fallback semantics preserved per caller)
- [ ] Net diff is LoC-negative across the touched files

## Resolution
(Fill in on close.)
