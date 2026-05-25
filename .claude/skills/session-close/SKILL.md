---
name: session-close
model: claude-sonnet-4-6
description: Close the session cleanly — update workspace-scoped session records, run Opus review against workspace repos, commit per-repo then commit harness docs.
---

# Session Close

You are closing a development session.

Your job is to: update session records, hand off to Opus for a post-session review,
commit workspace repo changes, then commit harness docs.

## Workspace context

Before proceeding, confirm which workspace is active (set in Step 0 of `/session-start`).
If `workspace.yaml` exists in CWD, read it to get workspace name and repos.
All path references below use `workspaces/<WORKSPACE_SLUG>/internal/` unless marked
"harness root". If no workspace is active (harness root session), all paths are the
original global paths (`docs/sessions.md`, `docs/opus_notes.md`, etc.).

**Path substitution:**

| File | Non-workspace | Workspace |
|---|---|---|
| sessions.md | `docs/sessions.md` | `workspaces/<slug>/internal/sessions.md` |
| opus_notes.md | `docs/opus_notes.md` | `workspaces/<slug>/internal/opus_notes.md` |
| Tickets open | `docs/tickets/open/` | `workspaces/<slug>/internal/tickets/open/` |
| Tickets closed | `docs/tickets/closed/` | `workspaces/<slug>/internal/tickets/closed/` |
| INDEX.md | `docs/tickets/INDEX.md` | `workspaces/<slug>/internal/tickets/INDEX.md` |
| archive/ | `docs/archive/` | `workspaces/<slug>/internal/archive/` |
| opus_review_context.md | `docs/opus_review_context.md` | `workspaces/<slug>/internal/opus_review_context.md` |

`docs/system_state.md` and `docs/architecture_invariants.md` are always at harness root.

## Commit discipline — code commits happen at ticket-close, not here

**By the time `/session-close` runs, all code changes in workspace repos must already be
committed — one commit per ticket.**
Step 6 commits: (a) any remaining dirty workspace repo changes, then (b) harness docs only.
If code files still appear in `git status` when you reach Step 6, stage and commit them
first with a `fix:` prefix, then proceed with the docs commit.

The pattern for every ticket closed during a session:
1. Implementation done, tests pass
2. Move ticket file to `workspaces/<slug>/internal/tickets/closed/`
3. **Immediately commit in the workspace repo:** the commit targets the workspace's primary repo
4. Only then move to the next ticket

## Pre-check — Did `/implementation-review` run?

If this was a code session and `/implementation-review` was not run, ask the user:
"Want to run `/implementation-review` first so we can fix issues inline instead of ticketing them?"
If they decline, proceed normally.

## Step 0 — Determine session ID and refresh INDEX.md

Run all three commands:
```
python scripts/tools/current_session.py
python scripts/tools/generate_ticket_index.py --session <N> --tickets-dir workspaces/<slug>/internal/tickets
python scripts/tools/archive_session_log.py --sessions workspaces/<slug>/internal/sessions.md
```

Record the session ID as `CURRENT_SESSION` and numeric part as `N`.

**If the scripts do not yet support these flags**, pass paths as environment variables or
run them without flags and adjust paths manually — note the gap for a follow-up ticket.

## Step 1 — Update sessions.md (workspace-scoped)

Update **two sections** of `workspaces/<WORKSPACE_SLUG>/internal/sessions.md`:

### Active Work section
- List files changed and what changed. Derive from `git diff` across workspace repos.
- Note tickets opened or closed this session (by ID)
- Active Work header: `**S[CURRENT_SESSION] — <one-line summary>**`

### Session Log section
Append one line:
```
S[N] YYYY-MM-DD: <one-line summary>
```

## Step 1b — Update docs/system_state.md (harness root)

```bash
python scripts/tools/update_system_state.py
```

This runs from harness root and reads `docs/sessions.md` for global phase status.
If the workspace's session data should also update global state, do so manually.

## Step 2 — Move closed tickets and write Resolution text

For any ticket being closed this session:
1. Tick all satisfied ACs. For incomplete items add `— DEFERRED to T[N]` or `— N/A: <reason>`.
2. Move file from `workspaces/<slug>/internal/tickets/open/` to `workspaces/<slug>/internal/tickets/closed/`.
3. Set frontmatter: `closed: S[CURRENT_SESSION] YYYY-MM-DD`
4. Write Resolution section. First token must be `S[CURRENT_SESSION] YYYY-MM-DD:`.

**After writing Resolution, commit the workspace repo immediately** (see Commit discipline).

## Step 3 — Classify the session: code-touching or docs-only

```bash
python scripts/tools/classify_session.py
```

Prints `code` or `docs`. For workspace sessions, the check is against the workspace repos
(not the harness root). If the script checks harness root by default, verify manually
whether workspace repo files changed.

## Step 4 — Pre-rotate opus_notes.md

```bash
python scripts/tools/rotate_opus_notes.py \
  --opus workspaces/<slug>/internal/opus_notes.md \
  --archive workspaces/<slug>/internal/archive/
```

Archives the oldest review section to the workspace archive. If the script does not yet
support these flags, run the rotation manually: move the oldest `# Opus Review` section
from `workspaces/<slug>/internal/opus_notes.md` to a dated file in
`workspaces/<slug>/internal/archive/`.

## Step 5 — Review: full Opus (code sessions) or static-only (docs sessions)

### If SESSION_TYPE = code

Generate context targeting the workspace primary repo:

```bash
python scripts/tools/prepare_opus_context.py \
  --repo <primary-repo-path> \
  --sessions workspaces/<slug>/internal/sessions.md \
  --opus workspaces/<slug>/internal/opus_notes.md \
  --output workspaces/<slug>/internal/opus_review_context.md
```

Then spawn the **Opus review agent** (`subagent_type: "general-purpose"`, `model: "opus"`,
`run_in_background: true`) with the workspace-scoped context:

```
You are doing a post-session review for [WORKSPACE NAME].
Session: S[CURRENT_SESSION]

## Start here — read these two files first, in order

1. `workspaces/<slug>/internal/opus_review_context.md`
2. `workspaces/<slug>/internal/opus_notes.md`

Do NOT read files outside workspaces/<slug>/ or the workspace's declared repos.
[... rest of Opus review instructions unchanged ...]

Append your review to `workspaces/<slug>/internal/opus_notes.md`.
```

**Multi-repo Opus context (when workspace has secondary repos):**

- **Primary repo:** full context as above — `prepare_opus_context.py` targets this path.
- **Secondary repos:** for each secondary repo in `workspace.yaml`, run `git diff HEAD` in
  that repo. If the diff is non-empty (dirty — changes made this session), include a brief
  summary block in the Opus prompt:
  ```
  ## Secondary repo: <name> (<path>)
  <paste the git diff or a condensed summary of changed files and their purpose>
  ```
  If the secondary repo is clean (no diff), mention it by name only:
  ```
  Secondary repo <name> had no changes this session.
  ```

**Isolation rule for Opus:** Opus must not read files from other workspaces or from repos
not declared in `workspace.yaml`. State this explicitly in the prompt.

### Step 5b — Proceed with Step 6 prep while Opus runs in background

Verify sessions.md, system_state.md, closed ticket files, and INDEX.md are correct.
Do NOT commit yet — wait for Opus to finish writing to opus_notes.md.

### Step 5c — Generate client progress

> **Note:** The first sentence of each ticket's `## Resolution` is copied verbatim
> to `client/progress.md`. Ensure it is written as a client-facing statement before
> closing the ticket.

If the workspace has a `client_remote` configured in `workspace.yaml`:

1. Generate the client progress summary:
   ```
   python scripts/tools/generate_client_progress.py \
     --workspace workspaces/<slug>/ \
     --session N
   ```
2. If `client_remote` is set, push the `client/` directory to the remote:
   ```
   cd workspaces/<slug>/client/
   git init  # if not already a git repo
   git add .
   git commit -m "progress: S[CURRENT_SESSION] update"
   git push <client_remote> main --force
   ```
   Note: `client/` is gitignored from the harness repo — this push goes to a separate private repo.
3. If `client_remote` is not set, generate `client/progress.md` locally only (no push, no error).

The push to `client_remote` is best-effort — if it fails, log the error and continue with Step 6.

### If SESSION_TYPE = docs

```bash
python scripts/tools/run_static_analysis.py
```

Append a static-analysis summary to `workspaces/<slug>/internal/opus_notes.md`.

## Step 6 — Commit changes

### 6a — Commit dirty workspace repos

For each workspace repo declared in `workspace.yaml`, check `git status`. If dirty,
commit remaining changes (any not already committed per-ticket):

```
cd <repo-path>
git add <changed files>
git commit -m "docs: S[CURRENT_SESSION] session close — <summary>"
```

### 6b — Commit harness docs

Back at harness root:

```bash
python scripts/tools/session_close_commit_msg.py --session N
```

```bash
git add docs/sessions.md \
        docs/system_state.md \
        docs/opus_notes.md \
        docs/archive/ \
        docs/tickets/INDEX.md
git commit -m "docs: S[CURRENT_SESSION] session close — <one-line summary>"
```

**Never include `workspaces/*/internal/` in the harness docs commit.** That data is
gitignored and stays local.

---

## What good looks like

**Hook-enforced:**
- All closed tickets have correct `closed: S[CURRENT_SESSION]` attribution
- No bare `- [ ]` ACs in moved tickets

**Manual checks:**
- sessions.md Active Work header says `**S[CURRENT_SESSION] — ...**`
- sessions.md Session Log has a new entry for S[CURRENT_SESSION]
- opus_notes.md contains exactly 2 `# Opus Review` sections after rotation
- New Opus findings have ticket files in `workspaces/<slug>/internal/tickets/open/`
- Workspace repo commits happened before the harness docs commit
- No workspace internal data in the harness repo git history

## Do not use this skill when

- Nothing was changed — pure question-only session with zero file edits.
