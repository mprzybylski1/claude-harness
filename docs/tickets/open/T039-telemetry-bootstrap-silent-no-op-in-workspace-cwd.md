---
id: T039
title: Telemetry bootstrap silently no-ops when session runs from a workspace cwd
severity: medium
status: open
phase: 2
layer: infra
opened: S9 2026-05-25
closed:
---

## Problem

After a full session run from a workspace cwd
(`workspaces/scrabble-score/`, S2 in that workspace = S9 at harness root),
the telemetry sentinel `.git/workflow_telemetry_on` is **absent** at session
end, despite `harness.yaml` containing `workflow_telemetry: true`. The
expected log file `.git/session_tool_log.jsonl` does not exist. No error
file `.git/session_tool_log.errors` was written either.

`python scripts/tools/toggle_telemetry.py status` confirms the
inconsistency:
```
Sentinel file: absent (OFF)
harness.yaml workflow_telemetry: True
```

The bootstrap logic in `scripts/hooks/log_tool_usage.py:128-138` is
correct in isolation:
1. If sentinel missing AND `_yaml_telemetry_enabled()` returns true →
   touch sentinel, exit (drop one record).
2. Subsequent calls hit the fast path and log.

A standalone YAML regex check confirms `_yaml_telemetry_enabled()` would
return `True` against the current `harness.yaml`. So the bootstrap path
should have fired on the first PostToolUse call this session — it didn't.

This is a regression against T035 (S8) which fixed the bootstrap
exit-after-touch behaviour. Whatever T035 verified now no longer holds
under workspace-cwd sessions.

## Hypothesis (to verify, not yet confirmed)

`.claude/settings.json` at harness root configures the hook as:
```json
{ "type": "command", "command": "python3 scripts/hooks/log_tool_usage.py" }
```
The path is **relative**. When Claude Code runs the hook with the current
working directory set to a workspace
(`workspaces/scrabble-score/`), `scripts/hooks/log_tool_usage.py` does
not resolve — there is no `scripts/` under the workspace. If Claude Code
executes the command with `cwd=workspace`, the hook would silently fail
to start (no output → no error file → no sentinel touch → no log).

Alternative hypotheses worth ruling out before fixing:
1. Claude Code resolves hook commands relative to the settings.json file
   location (not cwd) — in which case the relative path is fine and the
   bug lies elsewhere.
2. PostToolUse hooks aren't invoked at all when running from a
   subdirectory that has no `.claude/settings.json` of its own (i.e.
   settings.json discovery walks up but hook firing doesn't).
3. The hook fires but `ROOT = Path(__file__).resolve().parents[2]`
   computes the wrong root under some path/symlink condition.

## Acceptance Criteria

- [ ] Reproduce the silent no-op deterministically from a workspace cwd.
      Likely repro: from `workspaces/scrabble-score/`, run any Bash tool
      with telemetry on and the sentinel absent; check
      `.git/workflow_telemetry_on` afterward.
- [ ] Root-cause identified (one of the hypotheses above, or another).
      Document in this ticket's Resolution.
- [ ] Fix applied. Options depending on root cause:
      - **If hook command path is the issue:** make the command absolute
        in `.claude/settings.json`, OR have the hook wrapper compute its
        own absolute path independent of cwd.
      - **If hook discovery is the issue:** add a workspace-level
        `.claude/settings.json` that points to the harness hooks (or
        document the limitation).
- [ ] Smoke test added that runs the hook from a non-harness-root cwd
      and asserts the sentinel + log entry appear.
- [ ] Existing T035 tests still pass.

## Notes

Discovered S2 in scrabble-score workspace (S9 at harness root) while the
user was checking that all telemetry had been committed. Telemetry data
is gitignored by design (lives in `.git/`), so the "did you commit all
telemetry data?" answer was *"there was none to commit"* — which then
surfaced this regression.

Related closed tickets for context:
- T026 (workflow_telemetry_hook_logged — original implementation)
- T033 (hook subprocess overhead when off)
- T035 (bootstrap exit-after-touch — the fix this regresses against)

CLAUDE.md / TDD: telemetry is not safety-critical, but verifying the
hook fires under workspace cwd genuinely is a test-first situation —
the bug is a missing test for that scenario. Add the test before
re-fixing.

## Resolution
(Fill in on close.)
