---
id: T010
title: _yaml_load swallows YAML parse errors — workspace detection silently fails
severity: critical
status: open
phase: process
layer: infra
opened: S1 2026-05-25
closed:
---

## Problem

`scripts/tools/workspace_config.py:14` — `_yaml_load` catches bare `Exception: return {}`,
which makes a malformed `workspace.yaml` indistinguishable from a missing one. When
`active_workspace()` returns `None` due to a parse error, all hooks fall through to
harness-root paths. Ticket writes then land in `docs/tickets/closed/` of the harness
instead of being blocked. This is an Invariant 4 violation in the workspace-detection trust path.

## Acceptance Criteria

- [ ] `_yaml_load` distinguishes `OSError` (file missing → return `{}`) from
  `yaml.YAMLError` (malformed → log to stderr and exit 2, or re-raise)
- [ ] `ImportError` (yaml not installed) is not swallowed — propagates to caller
- [ ] `test_workspace_config.py` — new test: feed malformed YAML to `load_workspace()`;
  assert it does NOT return `{}` silently (expect exception or sys.exit 2)
- [ ] All existing workspace tests still pass

## Notes

Opus S1 finding #1 and #5. Finding #5 is a subset — the bare `Exception` also hides
`ImportError` and `AttributeError`. Both are fixed by the same narrowing.

## Resolution
