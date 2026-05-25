---
name: session-start
model: claude-sonnet-4-6
description: Begin a new session — detect workspace context, read scoped context files, surface invariant violations and ticket status, then await direction.
---

# Session Start

Run this at the beginning of every session before doing any other work.

## Step 0 — Detect workspace context

Determine whether you are running from **harness root** or **inside a workspace**.

Run:
```
python scripts/tools/workspace.py list
```

- **If the list is empty** and no `workspace.yaml` exists in CWD: you are at harness root
  with no workspaces yet. Proceed to Step 1 using global harness paths.
- **If workspaces exist** and CWD does not contain `workspace.yaml`: you are at harness
  root. Show the workspace list to the user and ask: **"Which workspace are you working
  in today?"** Record the chosen slug as `WORKSPACE_SLUG`. All subsequent path references
  use `workspaces/<WORKSPACE_SLUG>/internal/` as the base.
- **If `workspace.yaml` exists in CWD**: you are already inside a workspace. Read it to
  get the workspace name and repos. Set `WORKSPACE_SLUG` to the current directory name.
  Skip the selection prompt.

**Path substitution for workspace sessions:**

| Context file | Non-workspace path | Workspace path |
|---|---|---|
| Session brief | `docs/sessions.md` | `workspaces/<slug>/internal/sessions.md` |
| Opus notes | `docs/opus_notes.md` | `workspaces/<slug>/internal/opus_notes.md` |
| Tickets INDEX | `docs/tickets/INDEX.md` | `workspaces/<slug>/internal/tickets/INDEX.md` |
| Tickets open | `docs/tickets/open/` | `workspaces/<slug>/internal/tickets/open/` |
| Archive | `docs/archive/` | `workspaces/<slug>/internal/archive/` |

`docs/architecture_invariants.md` is always read from harness root — invariants are global.

## Step 1 — Read context files in order

Read these files **sequentially** (use workspace-scoped paths if in a workspace):

1. `docs/architecture_invariants.md` — hard constraints; always read from harness root
2. Run `python scripts/tools/extract_session_brief.py` with the correct sessions.md path
   and read its output — prints Current Phase & Status, Active Work, and last 5 Session Log entries.
   If in a workspace, pass the workspace path:
   ```
   python scripts/tools/extract_session_brief.py --sessions workspaces/<slug>/internal/sessions.md
   ```
   Do not read sessions.md directly.
3. Run `python scripts/tools/extract_opus_key_sections.py --with-carry-forwards` with the
   correct opus_notes.md path:
   ```
   python scripts/tools/extract_opus_key_sections.py --with-carry-forwards \
     --opus workspaces/<slug>/internal/opus_notes.md
   ```
   Prints `## Invariant Violations`, `## Architectural Concerns`, and
   `## Suggested Next Session Focus`. Do not read opus_notes.md directly.
4. Workspace tickets INDEX (`workspaces/<slug>/internal/tickets/INDEX.md`) — ticket overview
5. Run `python scripts/tools/surface_stale_tickets.py` — prints tickets over triage threshold.
   Empty if none qualify.
6. Run `python scripts/tools/repo_hygiene.py --warn-only` — WARN-level hygiene findings.
   Not a blocker; address when convenient.

**If extract_session_brief.py or extract_opus_key_sections.py do not yet support --sessions
or --opus flags:** read the files directly as a fallback and note the gap.

**Do not read individual ticket files at session start.** The INDEX has everything needed.

If the workspace's `internal/archive/` contains relevant reviews, search with `grep`.

## Step 2 — Check for outstanding invariant violations

Use the `## Invariant Violations` output from Step 1.3.

- If **"None"** → proceed to Step 3.
- If violations listed → these are **critical blockers**:
  1. List each with its ticket ID in the Step 3 briefing.
  2. State: **"New feature work is blocked until these are resolved."**
  3. Offer violation tickets first when the user asks what to work on.

## Step 3 — Produce a session briefing

Run `python scripts/tools/current_session.py` to get the session ID.

---
**Session:** S[CURRENT_SESSION]  
**Workspace:** [workspace name from workspace.yaml, or "harness root (no workspace)"]  
**Repos:** [list repo names and roles from workspace.yaml, or "N/A"]

**Phase:** [current phase and gate criteria — what's done, what's remaining]

**Invariant violations to fix first:**
- [List from latest Opus review, or "None — clear to proceed"]

**Open tickets:** [total] — [N critical] / [N high] / [N medium] / [N low]

**Aging (open ≥ 10 sessions):**
- [List ticket IDs, titles, and age — or "None"]

**Triage required** (open ≥ 50 sessions):
- [Output of `surface_stale_tickets.py`, or "None"]

**Long-lived carry-forwards** (Opus issues ≥5 sessions unaddressed):
- [Output from `--with-carry-forwards`, or "None"]

**Last session:** [one-line summary from Session Log tail]

**Suggested focus:**
- [1-3 specific tickets most relevant to current gate or critical/high severity]
---

## Step 4 — Await direction

Ask the user: **"What do you want to work on today?"**

Do not begin implementation until the user responds.

## What good looks like

- Workspace is identified before any context file is read
- No state from other workspaces appears in the briefing
- Invariant violations from the prior Opus review are acknowledged
- The user knows phase gate status without asking
- Aging tickets are visible
- The user is asked before work begins

## Do not use this skill when

- The user has already been briefed this session (do not re-run mid-session)
- The user explicitly says to skip the briefing and dive straight into work
