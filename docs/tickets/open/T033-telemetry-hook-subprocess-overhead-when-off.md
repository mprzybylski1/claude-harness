---
id: T033
title: log_tool_usage.py pays subprocess + YAML-load cost on every tool call when telemetry is off
severity: medium
status: open
phase: 2
layer: infra
opened: S7 2026-05-25
closed:
---

## Problem

S6 Opus review Concern #9 (deferred). The PostToolUse hook
`scripts/hooks/log_tool_usage.py` is registered with matcher `.*` in
`.claude/settings.json` and therefore fires after every tool call. Inside
the hook:

1. Python interpreter starts.
2. `harness_config` is imported (which loads `harness.yaml` via PyYAML).
3. `_telemetry_enabled(harness)` checks `workflow_telemetry` (default
   `False` — disabled).
4. If disabled, the hook returns without writing.

On a session with hundreds of tool calls, this pays the interpreter +
import + YAML-load cost universally for an opt-in feature that is OFF by
default. T026 (the telemetry feature itself) is closed; this is a
hardening follow-up.

## Acceptance Criteria

- [ ] Implement one of the two mitigations Opus suggested (whichever is
      simpler to ship without breaking existing telemetry):
  - **Option A — sentinel file:** check for
    `.git/workflow_telemetry_on` (or similar) at the top of the script,
    before any non-stdlib import; exit immediately if absent. Sentinel is
    created/removed by a helper script the user toggles.
  - **Option B — settings.json gating:** add the hook to
    `.claude/settings.json` only when telemetry is enabled, via an
    `enable-telemetry.py` setup script that edits settings.
- [ ] The OFF-state hook completes in well under 10 ms (stdlib-only path).
- [ ] The ON-state writes a record exactly as before — no regression vs.
      T026's behavior.
- [ ] Test or measurement that demonstrates the OFF-state overhead delta.
- [ ] Documentation updated (`harness.yaml` comments and/or a short note in
      the relevant skill) to describe the new toggle mechanism.

## Notes

Surfaced as Concern #9 in the S6 Opus review (opus_notes.md). User noted
in S7 that the hook fired ~hundreds of times during a workspace session
that gathered zero telemetry data (config commented out in `harness.yaml`).

Option A is probably the simpler ship — a 5-line top-of-file check. Option
B requires a settings-editing utility and is more invasive but cleaner
architecturally.

Out of scope for this ticket: Concerns #10 (`analyze_tool_log.py`
session-boundary retries) and #11 (`prepare_opus_context.py` source
header) from the same S6 review — file separately if/when prioritized.

## Resolution

(Fill in on close.)
