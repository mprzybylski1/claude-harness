---
id: T143
title: Collapse duplicated .active_workspace tri-state reader — hook imports workspace_config.read_session_state
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S26 2026-05-31
closed: S26 2026-05-31
---

## Problem

T136 added `workspace_config.read_session_state()` (the *attribution* authority — which
layer a telemetry record / index / SR is stamped with), but `check_cross_layer_writes.py`
(the *enforcement* authority — which writes get blocked) kept its own private copy of the
same `.active_workspace` tri-state read. They agree today (same `__harness__` sentinel,
`.strip()`, empty→undeclared rule) but could silently diverge — a future fourth state, a
sentinel rename, or different whitespace handling done in one file — and the disagreement
would be invisible: the tool that attributes and the hook that blocks would have different
ideas of what layer the session is. (S25 Opus review, Concern #2.)

## Acceptance Criteria

- [x] scripts/hooks/check_cross_layer_writes.py imports and uses workspace_config.read_session_state() instead of maintaining its own copy of the tri-state read (currently check_cross_layer_writes.py:34-57)
- [x] Single source of truth: the attribution authority (read_session_state) and the enforcement authority (the hook) read the same sentinel (__harness__), whitespace handling, and empty->undeclared rule
- [x] The workspace_config.py:131-132 deferred-debt note is removed once the hook imports the shared function
- [x] Existing tests/test_check_cross_layer_writes.py still pass; the four state x target combinations remain covered

## Resolution

`check_cross_layer_writes.py` now imports `workspace_config.read_session_state` and calls
it with the hook's `ROOT`, deleting its private `_read_session_state` + the duplicated
`_HARNESS_SENTINEL`/`STATE_*` constants. The `STATE_*` names are re-exported as aliases of
`_wc.STATE_*` so `main()` stays readable. The import resolves from the hook's own location
(`_default_root/scripts/tools`), independent of the `HARNESS_ROOT` env override (which only
redirects the state-file read) — verified live: a cross-workspace block fires correctly with
`HARNESS_ROOT` pointed at a tmp dir.

Trust-boundary nuance handled: this hook is the sole Inv 2/4 confidentiality enforcer, and
Claude Code treats exit 2 as *block* but any other non-zero (e.g. an uncaught `ImportError`
→ exit 1) as a *non-blocking* error → the tool proceeds (fail-OPEN). So the new import is
wrapped to map any import failure to a stderr-warn + `exit 2`. Because the hook matches
`Edit|Write` only, that block still leaves Bash as a `git checkout` recovery surface —
consistent with T142's fail-closed-with-recovery design.

Two new guard tests (`TestSingleSourceOfTruth`): the hook imports the shared reader, and it
carries no private `_read_session_state` / `_HARNESS_SENTINEL`. The 23 existing behavioral
tests (all four state×target combinations) stay green. 485 pass.

The `workspace_config.py` deferred-debt note (former lines 131-132) is replaced with a
single-source-of-truth statement.

## Resolution
check_cross_layer_writes.py now imports workspace_config.read_session_state (called with the hook's ROOT) and drops its private _read_session_state + duplicated _HARNESS_SENTINEL/STATE_* constants; STATE_* re-exported as aliases of _wc.STATE_*. Single source of truth for the tri-state read — the attribution authority (read_session_state) and the enforcement authority (the hook) can no longer silently diverge (Opus S25 Concern #2). Import resolves from the hook's own location, independent of HARNESS_ROOT (verified live). Trust-boundary nuance: this is the sole Inv 2/4 enforcer and Claude Code treats exit 2 as block but other non-zero (ImportError->exit 1) as non-blocking=fail-OPEN, so the import is wrapped to map failure to stderr+exit 2; Edit|Write-only matcher leaves Bash as recovery surface (T142 design). 3 new guard tests incl. mutation-verified fail-closed-on-missing-import; 23 existing behavioral tests (all 4 state x target combos) stay green. workspace_config.py debt note replaced with single-source statement.

Closed S26 2026-05-31.
