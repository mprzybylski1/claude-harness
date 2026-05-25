---
id: T036
title: harness_config.load_for_repo fail-closed on malformed YAML (S6 Bug #2)
severity: high
status: closed
phase: 2
layer: infra
opened: S8 2026-05-25
closed: S8 2026-05-25
---

## Problem

S6 Bug #2 / Invariant 4 violation. `load_for_repo` silently fell back to harness root
config when workspace `harness.yaml` was malformed, causing wrong code/docs classification.

## Acceptance Criteria

- [x] `load_for_repo` exits 2 with clear ERROR message when existing harness.yaml fails to parse.
- [x] Test updated to expect exit 2 and ERROR in stderr.

## Resolution

S8 2026-05-25: `except Exception` block now prints ERROR and calls `sys.exit(2)` instead of warning and falling back silently. Test updated accordingly.
