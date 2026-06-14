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
  root. Also run:
  ```
  python scripts/tools/portfolio.py
  ```
  Show the portfolio output to the user before the workspace selection prompt. This gives
  the user a cross-workspace overview before choosing where to focus. Then show the
  workspace list and ask: **"Which workspace are you working in today?"** Record the
  chosen slug as `WORKSPACE_SLUG`.

  Then resolve the workspace docs root — this may be inside the project repo if `docs_path`
  is configured:
  ```
  python scripts/tools/workspace_internal_path.py <WORKSPACE_SLUG>
  ```
  Record the output as `INTERNAL`. All subsequent path references use `INTERNAL` as the base.
- **If `workspace.yaml` exists in CWD**: you are already inside a workspace. Read it to
  get the workspace name and repos. Set `WORKSPACE_SLUG` to the current directory name.
  Run `python scripts/tools/workspace_internal_path.py <WORKSPACE_SLUG>` and record as `INTERNAL`.
  Skip the selection prompt.

**Write the session state file** after workspace detection (required by `check_cross_layer_writes.py` hook):
- **Workspace session:** write the slug to `.claude/.active_workspace`:
  ```bash
  echo -n "<WORKSPACE_SLUG>" > .claude/.active_workspace
  ```
- **Harness-root session:** write the harness sentinel:
  ```bash
  echo -n "__harness__" > .claude/.active_workspace
  ```

The `check_cross_layer_writes` hook fails closed if this file is missing or empty — all doc writes
will be blocked until you declare session type.

**Path substitution for workspace sessions:**

| Context file | Non-workspace path | Workspace path |
|---|---|---|
| Session brief | `docs/sessions.md` | `<INTERNAL>/sessions.md` |
| Opus notes | `docs/opus_notes.md` | `<INTERNAL>/opus_notes.md` |
| Tickets INDEX | `docs/tickets/INDEX.md` | `<INTERNAL>/tickets/INDEX.md` |
| Tickets open | `docs/tickets/open/` | `<INTERNAL>/tickets/open/` |
| Archive | `docs/archive/` | `<INTERNAL>/archive/` |

`docs/architecture_invariants.md` is always read from harness root — invariants are global.

## Step 1 — Read context files in order

Read these files **sequentially** (use workspace-scoped paths if in a workspace):

1. `docs/architecture_invariants.md` — hard constraints; always read from harness root
2. Run `python scripts/tools/extract_session_brief.py` with the correct sessions.md path
   and read its output — prints Current Phase & Status, Active Work, last 5 Session Log entries,
   and a **Hook errors (last 5)** section tailing `.git/session_tool_log.errors`.
   If the errors file is absent or empty the section shows "none".
   If in a workspace, pass the workspace path:
   ```
   python scripts/tools/extract_session_brief.py --sessions <INTERNAL>/sessions.md
   ```
   Do not read sessions.md directly.
   **If Hook errors shows any lines**, surface them in the Step 3 briefing under a
   "Hook errors detected" heading so the operator sees them immediately.
3. Run `python scripts/tools/extract_opus_key_sections.py --with-carry-forwards` with the
   correct opus_notes.md path:
   ```
   python scripts/tools/extract_opus_key_sections.py --with-carry-forwards \
     --opus <INTERNAL>/opus_notes.md
   ```
   Prints `## Invariant Violations`, `## Architectural Concerns`, and
   `## Suggested Next Session Focus`. Do not read opus_notes.md directly.
4. Workspace tickets INDEX (`<INTERNAL>/tickets/INDEX.md`) — ticket overview
5. Run `python scripts/tools/surface_stale_tickets.py` — prints tickets over triage threshold.
   Empty if none qualify.
6. Run `python scripts/tools/repo_hygiene.py --warn-only` — WARN-level hygiene findings.
   Not a blocker; address when convenient.
7. **Harness root only (no workspace selected):** Run
   `python scripts/tools/list_raised_concerns.py` — aggregates pending workspace→harness
   concerns across all workspaces. Empty output means no pending concerns; omit the
   section from the briefing entirely in that case. If output is non-empty, include it
   under **Pending raised concerns** in the Step 3 briefing.

8. **Workspace session only:** Run
   `python scripts/tools/surface_workspace_concerns.py --workspace <WORKSPACE_SLUG>` —
   surfaces the workspace's own raised concerns and auto-archives terminal items after
   showing them once. Empty output means no concerns; omit the section from the briefing.
   Include non-empty output under **Your raised concerns** in the Step 3 briefing.

9. **Workspace session only:** Run
   `python scripts/tools/check_docs_path_gitignored.py <WORKSPACE_SLUG>` —
   checks whether the workspace's `docs_path` is inside a gitignored directory.
   If output is non-empty, surface it in the Step 3 briefing as a high-severity warning
   under **docs_path gitignored**. If empty, omit the section.
   Skipped silently when docs_path is not configured.

10. Run `python scripts/tools/check_session_continuity.py` — detects whether the
    about-to-be-used session number S<N> was already stamped on tickets by a prior,
    unlogged session (a numbering collision, e.g. the ghost S30). For a workspace
    session, pass the workspace paths:
    ```
    python scripts/tools/check_session_continuity.py \
      --sessions <INTERNAL>/sessions.md \
      --tickets-dir <INTERNAL>/tickets/open \
      --archive-dir <INTERNAL>/archive
    ```
    Empty output means no collision; omit the section. If non-empty, surface it under
    **Session-number collision** in the Step 3 briefing and reconcile before opening
    new S<N> tickets.

**Do not read individual ticket files at session start.** The INDEX has everything needed.

If the workspace's archive contains relevant reviews, search with `grep` in `<INTERNAL>/archive/`.

## Step 2 — Check for outstanding invariant violations

Use the `## Invariant Violations` output from Step 1.3.

- If **"None"** → proceed to Step 3.
- If violations listed → these are **critical blockers**:
  1. List each with its ticket ID in the Step 3 briefing.
  2. State: **"New feature work is blocked until these are resolved."**
  3. Offer violation tickets first when the user asks what to work on.

## Step 3 — Produce a session briefing

Run the appropriate command to get the session ID:
- **Workspace session:** `python scripts/tools/current_session.py --sessions <INTERNAL>/sessions.md`
- **Harness root:** `python scripts/tools/current_session.py`

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

**Carry-forwards** (Opus issues ≥2 sessions unaddressed):
- [Output from `--with-carry-forwards`, or "None"]

**Last session:** [one-line summary from Session Log tail]

**Hook errors detected:**
- [Last 5 lines from Hook errors section, or "None"]

**Pending raised concerns:** *(harness root only — omit section entirely if list_raised_concerns.py produces no output)*
```
[Full output of python scripts/tools/list_raised_concerns.py]
```

**Your raised concerns:** *(workspace session only — omit section entirely if surface_workspace_concerns.py produces no output)*
```
[Full output of python scripts/tools/surface_workspace_concerns.py --workspace <WORKSPACE_SLUG>]
```

**docs_path gitignored:** *(workspace session only — omit section entirely if check_docs_path_gitignored.py produces no output)*
- [Output of check_docs_path_gitignored.py, or omit]

**Session-number collision:** *(omit section entirely if check_session_continuity.py produces no output)*
```
[Output of check_session_continuity.py, or omit]
```

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
- Hook errors from `.git/session_tool_log.errors` are surfaced if present
- Harness-root sessions show pending raised concerns from all workspaces
- Workspace sessions show only their own raised concerns; terminal items auto-archived after surfacing
- Both concerns sections omitted entirely when empty (no noise)
- Gitignored docs_path surfaced as high-severity warning for workspace sessions
- The user is asked before work begins

## Do not use this skill when

- The user has already been briefed this session (do not re-run mid-session)
- The user explicitly says to skip the briefing and dive straight into work
