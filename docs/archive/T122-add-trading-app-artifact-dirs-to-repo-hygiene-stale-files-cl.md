---
id: T122
title: add trading-app artifact dirs to repo_hygiene STALE_FILES; clean up dead skip-list entries
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S21 2026-05-28
closed: S21 2026-05-28
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] STALE_FILES includes WARN entries for `core/`, `execution/`, `data/`, `strategies/`, `risk_engine/` with "Trading-app artifact directory" hint
- [x] ALWAYS_SKIP no longer references `data/`, `research/results/`, `research/contexts/`
- [x] Test `test_stale_files_lists_trading_app_artifact_dirs` asserts the 5 entries; `test_always_skip_drops_dead_trading_app_entries` asserts cleanup; `test_trading_app_artifact_entries_are_warn_severity` enforces WARN
- [x] `repo_hygiene.py --warn-only` still reports clean (none of the artifact dirs exist) — `test_real_harness_still_clean` verifies

## Resolution
Added WARN-severity STALE_FILES entries for core/, execution/, data/, strategies/, risk_engine/ — these top-level dirs belong to the trading-app source project and should never appear in the harness. Removed dead ALWAYS_SKIP entries (data/, research/results/, research/contexts/) carried over from the trading-app codebase that the harness no longer contains. 4 new tests in TestTradingAppArtifactGuards.

Closed S21 2026-05-28.
