---
id: T010
title: _yaml_load swallows YAML parse errors — workspace detection silently fails
severity: critical
status: closed
phase: process
layer: infra
opened: S1 2026-05-25
closed: S2 2026-05-25
---

## Problem

`scripts/tools/workspace_config.py:14` — `_yaml_load` catches bare `Exception: return {}`,
which makes a malformed `workspace.yaml` indistinguishable from a missing one. When
`active_workspace()` returns `None` due to a parse error, all hooks fall through to
harness-root paths. Ticket writes then land in `docs/tickets/closed/` of the harness
instead of being blocked. This is an Invariant 4 violation in the workspace-detection trust path.

## Acceptance Criteria

- [x] `_yaml_load` distinguishes `OSError` (file missing → return `{}`) from
  `yaml.YAMLError` (malformed → log to stderr and exit 2, or re-raise)
- [x] `ImportError` (yaml not installed) is not swallowed — propagates to caller
- [x] `test_workspace_config.py` — new test: feed malformed YAML to `load_workspace()`;
  assert it does NOT return `{}` silently (expect exception or sys.exit 2)
- [x] All existing workspace tests still pass

## Notes

Opus S1 finding #1 and #5. Finding #5 is a subset — the bare `Exception` also hides
`ImportError` and `AttributeError`. Both are fixed by the same narrowing.

## Resolution

Split `_yaml_load` exception handling: `import yaml` moved outside the try block (so `ImportError` is never caught), `except (FileNotFoundError, OSError): return {}` for missing files, `except yaml.YAMLError: raise` for malformed content. Added `tests/test_workspace_config.py` with 4 tests covering missing file, valid YAML, malformed YAML raises, and malformed YAML does not silently return `{}`. All 51 tests pass.
