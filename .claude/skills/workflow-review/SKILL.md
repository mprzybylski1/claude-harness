---
name: workflow-review
model: claude-opus-4-7
description: Analyse the workflow layer — skills, hooks, scripts, CLAUDE.md — and surface friction, waste, and brittleness. Works in two modes: (1) in-session retrospective while context is warm, (2) cold-start periodic audit. Both modes produce ranked improvements and offer to open tickets.
---

# Workflow Review

Structured analysis of the **workflow layer** — skills, hooks, scripts, and process
instructions — not production code or tests. Your job is to find friction, waste, and
brittleness and propose concrete fixes ranked by value vs effort.

Run at any point during or after a session. Most valuable either right before
`/session-close` (warm context) or as a periodic health check (every ~10 sessions).

## When to use

- After a session that felt slow, required workarounds, or surfaced harness gaps
- When the same manual step has repeated across multiple sessions
- When an Opus review has flagged the same process issue 3+ sessions running
- Proactively every ~10 sessions as a periodic health check
- When new workspace tooling was exercised for the first time

## Do not use when

- The session was entirely docs-only with no harness tooling exercised
- You have already run workflow-review this session
- The question is about production code, tests, or domain strategy

---

## Step 1 — Detect scope and gather context

### 1a — Determine workspace scope (run this first)

```bash
python3 scripts/tools/workspace.py list
```

**If a workspace is active this session** (user selected one at session-start, or
`workspace.yaml` exists in CWD):

- The review scope is **that workspace only**. Analyse its workflow experience:
  its session log, tickets, opus notes, and how harness tooling served it.
- Do NOT produce harness-global findings during a workspace review. Harness
  infrastructure improvements belong in a harness-root session.
- Resolve the workspace docs root:
  ```bash
  python3 scripts/tools/workspace_internal_path.py <WORKSPACE_SLUG>
  ```
  Record the output as `INTERNAL`. Use `INTERNAL` for all path substitutions below.

**If no workspace is active** (harness root session):

- The review scope is the **harness itself** — skills, hooks, scripts, CLAUDE.md.
- Use the harness-root paths below (no `INTERNAL` substitution needed).

### 1b — Determine warm/cold mode

- **Warm mode** (in-session): you have direct recall of this session's events.
  Use recall as primary signal; files confirm or extend it.
- **Cold mode** (periodic audit): no session recall. Files are the only signal.

### 1c — Read context files

```bash
python3 scripts/tools/current_session.py
# workspace: python3 scripts/tools/current_session.py --sessions <INTERNAL>/sessions.md

python3 scripts/tools/extract_session_brief.py
# workspace: python3 scripts/tools/extract_session_brief.py --sessions <INTERNAL>/sessions.md

python3 scripts/tools/extract_opus_key_sections.py --with-carry-forwards
# workspace: add --opus <INTERNAL>/opus_notes.md
```

Then read:
1. `CLAUDE.md` — Session Start Protocol section and Working Style (harness root always)
2. `.claude/skills/session-start/SKILL.md`
3. `.claude/skills/session-close/SKILL.md`
4. `ls scripts/tools/` and `ls scripts/hooks/` — inventory what exists (harness root always)
5. `.claude/settings.json` — which hooks are wired and how (harness root always)
6. Sessions log — last 20 lines (frequency/length signal):
   - harness root: `docs/sessions.md`
   - workspace: `<INTERNAL>/sessions.md`
7. Tickets index — open tickets (avoid duplicating existing tracking):
   - harness root: `docs/tickets/INDEX.md`
   - workspace: `<INTERNAL>/tickets/INDEX.md`

Do **not** read individual ticket files, full `opus_notes.md`, or any production source.

---

## Step 2 — Telemetry (when available)

If `workflow_telemetry: true` is set in `harness.yaml`, run:

```bash
python3 scripts/tools/analyze_tool_log.py --session S[CURRENT_SESSION]
```

This always reads from the harness-root `.git/session_tool_log.jsonl` — telemetry is
global regardless of workspace. Filter by session to isolate workspace-session traffic.

Use the output as objective signal alongside qualitative findings. If telemetry is
disabled or the log is empty, note it in the output and move on.

---

## Step 3 — Analysis across five dimensions

Work through each dimension. In warm mode, recall specific moments first, then verify
against files. In cold mode, derive everything from the files. If a dimension has no
findings, say so briefly and move on.

### Dimension 1 — Prose doing mechanical work

Look for instructions in skills or CLAUDE.md that describe a deterministic operation a
script could do instead. Flag any step that:
- Asks the model to parse a pattern from text (dates, IDs, file lists)
- Asks the model to check membership in a fixed list (file path prefixes, section names)
- Asks the model to count or compare numbers
- Repeats the same logic across multiple skills without a shared script

Also ask (warm mode):
- Which scripts were called more than once for the same purpose?
- Which bash commands failed and required a retry or workaround?
- Which tool calls could have been avoided with better harness support?

For each finding: name the step, describe the script that would replace it, estimate lines.

### Dimension 2 — Token cost audit

For each file read at session start or session close, estimate token cost and ask:
- Is the whole file needed, or just a section?
- Is it read more than once per session (start + close + Opus)?
- Could a script pre-extract the relevant portion?
- Is the file growing unboundedly (session log, archive)?

Flag files where cost > benefit — where a trimmed read or script extraction would save
meaningfully without losing safety-critical information.

### Dimension 3 — Recurring Opus process complaints

From the `extract_opus_key_sections.py` output, look for complaints that:
- Appear in multiple sessions (phrases like "N-session carry-forward", "recurring",
  "broken record", "same pattern")
- Describe mechanical failures (wrong session ID, stale index, missing attribution)
- Have an open ticket that hasn't moved in many sessions

Also ask (warm mode):
- Does any friction from this session match Opus carry-forward findings?
- Is this friction new, or encountered in previous sessions?

For each: is this addressable by a script or hook? If yes, that is the fix.

### Dimension 4 — Hook opportunities

Look at `.claude/settings.json` and skill files. Ask: what events happen in the workflow
that currently require a manual step but could be automated?

Also ask (warm mode):
- What did I do manually that should be automated?
- Were there permission prompts that should be pre-allowed?

**Good hook candidates:**
- Any "run script X after doing Y" instruction in a skill
- Any "verify Z before committing" check that is currently prose
- Any file that must stay consistent with another (e.g. INDEX.md ↔ ticket files)

**Poor hook candidates:**
- Steps requiring judgment (writing session notes, ticket content)
- Steps only meaningful at specific points in a skill flow, not on every file write

### Dimension 5 — Growing files and SKILL gaps

**Growing files — check** (use workspace paths when in a workspace):
- sessions.md Session Log — one line per session, never trimmed
- opus_notes.md — should be held to ~2 sessions by rotation script
- archive/ — should grow but not be re-read

For each: at what line count does it become a meaningful token cost? Is there already
a rotation/archiving mechanism?

**SKILL gaps — ask:**
- Which SKILL.md steps didn't match what the scripts actually support?
- Were any SKILL steps skipped because they were inapplicable or unclear?
- Was the session-start briefing accurate? Did it surface the right tickets?
- Did any script use harness-root paths instead of workspace paths?
- Were there workspace context gaps or path confusion?

---

## Step 4 — Produce the report

```
## Workflow Review — S[N] YYYY-MM-DD

**Summary:** One sentence on the overall state of the workflow layer.

### Immediate fixes (< 10 lines, no new files)
For each: `[VALUE: H/M/L | EFFORT: low]` — what to change and where.

### Short-term improvements (new script or hook, < 50 lines)
For each: `[VALUE: H/M/L | EFFORT: medium]` — what the script does, which skill/CLAUDE.md
step it replaces, estimated token or time saving.

### Longer-term structural changes
For each: `[VALUE: H/M/L | EFFORT: high]` — what the change is and why it's deferred.

### Recurring Opus complaints still open
List any complaint that has appeared 3+ sessions without a fix. For each: ticket ID if
one exists, or "not ticketed" with a one-line description of the simplest fix.

### What is already working well
Two or three things the workflow does well that should not be changed.
```

---

## Step 5 — Propose tickets

For each finding rated **medium or high value**, offer to open a ticket.

Present each as:

> **Proposed ticket:** [title]
> Severity: [low/medium/high]
> Problem: [one paragraph]
> ACs: [bullet list]
>
> Open this ticket? [y/n]

Only write the ticket file after the user confirms. Use `docs/tickets/TEMPLATE.md`.
Assign the next available T-number by checking the highest existing ID in the active
tickets location:
- harness root: `docs/tickets/open/` and `docs/archive/`
- workspace: `<INTERNAL>/tickets/open/` and `<INTERNAL>/archive/`

Low-severity findings: batch them and ask once whether to open all, some, or skip.

---

## Step 6 — Log to sessions.md (optional)

If the review surfaced meaningful findings, add a brief note to the **Active Work**
section of the active sessions.md (`docs/sessions.md` at harness root,
`<INTERNAL>/sessions.md` in a workspace):

```
Workflow review: [N] friction points; [N] tickets proposed; [N] opened.
```

---

## Standards

- Every finding must reference the specific file and section where the problem lives.
- Do not recommend changes to production code, tests, or strategy specs.
- Do not recommend adding more process steps — only simplifying or automating existing ones.
- If a finding is already tracked by an open ticket, note the ticket ID and do not duplicate it.
- Prioritise by: (tokens saved × sessions per year) + (error rate reduction). A 1-line
  fix that prevents a recurring 15-session failure beats a 50-line script saving 500 tokens.

## What good looks like

- Every friction point has a specific root cause (not "scripts were slow")
- Proposed improvements are scoped to a single file or script each
- Ticket ACs are testable
- The verdict gives a clear signal about workflow health
- Low-value findings are batched, not individually escalated