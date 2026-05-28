---
id: T131
title: architecture_invariants.md: reconcile placeholder Invariants 1-2 (4-session Opus carry-forward)
severity: low
status: closed
phase: 2
layer: process
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed: S23 2026-05-28
---

## Problem

`docs/architecture_invariants.md` shipped with placeholder Invariants 1 & 2 ("Invariant
1 — [Name]" / "Rule: [State the rule]") and a non-applicable Invariant 3 (append-only
audit log — no audit table in harness). Opus flagged the placeholder for 5 consecutive
sessions (S18–S22 carry-forward). The doc's own preface says each invariant should be
"checkable by a specific grep or test"; replacing the placeholders requires anchoring
each rule to a concrete verification command against current harness source.

## Acceptance Criteria

- [x] Either fill in Invariants 1 and 2 with concrete harness rules (e.g. 'all hook scripts must sys.exit(2) on block', 'no writes to .claude/.active_workspace outside session-start') with verification commands, or delete the placeholder file entirely
- [x] Invariant 5 verification clause updated to reference check_cross_layer_writes.py (which actually enforces the workspace-write side now)
- [x] Opus S22 carry-forward note resolved

## Resolution
Replaced placeholder Invariants 1-3 with concrete grep-anchored rules: (1) workspace↔harness session-number separation, (2) session-type declaration required for protected writes, (3) fail-closed on workspace-boundary ambiguity. Renumbered the prior Invariant 5 (workspace isolation) to Invariant 4 and updated its verification to also reference the cross-layer hook. Dropped Invariant 4 (fail-closed-on-exceptions) and Invariant 3 (append-only audit log) — the former was too broad to grep-anchor and the latter does not apply to harness (no audit table). All 5 grep verifications run today and return meaningful matches against current source (raise_for_harness.py:106/115, surface_workspace_concerns.py:72, check_cross_layer_writes.py:34/38/45/82, tests/test_check_cross_layer_writes.py boundary tests). Retires the 5-session S18-S22 carry-forward.

Closed S23 2026-05-28.
