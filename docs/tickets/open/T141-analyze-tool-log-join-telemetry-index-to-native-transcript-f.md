---
id: T141
title: analyze_tool_log: join telemetry index to native transcript for token-level data
severity: low
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S25 2026-05-31
closed:
---

## Problem

The live-stamped telemetry index (`.git/session_tool_log.jsonl`) records a
`claude_session_uuid` per call but not token counts or full I/O. Those live in
Claude Code's native transcript. T137 deferred the join here on the premise that
`claude_session_uuid` (= `$CLAUDE_CODE_SESSION_ID`) IS the native transcript filename.
Opus S25 Concern #3 flagged that premise as unverified — env vars have been empty in
this harness's hook subshells before (the stale S3 `$CLAUDE_PROJECT_DIR` note) — and
warned that if it's wrong the field is silent dead weight. This ticket is **deferred
under its own YAGNI clause** (AC #2: no consumer needs token-level data yet), so the
S26 deliverable was the read-only verification, not the join.

## Status: DEFERRED (premise verified S26 2026-05-31)

Not built — no consumer needs token-level data yet (AC #2 YAGNI). Kept open so the
join can be built when a consumer (e.g. a richer /workflow-review token audit) appears.

**Verification of the join-key premise (Opus S25 Concern #3) — both halves hold:**

1. `CLAUDE_CODE_SESSION_ID` **is populated in the hook subshell.** Confirmed two ways
   on Claude Code 2.1.x: it is present in the session env
   (`3a482593-bf4d-47a8-8300-1be8d60e01f4`), and live `.git/session_tool_log.jsonl`
   records carry that exact non-empty value in `claude_session_uuid` — i.e. the hook
   that wrote them saw the var. Not the empty-env failure mode Concern #3 feared.
2. The uuid **maps exactly to a real transcript file**:
   `~/.claude/projects/-Users-mprzybylski-PycharmProjects-claude-harness/3a482593-bf4d-47a8-8300-1be8d60e01f4.jsonl`
   exists. So `claude_session_uuid` is a valid live join key, not dead weight; the
   field should be kept.

Caveat: verified against Claude Code 2.1.x. The `~/.claude/projects/<slugged-cwd>/<uuid>.jsonl`
layout and the env-var name are Claude Code internals; re-confirm both before building
the join if a future version changes them. The build step must still handle transcript
schema/format drift defensively (AC #3).

## Acceptance Criteria

- [ ] Join the live-stamped index (claude_session_uuid) to the native JSONL transcript under ~/.claude/projects/.../<uuid>.jsonl to surface per-call/per-message token counts and full I/O
- [ ] Only build when a consumer needs token-level data (e.g. a richer /workflow-review token audit) — YAGNI until then
- [ ] Handle transcript-schema fragility/format drift defensively; locate the transcript by claude_session_uuid (= filename)
- [ ] This is the deferred half of T137's fix+bridge decision (see docs/native_vs_custom.md telemetry rationale)

## Resolution
(Fill in on close.)
