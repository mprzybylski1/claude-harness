---
name: workflow-review
description: Reflect on the current session's workflow, surface friction points, and propose harness improvements as tickets.
---

# Workflow Review

Structured retrospective on the current session's workflow. No agent spawned — Claude
reflects on its own in-session experience and produces actionable improvement proposals.

Run at any point during or after a session. Most valuable right before `/session-close`
while context is warm.

## When to use

- After a session that felt slow, required workarounds, or surfaced gaps in the harness
- When a script didn't behave as documented
- When you notice the same manual step repeating across sessions
- Proactively at the end of any session where new workspace tooling was exercised

## Do not use this skill when

- The session was entirely docs-only with no harness tooling exercised
- You have already run workflow-review this session

---

## Step 1 — Gather session context

Read the current open ticket list and session brief to ground the reflection:

```bash
python scripts/tools/current_session.py
python scripts/tools/extract_session_brief.py
cat docs/tickets/INDEX.md
```

For workspace sessions, use the workspace-scoped paths:
```bash
python scripts/tools/current_session.py --sessions <INTERNAL>/sessions.md
python scripts/tools/extract_session_brief.py --sessions <INTERNAL>/sessions.md
cat <INTERNAL>/tickets/INDEX.md
```

---

## Step 1b — Telemetry data (when available)

If `workflow_telemetry: true` is set in `harness.yaml`, run the analysis script and
include its output in the retrospective as objective signal alongside qualitative findings:

```bash
python scripts/tools/analyze_tool_log.py --session S[CURRENT_SESSION]
```

If telemetry is disabled or the log is empty, skip this step and note it in the verdict.

---

## Step 2 — Systematic reflection

Work through each category below. For each one, recall specific moments from this
session. If nothing applies in a category, say so briefly and move on.

### 2a — Script and tool friction

Ask yourself:
- Which scripts were called more than once for the same purpose? Why?
- Which script flags were missing, wrong, or not documented?
- Which bash commands failed and required a retry or workaround?
- Which tool calls (Read, Edit, Bash) could have been avoided with better harness support?
- Were there any permission prompts that should be pre-allowed?

### 2b — SKILL gaps and deviations

Ask yourself:
- Which SKILL.md steps didn't match what the scripts actually support?
- Were any SKILL steps skipped because they weren't applicable or were unclear?
- Was the session-start briefing accurate? Did it surface the right tickets?
- Did session-close run cleanly, or were there manual workarounds?

### 2c — Workspace and path issues

Ask yourself:
- Did any script use harness-root paths instead of workspace paths?
- Was workspace context missing or incorrect at any point?
- Were there untracked files, missing .gitignore entries, or path confusion?

### 2d — Repetition and missing automation

Ask yourself:
- What did I do manually that should be automated (a hook, a script flag, a pre-check)?
- What did I have to look up or re-derive that should be cached or pre-computed?
- Were there any repeated patterns across multiple tickets that suggest a missing abstraction?

### 2e — Cross-session signals

Ask yourself:
- Is this friction new, or have I encountered it in previous sessions?
- Does it match any Opus carry-forward findings in the current opus_notes.md?

---

## Step 3 — Produce the retrospective

Format your findings as follows. Be specific — file paths, flag names, script names.
If a category has no findings, omit it.

```
## Workflow Review — S[N] [YYYY-MM-DD]

### Friction points

1. [Specific friction] — [what happened]
2. ...

### Root causes

1. [Root cause for friction #1] — [why it exists]
2. ...

### Proposed improvements

1. [Concrete change] — [which file/script/skill] — [severity: low/medium/high]
2. ...

### Verdict

[One sentence: was this session smooth, rough, or mixed? What's the single biggest
workflow bottleneck right now?]
```

---

## Step 4 — Propose tickets

For each proposed improvement rated **medium or high**, offer to open a ticket.

Present each as:

> **Proposed ticket:** [title]
> Severity: [low/medium/high]
> Problem: [one paragraph]
> ACs: [bullet list]
>
> Open this ticket? [y/n]

Only write the ticket file after the user confirms. Use the standard ticket template
(`docs/tickets/TEMPLATE.md`). Assign the next available T-number by checking the
highest existing ID in `docs/tickets/open/` and `docs/tickets/closed/`.

Low-severity findings: list them at the end as a block and ask once whether to
open them all, open some, or skip.

---

## Step 5 — Log to sessions.md (optional)

If the retrospective surfaced meaningful findings, add a brief note to the
**Active Work** section of sessions.md:

```
Workflow review: [N] friction points; [N] tickets proposed; [N] opened.
```

This makes the review visible to the next session-start briefing.

---

## What good looks like

- Every friction point has a specific root cause (not "scripts were slow")
- Proposed improvements are scoped to a single file or script each
- Ticket ACs are testable
- The verdict gives a clear signal about workflow health
- Low-value findings are batched, not individually escalated
