---
name: session-start
model: claude-sonnet-4-6
description: Begin a new session — read context files in order, surface outstanding invariant violations, report ticket aging and phase gate status, then await direction.
---

# Session Start

Run this at the beginning of every session before doing any other work.

## Step 1 — Read context files in order

Read these files **sequentially**:

1. `docs/architecture_invariants.md` — hard constraints that never change without an explicit decision
2. Run `python scripts/tools/extract_session_brief.py` and read its output —
   this prints Current Phase & Status, Active Work, and the last 5 Session Log entries.
   Do not read `docs/sessions.md` directly; the script extracts what matters.
3. Run `python scripts/tools/extract_opus_key_sections.py --with-carry-forwards` and read its output —
   this prints `## Invariant Violations`, `## Architectural Concerns`, and
   `## Suggested Next Session Focus` (capped at 5 items; full list in opus_notes.md),
   then any Opus carry-forward items outstanding ≥5 sessions.
   Do not read `docs/opus_notes.md` directly; the script extracts what matters.
4. `docs/tickets/INDEX.md` — ticket overview (ID, title, severity, age); this is sufficient for the session briefing
5. Run `python scripts/tools/surface_stale_tickets.py` — prints any open ticket over the triage
   threshold (default 50 sessions). Output is empty if no tickets qualify.
6. Run `python scripts/tools/repo_hygiene.py --warn-only` — prints WARN-level hygiene findings:
   stale infrastructure files, deprecated operational references (dead GitHub Actions
   runner, etc.). Empty when the repo is clean. Not a blocker — address when convenient.
   Run without `--warn-only` for full INFO output on demand.

**Do not read individual files in `docs/tickets/open/` at session start.** Read a specific
ticket body only when the user is actively working on that ticket. The INDEX has everything
needed for situational awareness and the session briefing.

If `docs/archive/` contains relevant reviews (e.g. the user asks about a past session), search
there with `grep`. Do not load archive files into context by default.

## Step 2 — Check for outstanding invariant violations

Use the `## Invariant Violations` output from Step 1.3 (`extract_opus_key_sections.py`).
Do **not** re-read `docs/opus_notes.md` — the script already extracted that section.

- If it says **"None"** → no blocking work, proceed to Step 3.
- If it lists violations → these are **critical blockers**. You must:
  1. List each violation with its ticket ID in the Step 3 briefing.
  2. State explicitly in the briefing: **"New feature work is blocked until these are resolved."**
  3. When the user asks what to work on, offer the violation tickets first. Do not begin
     unrelated work until the user has explicitly acknowledged the violations and decided
     to defer them.

The session-start briefing is the enforcement point for invariant violations — the same role
that `check_session_log.py` plays for session-close. Do not soften violations into suggestions.

## Step 3 — Produce a session briefing

Run `python scripts/tools/current_session.py` to get the current session ID. Use that output
as `CURRENT_SESSION` everywhere below.

Report the following, concisely:

---
**Session:** S[CURRENT_SESSION]

**Phase:** [current phase and gate criteria from sessions.md — what's done, what's remaining]

**Invariant violations to fix first:**
- [List from latest Opus review, or "None — clear to proceed"]

**Open tickets:** [total] — [N critical] / [N high] / [N medium] / [N low]

**Aging (open ≥ 10 sessions):**
- [List ticket IDs, titles, and age — or "None"]

**Triage required** (open ≥ 50 sessions — decision needed this session or explicit deferral):
- [Output of `surface_stale_tickets.py`, or "None"]

**Long-lived carry-forwards** (Opus issues ≥5 sessions unaddressed):
- [Output from `--with-carry-forwards` flag in step 3, or "None"]

**Last session:** [one-line summary from Session Log tail]

**Suggested focus** (based on phase gate and ticket priorities):
- [1-3 specific tickets most relevant to current gate criteria or critical/high severity]
---

## Step 4 — Await direction

Ask the user: **"What do you want to work on today?"**

Do not begin implementation until the user responds. If the briefing surfaces invariant
violations, offer to fix them first but let the user decide.

## What good looks like

- Invariant violations from the prior Opus review are acknowledged before new work begins
- The user knows the current phase gate status without having to ask
- Aging tickets are visible — no silent backlog rot
- The session number is correctly incremented from the last Session Log entry
- The user is asked before work begins, not after

## Do not use this skill when

- The user has already been briefed this session (do not re-run mid-session)
- The user explicitly says to skip the briefing and dive straight into work
