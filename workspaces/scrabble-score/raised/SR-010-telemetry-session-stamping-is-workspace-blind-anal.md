---
id: SR-010
from: scrabble-score
raised: S12 2026-05-30
title: Telemetry session-stamping is workspace-blind; analyze_tool_log filter pulls foreign records
severity: medium
status: resolved
harness_ticket: T137
resolved_in: S25
---

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

## Harness disposition

(Filled by harness on promotion or rejection.)
