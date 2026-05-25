---
id: T018
title: internal_dir should fail loudly when docs_path directory does not exist
severity: medium
status: closed
phase: 2
layer: tools
opened: S4 2026-05-25
closed: S4 2026-05-25
---

## Problem

`workspace_config.internal_dir()` calls `Path(docs_path).expanduser().resolve()` without
verifying the directory exists. A deleted or misconfigured docs_path silently produces
empty ticket lists in `portfolio.py`, an empty sessions log in `extract_session_brief.py`,
and would create a fresh sessions.md on first write — masking the configuration error
rather than surfacing it.

## Acceptance Criteria

- [x] `active_internal_dir()` exits 2 when `docs_path` is configured but the
  directory does not exist — clear error message with recovery hint
- [x] Hooks that call `active_internal_dir()` propagate the failure (exit 2)
- [x] Test: missing docs_path directory triggers an error, not empty results
- [x] All existing tests still pass

## Resolution

S4 2026-05-25: Missing docs_path directories now fail loudly instead of producing silent empty results.

Added the existence check to `active_internal_dir()` in `workspace_config.py`: when `docs_path` is configured but the resolved directory doesn't exist, prints a clear error with recovery hint and exits 2. `internal_dir()` stays a pure path resolver (no side effects). Updated `test_active_internal_dir_with_docs_path` to create the harness_dir (the test was previously passing by omission). 1 new test; 69/69 pass.
