---
name: implementation-review
model: claude-sonnet-4-6
description: Run a mid-session Opus review after implementation is done — findings go to conversation for inline fixes, not tickets.
---

# Implementation Review

Run after implementation is done but before session close. Opus reviews the diff
and reports findings directly to the conversation so you can fix them immediately.
No tickets created, no writes to opus_notes.md — that stays with session-close.

## When to use

After you've finished implementing and tests pass, but before `/session-close`.
This catches issues while context is warm so they get fixed inline instead of
becoming ticket churn for the next session.

## Steps

### Step 1 — Build the review context

**Harness-root session** (no active workspace):

```bash
python scripts/tools/prepare_opus_context.py
```

Builds `docs/opus_review_context.md` with the harness session diff.

**Workspace session** — pass the primary repo path and workspace-scoped session
files (matches session-close Step 5):

```bash
python scripts/tools/prepare_opus_context.py \
  --repo <primary-repo-path> \
  --sessions <INTERNAL>/sessions.md \
  --opus <INTERNAL>/opus_notes.md \
  --output <INTERNAL>/opus_review_context.md
```

Without `--repo`, the script targets the harness repo's git, which is empty for
workspace sessions — the Opus reviewer then "reviews" a 0-line diff and reports
clean by definition. **Check the script's output line for the diff size**: if it
shows `0 diff lines` in a workspace session, you missed the flags — re-run with
the workspace form above before spawning the reviewer.

Safe to call multiple times per session.

### Step 2 — Spawn Opus reviewer

Use the **Agent tool** with `subagent_type: "general-purpose"` and `model: "opus"`:

```
You are doing a mid-session implementation review for a safety-critical automated
trading system. Your job is to find issues that can be fixed RIGHT NOW — before
session close.

## Rules

- **Report findings to the conversation only.** Do NOT create ticket files.
- **Do NOT write to docs/opus_notes.md.** Session-close owns that file.
- **Do NOT read any file** beyond the two listed below. Use confidence qualifiers
  ("diff suggests..." vs "confirmed:") for anything you can't verify from the context.

## Read these two files, in order

1. `<CONTEXT_PATH>` — session diff, architecture invariants, static analysis
   results. Do NOT run git diff or re-read source files separately.
2. `docs/architecture_invariants.md` — hard constraints (always at harness root).

Substitute `<CONTEXT_PATH>` with the `--output` path used in Step 1:
- Harness-root session: `docs/opus_review_context.md`
- Workspace session: `<INTERNAL>/opus_review_context.md`

## What to look for

1. **Invariant violations** — use the static analysis section, not source reads.
2. **Fail-closed semantics** — exceptions caught and swallowed in core/, silent
   fallbacks, auto-resume without human action.
3. **Concrete bugs** — off-by-one, missing edge cases, wrong return values.
4. **Test gaps** — new safety-critical code paths without test coverage.
5. **Schema/interface issues** — type mismatches, missing fields.

## What to skip

- Architectural musings and future-proofing suggestions
- Style nits and naming preferences
- Things that are already tracked in open tickets (check `docs/tickets/INDEX.md`
  if unsure, but don't read individual ticket files)

## Output format

Return a flat numbered list of findings. For each:
- File path and line number (or function name)
- What's wrong
- How to fix it

If everything looks clean, say so in one sentence. Don't pad the output.
```

### Step 3 — Fix findings inline

Review Opus's findings. Fix everything that's actionable. Run tests after fixes.
Anything that genuinely can't be fixed now (blocked on external dependency, needs
design discussion) — note it for session-close, which may ticket it.

When fixes are done and tests pass, **commit before returning to session-close**:
`git add <changed files> && git commit -m "fix: <summary of review fixes>"`.
Per-ticket commit discipline means session-close should only need to commit docs/.

## Do not use this skill when

- No code was changed this session (docs-only work)
- You haven't finished implementing yet (review a partial diff = noise)
- Session-close is about to run anyway and there's nothing to fix
