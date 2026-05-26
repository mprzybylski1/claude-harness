---
id: T063
title: Test pollution into real telemetry log + closed/ vs archive/ ticket split
severity: low
status: closed
phase: 2
layer: infra
opened: S12 2026-05-26
closed: S13 2026-05-26
---

## Problem

Two unrelated minor cleanups batched per /workflow-review S12 recommendation:

1. **Test pollution of telemetry log.** `tests/test_telemetry.py::TestLogToolUsageHook` tests invoke the actual hook via subprocess with synthetic payloads, which then write entries to the real `.git/session_tool_log.jsonl`. Telemetry shows multiple `"path": "foo.py"` records stamped with the current session — fake activity that contaminates analysis. Fix: patch `_LOG_PATH` (and `_SENTINEL`) in those tests, or convert them to in-process tests like `test_record_includes_workspace_field` does.

2. **Two ticket-archive directories.** `docs/tickets/closed/` holds T001–T038; `docs/archive/` holds T039+ and all session opus_notes archives. `close_ticket.py` writes only to `docs/archive/`. The split is a historical artifact of a directory restructure but is undocumented and confusing.

## Acceptance Criteria

- [x] (1) `TestLogToolUsageHook.test_bootstrap_creates_sentinel_from_yaml` and `test_bootstrap_works_from_workspace_cwd` and `test_exits_zero_with_any_state` no longer write to the real `.git/session_tool_log.jsonl`. Re-run the suite and confirm the log is unchanged.
- [x] (2) Decision made: either move all `docs/tickets/closed/*.md` into `docs/archive/` (and delete `closed/`), OR add a one-line note in `CLAUDE.md` documenting the historical split. Either is acceptable.

## Notes

Both are tiny. Bundled because neither warrants a standalone ticket. Surfaced by /workflow-review S12.

## Resolution

Converted 4 subprocess TestLogToolUsageHook tests to in-process using mock.patch.object(ltu, ROOT, fake_root) — no more writes to real telemetry log. Added CLAUDE.md note documenting closed/ vs archive/ historical split.

Closed S13 2026-05-26.
