# Native vs. Custom — what this harness builds, and why

A map of every harness capability against what Claude Code now does **natively**,
so we keep building only what the platform genuinely lacks and stop reinventing
what it already provides.

Written S24 2026-05-30.

> **Caveat on the native column.** Native-feature claims below are limited to
> capabilities verified to exist (auto-memory, subagent `model:` override, the
> core hook events, `/loop`, `/schedule`, plan mode, MCP, OpenTelemetry export,
> JSONL transcripts, `/code-review ultra`). Several more exotic features surfaced
> during research (agent "teams", assorted niche hook events) were **excluded as
> unverified** — do not design against them without confirming first.

---

## One-line answer

The harness's **core — ticketing plus the workspace-isolation model — has no
native equivalent and must stay custom.** That is the genuine value-add. Several
*supporting* layers, however, reinvent things Claude Code now does natively, and
one of them (telemetry) is the subject of an open ticket — which makes
"native vs. custom" a live architectural fork, not a hypothetical.

---

## Verdict table

| Capability | Native equivalent? | Call |
|---|---|---|
| Ticket lifecycle (create/close/index/aging, T-numbering) | none | **Keep custom** |
| Workspace isolation model (multi-repo, scoped docs, `docs_path`) | none | **Keep custom** |
| Cross-layer write governance (`check_cross_layer_writes`, AC gate, fix-commit gate) | hook *system* is native; the *rules* are not | **Keep custom — already uses native primitives correctly** |
| SR boundary-ticketing (workspace→harness `raised/`) | none | **Keep custom** |
| Opus review (session-close / impl-review) | subagent `model:` override; cloud `/code-review ultra` | **Hybrid — native primitive, custom context-prep** |
| Telemetry (`log_tool_usage` → `analyze_tool_log`) | native OTel events + JSONL transcripts | **Keep custom as a thin live-stamped domain index + join key — decided T137, rationale below** |
| Session-start briefing (manual `/session-start`) | `SessionStart` hook can inject context automatically | **Hybrid — keep the briefing, native-ify the trigger** |
| Background ticket impl (`implement_ticket.py` state machine) | partial — `Agent` + `run_in_background` | **Hybrid — keep snapshot/revert, native runner** |
| User memory (`~/.claude/.../memory/MEMORY.md`) | this *is* native auto-memory | **Already native — not custom** |

---

## Bucket 1 — Genuinely custom (no native path; this is the portfolio)

Ticketing, the workspace model, the cross-layer invariants, and SR promotion.
Claude Code has **no concept of a structured ticket, a multi-project workspace,
or a write boundary between layers.** Everything here is real engineering with no
shortcut.

Consequence for the open backlog: the queued fixes **T135** (ticket-counter
scoping) and **T136** (index regen fail-closed) are correctly "fix the custom
thing" — there is nothing native to fall back to.

The governance hooks (`check_ticket_acs`, `check_cross_layer_writes`,
`check_fix_commit_has_code`, `check_session_log`) **use the native hook system the
way it is meant to be used**: native event (`PreToolUse`/`Stop`), custom logic.
That is not reinvention — leave it.

## Bucket 2 — Reinventing native (candidates to thin)

- **Telemetry — DECIDED (T137, S25): keep custom, but as a thin live-stamped
  domain index, not a data store.** The fork (fix the custom logger vs. delete it
  and read native OTel/transcripts) was resolved in favour of **fix + bridge**,
  for reasons that survive scrutiny:
  - **Native has no `S<N>`/workspace concept.** Transcripts are keyed by Claude
    session UUID (23 files in this project dir; one human "session" spans several
    via compaction/`bridge-session`). `/workflow-review` reasons in the harness's
    `(S<N>, workspace)` vocabulary, which only exists in this layer. You cannot
    get `S<N>`-keyed analysis without custom code **either way** — going fully
    native would *relocate* custom code into a transcript parser coupled to an
    undocumented Anthropic-controlled schema, not eliminate it. So "delete it"
    does not actually remove the reinvention; it moves it somewhere more fragile.
  - **Domain keying is only cheap live.** The hook knows the active session and
    workspace at write time (from `.claude/.active_workspace`); reconstructing
    that post-hoc from a UUID-keyed transcript is fuzzy. So the logger stays a
    **live-stamped index**: `(ts, tool, path, S<N>, workspace, claude_session_uuid)`.
  - **It is not a parallel data store.** `claude_session_uuid` == the native
    transcript filename, so the index **joins** to native telemetry for the richer
    per-call data (tokens, full I/O) on demand — no duplication. The join itself
    is deferred until a consumer needs token-level data (its own ticket); nothing
    today does.
  This is the "why custom" rationale that the portfolio note below calls for —
  now on record rather than implied. SR-010's workspace-blind stamping is fixed
  by switching attribution from per-file-path to active-session.
- **`/session-start` trigger.** The briefing content is valuable and custom; the
  *manual invocation* is not. A native `SessionStart` hook can inject
  `additionalContext` automatically, so the briefing loads without the user
  typing the command. Keep the skill's logic; consider firing it from a
  `SessionStart` hook.

## Bucket 3 — Hybrid (native primitive + custom glue)

- **Opus review.** Spawning a subagent with `model: opus` is native (the `Agent`
  tool's `model` param). Worth keeping custom: `prepare_opus_context.py`
  (pre-building the diff/invariants so the reviewer does not burn tool calls) and
  notes rotation. Upgrade available: the review writes markdown that
  `extract_opus_key_sections.py` re-parses — native **structured output (schema)**
  on the subagent would remove that parse layer. `/code-review ultra` is the
  cloud-grade option for branch review.
- **Background implementation.** `run_in_background` on the `Agent` tool covers
  "run detached" natively; the snapshot / revert-on-failure state machine is the
  value-add native does not give. Keep the safety logic; consider native for the
  runner.

---

## The honest portfolio take

Two layers read as "didn't know the platform" to a reviewer unless framed
deliberately: the **custom telemetry logger** (native OTel exists) and **session
protocols as pure scripts** (`SessionStart`/`SessionEnd` hooks exist). Everything
else — ticketing, workspaces, governance — reads as "built what the platform
genuinely lacks," which is the good signal.

Recommended posture: either (a) migrate telemetry + session triggers to native
and delete the custom code, or (b) add a one-paragraph "why custom" rationale to
each (in-session analysis / structured briefing). **Silent reinvention is the
worst of the three** — it invites the "why didn't they use the native feature?"
question with no answer on record.
