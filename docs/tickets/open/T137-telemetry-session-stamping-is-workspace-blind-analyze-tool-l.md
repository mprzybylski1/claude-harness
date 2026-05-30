---
id: T137
title: Telemetry session-stamping is workspace-blind; analyze_tool_log filter pulls foreign records
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S24 2026-05-30
closed:
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

- [ ] `log_tool_usage.py` records the active workspace (from `.claude/.active_workspace`)
- [ ] `analyze_tool_log.py` accepts `--workspace SLUG` and filters on the
- [ ] Test covers the workspace-filtered path; harness-root behaviour unchanged.

## Coordination

Part of the workspace-blind tooling sweep (SR-007 family): **T135 (SR-008) →
T136 (SR-009) → T137 (SR-010)**, triaged S24 as "3 tickets, helper-first".

- **Depends on T135's `workspace_context.py` helper.** Consume the shared
  resolver so `log_tool_usage.py` and `analyze_tool_log.py` agree on workspace
  scope with the rest of the harness tooling, rather than re-deriving it.
- No file overlap with T135/T136 (telemetry scripts are independent of the
  ticket-tooling scripts), so this ticket can land any time after the helper exists.

## Resolution
(Fill in on close.)
