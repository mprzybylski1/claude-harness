---
id: T137
title: Telemetry session-stamping is workspace-blind; analyze_tool_log filter pulls foreign records
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S24 2026-05-30
closed: S25 2026-05-31
source: scrabble-score/SR-010
---

## Problem

Promoted from scrabble-score/SR-010.

## Decision required (before implementing)

**Fix the custom logger vs. replace it with native telemetry.** `log_tool_usage.py`
re-implements what Claude Code already emits natively: OpenTelemetry tool-use
events plus the JSONL session transcript under `~/.claude/projects/.../`. This
ticket as written ("fix the workspace stamping") assumes we keep the custom
logger — but that may be the wrong fix. Decide first:

- **Option A — fix custom (this ticket as scoped).** Add workspace-aware stamping
  to `log_tool_usage.py` + `--workspace` to `analyze_tool_log.py`. Keeps
  `analyze_tool_log.py`'s **in-session workflow report**, which native telemetry
  does not give cheaply (native OTel needs an external backend like
  CloudWatch/Datadog; native transcripts carry no per-tool token counts).
- **Option B — replace with native.** Delete `log_tool_usage.py` (and the
  PostToolUse `.*` hook wiring) and read native OTel/transcripts instead. Removes
  a reinvented layer and sidesteps this entire workspace-blind bug class — but
  loses the on-demand in-session analysis unless re-derived from transcripts.

Do not implement until this is chosen. See `docs/native_vs_custom.md` for the
full native-vs-custom analysis (T137 is the one open ticket where this fork is
live). If Option B wins, this ticket's scope changes from "fix" to "remove +
migrate", and the AC list below must be rewritten.

## Context

Surfaced in scrabble-score S12 during `/workflow-review`. `log_tool_usage.py` stamps
each record with the harness-global `S<N>`, not the workspace session. So
`analyze_tool_log.py --session S12` from this workspace returned 92 records belonging
to a *different historical S12* (a harness session editing `log_tool_usage.py`,
`foo.py`, `test_telemetry.py` — none of which this workspace touched), while none of
the actual S12 scrabble-score activity was attributable.

Net effect: telemetry is unusable as a per-session signal from inside a workspace —
the `--session` filter silently collides across layers. This degrades every
`/workflow-review` run done from a workspace (the dimension-2 token audit and
error/retry analysis read foreign data). The S11 session-close note already flagged
"Telemetry undercount noted for harness investigation" — same root cause, now
confirmed as a layer collision rather than a count bug. Not blocking.

## Proposed change

1. `log_tool_usage.py` records the active workspace (from `.claude/.active_workspace`)
   alongside the session ID on each log line.
2. `analyze_tool_log.py` accepts `--workspace SLUG` and filters on the
   `(workspace, session)` pair; when run from a workspace with only `--session`, it
   auto-detects the active workspace.
3. Test covers the workspace-filtered path; harness-root behaviour unchanged.

Shares the SR-008/009 root cause — a `workspace_context.py` helper resolving
`(slug, internal_path, sessions_md)` would let the hook and analyzer agree on scope.
## Acceptance Criteria

- [x] `log_tool_usage.py` records the active workspace (from `.claude/.active_workspace`) — attribution switched from per-file-path (T057) to active-session via `workspace_config.read_session_state`; also stamps `claude_session_uuid` (live join key). Verified in the live log this session.
- [x] `analyze_tool_log.py` accepts `--workspace SLUG` and filters on the `(workspace, session)` pair; with only `--session` (and the default log), it auto-detects the active workspace, so the S<N> filter no longer collides across layers.
- [x] Test covers the workspace-filtered path; harness-root behaviour unchanged — `TestActiveWorkspaceStamping` (active-based stamping incl. the bare-Bash attribution fix) + `TestWorkspaceFilter` (filter, harness alias, legacy-record default, gated auto-detect). The decision gate was resolved (fix + bridge, not replace); rationale in `docs/native_vs_custom.md`. Deferred transcript-join → T141.

## Coordination

Part of the workspace-blind tooling sweep (SR-007 family): **T135 (SR-008) →
T136 (SR-009) → T137 (SR-010)**, triaged S24 as "3 tickets, helper-first".

- **Depends on T135's `workspace_context.py` helper.** Consume the shared
  resolver so `log_tool_usage.py` and `analyze_tool_log.py` agree on workspace
  scope with the rest of the harness tooling, rather than re-deriving it.
- No file overlap with T135/T136 (telemetry scripts are independent of the
  ticket-tooling scripts), so this ticket can land any time after the helper exists.

## Resolution
Decision gate resolved: FIX the custom logger + BRIDGE to native (not replace).
Full rationale recorded in docs/native_vs_custom.md (telemetry section). In short:
native transcripts are richer but UUID-keyed with no S<N>/workspace concept;
/workflow-review reasons in the harness's (S<N>, workspace) vocabulary, which only
exists in this layer; going fully native would relocate custom code into a fragile
transcript parser, not remove it. So the logger stays as a thin LIVE-STAMPED INDEX
that joins to native telemetry on demand.

Fix (SR-010 root cause): attribution switched from per-file-PATH (T057) to
ACTIVE-SESSION. log_tool_usage.py now reads .claude/.active_workspace via
workspace_config.read_session_state (the T136 helper — the SR-008/009/010
convergence realized) and stamps every call in a session with that session's
(workspace, S<N>). The old path-based scheme under-attributed any call that didn't
touch a declared-repo file (bare Bash, harness reads) to the harness layer — the
"none of the actual S12 activity was attributable" half of the SR.

analyze_tool_log.py: added --workspace SLUG (alias "harness" → ""), filters on
(workspace, session); a missing workspace key counts as "" (legacy records). With
only --session and the DEFAULT log, it auto-detects the active workspace from
.active_workspace — so `--session S12` from a workspace no longer pulls foreign-
layer S12 records. Auto-detect is gated to "no --log override" so explicit-log /
ad-hoc analysis stays decoupled from session state.

Live bridge: each record now carries claude_session_uuid = $CLAUDE_CODE_SESSION_ID,
which IS the native transcript filename (verified live: e693d4fb… ↔ e693d4fb….jsonl).
This makes the index join-ready to native telemetry for token-level data WITHOUT a
parallel store. The join itself is deferred (YAGNI — nothing consumes tokens today)
→ T141.

Removed the path-based subsystem (_detect_workspace/_candidate_paths/_list_workspaces
/_session_for_workspace) and its TestWorkspaceAwareStamping class; replaced with
TestActiveWorkspaceStamping + TestWorkspaceFilter. All other telemetry tests (rotation,
rate-limit, bootstrap, _extract_path, analyzer) untouched and green.

Out of scope, noted: session derivation still uses last-logged+1, so close-time
records can stamp one session high (the T139 timing skew, pre-existing; path-based
had it too). The live claude_session_uuid is the stable key to reconcile against the
transcript regardless of that skew.

Live-verified this session (log_tool_usage is a script, read fresh per call): real
log records now carry active-based (workspace, S<N>) + the correct UUID.

Files: scripts/hooks/log_tool_usage.py, scripts/tools/analyze_tool_log.py,
scripts/tools/workspace_config.py (no change this ticket — reused T136 helpers),
tests/test_telemetry.py, docs/native_vs_custom.md. Full suite green (minus the 13
pre-existing test_workflow_orchestrator ImportErrors, unrelated).

Closed S25 2026-05-31.
