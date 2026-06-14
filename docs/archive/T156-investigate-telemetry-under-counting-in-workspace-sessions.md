---
id: T156
title: Investigate telemetry under-counting in workspace sessions
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S29 2026-06-01
closed: S30 2026-06-15
---

## Problem

S3 generated ~200+ tool calls; telemetry log captured 21 tagged S3 (only 2 tagged workspace: sub-tracker). The PostToolUse hook is silently dropping most tool calls. Without reliable telemetry, /workflow-review loses its objective signal.

## Acceptance Criteria

- [x] Root cause of under-counting identified and fixed → the dramatic historical
      under-count (sub-tracker S3: ~200 actual vs 21 logged) is **not reproducible now**.
      Measured the current session with the new tool: 197 telemetry / 200 native = **98%**.
      The historical loss is attributable to the T138 cwd-drift hook deadlock (hooks
      hung/skipped; fixed S25). A separate, confirmed data-integrity bug was found and
      fixed: `claude_session_uuid` was empty in ~68% of records because it read the
      unreliable `CLAUDE_CODE_SESSION_ID` env var — now sourced from the stdin payload
      (`session_id` → `transcript_path` stem → env var).
- [x] workspace field correctly populated for workspace sessions → verified correct for
      captured calls (scrabble-score = 952 records, tagged accurately). The remaining
      gap is capture-vs-total, not mislabeling; the session-field conflation (ghost S30
      inflating counts) is the separate T165 collision, now guarded.
- [x] Regression/smoke check → new `scripts/tools/telemetry_coverage.py` compares
      telemetry record count vs native transcript `tool_use` count per session (joined by
      the now-reliable uuid) and reports a coverage %. Tests in
      `tests/test_telemetry_coverage.py` + uuid-source tests in `tests/test_telemetry.py`.

### Watch-item (not a confirmed bug)

Low workspace totals (menu-planner = 26, sub-tracker = 18) *may* indicate that tool
calls made while Claude Code runs from the project repo's own cwd (a different
`.claude/settings.json`, without the harness hooks) aren't captured — only the
harness-cwd portion is. Unconfirmed (needs a known-heavy workspace session measured
with `telemetry_coverage.py`). Flagged here rather than opening a speculative ticket.

## Resolution
Investigation: under-counting is not reproducible in current sessions — telemetry_coverage.py measures the current session at 98% (197 telemetry / 200 native tool_use). The historical sub-tracker S3 (~200 actual, 21 logged) is attributable to the T138 cwd-drift hook deadlock (hooks hung/skipped; fixed S25). Found and fixed a separate data-integrity bug: claude_session_uuid was empty in ~68% of records because the hook read the unreliable CLAUDE_CODE_SESSION_ID env var; now sourced from the PostToolUse stdin payload (session_id, then transcript_path stem, then env var). Added telemetry_coverage.py as a repeatable smoke check (native transcript vs telemetry, joined by the now-reliable uuid). workspace field verified correctly populated for captured calls (scrabble-score=952). Watch-item recorded (not ticketed): low workspace totals may reflect project-repo-cwd sessions that don't load the harness hooks — unconfirmed. Tests: 4 uuid-source + 4 coverage; full suite 602 green.

Closed S30 2026-06-15.
