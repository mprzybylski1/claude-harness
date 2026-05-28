---
id: T126
title: session-start: surface_workspace_concerns.py stages archives but does not commit them
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed: S22 2026-05-28
source: scrabble-score/SR-006
---

## Problem

Promoted from scrabble-score/SR-006.

## Context

`surface_workspace_concerns.py` (invoked by `/session-start` Step 1.8) auto-
archives terminal SR items after surfacing them once — moves them from
`workspaces/<slug>/raised/SR-NNN.md` to `workspaces/<slug>/raised/archive/`.
The rename is **staged** in the harness repo but not committed. The
operator inherits a pre-staged housekeeping change at the start of every
session that has resolved SRs since the last visit.

S9 hit this: SR-002 and SR-003 (resolved in S21) were pre-staged at
session-start. I had to create a separate `chore: auto-archive resolved
SRs` commit before starting T017/T018 work, because the staged housekeeping
didn't belong in any subsequent ticket commit. Per CLAUDE.md commit
discipline ("one commit per ticket"), the only clean shape is a dedicated
`chore:` commit for the auto-archive.

Skill text (`session-start/SKILL.md`) does not mention this. A first-time
operator wouldn't know whether the staged rename is "their problem to
commit" or "the next session-close will handle it" — it's neither, it sits
across sessions until manually committed.

Not blocking — operators figure it out by inspecting `git status` — but
it's avoidable friction.

## Proposed change

Two reasonable options:

**Option A (auto-commit):** `surface_workspace_concerns.py` creates the
`chore:` commit itself after staging the renames. One commit per session
that has auto-archives; deterministic and zero operator burden. Risk: the
script makes a write to git history during what's nominally a *read* step
of session-start — unusual semantics.

**Option B (surface the work):** `surface_workspace_concerns.py` prints a
warning line in the session-start briefing: *"Note: N resolved SRs were
archived (staged in git). Commit with: `git commit -m 'chore: archive
resolved SRs S<N>' workspaces/<slug>/raised/`"*. Operator commits as part
of their session-start ritual or before first ticket. Side-steps the
"script writes to history" concern.

Preferred: B — keeps session-start a read-mostly phase, but eliminates the
"what's this staged rename?" surprise.
## Acceptance Criteria

- [x] surface_workspace_concerns.py auto-commits archive moves after staging them (Option A)
- [x] Commit uses pathspec — only the archive paths are committed, unrelated staged work in the operator's tree is preserved
- [x] Commit message includes the workspace's current session id (`chore: auto-archive resolved SRs S<N>`)
- [x] Commit failure (signing issue, pre-commit hook reject, etc.) falls back to pre-T126 behaviour: moves remain staged + warning printed
- [x] Session-start no longer leaves a pre-staged housekeeping change for the operator to deal with

## Resolution
Implemented Option A per the T126 disposition (re-litigated A vs B vs C-prime in-session: C-prime would have required session-close to grow cross-repo behaviour — the same shape we just refused in T125 — so it was the wrong cost/value trade). Auto-commit happens via 'git -C <ROOT> commit -- <staged paths>' with explicit pathspec, so unrelated staged work in the operator's tree is preserved. Commit message includes the workspace's current session id resolved through _workspace_sessions_md(slug). If any step fails (no git identity, signing issue, pre-commit hook reject), the script falls back to pre-T126 behaviour: moves remain staged and a warning explains how to commit manually. 3 new tests cover auto-commit happy path with session id in HEAD message, unrelated-staged-work isolation, and pre-commit-hook-reject fallback.

Closed S22 2026-05-28.
