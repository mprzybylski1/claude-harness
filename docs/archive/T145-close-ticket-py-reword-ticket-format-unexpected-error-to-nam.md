---
id: T145
title: close_ticket.py: reword 'ticket format unexpected' error to name the remediation
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S26 2026-05-31
closed: S26 2026-05-31
---

## Problem

The default (replace) path errored with `ERROR: ## Resolution placeholder not found —
ticket format unexpected` when the operator had removed the placeholder by authoring
rich Resolution content during the work. "Ticket format unexpected" reads like a parse
failure when the real cause is benign. (Surfaced by S26 workflow review.)

## Acceptance Criteria

- [x] When ## Resolution section has no placeholder, error message names both remediations: restore (Fill in on close.) so --resolution can replace it, or pass --append to add the new text after existing content
- [x] Test covers the new wording on the missing-placeholder path

## Resolution

Done as part of T144 (the better error message is T144's AC #3 — the reworded text
fires on the same no-placeholder branch that `--append` is the primary fix for).
The `_replace_resolution` final branch now prints a two-bullet error naming both
remediations, and `test_close_ticket_resolution.py::TestReplaceMode::
test_missing_placeholder_error_names_both_remediations` asserts the new wording
(and that "ticket format unexpected" is gone). No separate code change beyond T144.

Done as part of T144: the reworded no-placeholder error (naming both remediations, dropping 'ticket format unexpected') is T144's AC #3, covered by test_missing_placeholder_error_names_both_remediations. No separate code change.

Closed S26 2026-05-31.
