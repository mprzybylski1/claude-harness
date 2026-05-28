---
id: SR-006
from: scrabble-score
raised: S10 2026-05-28
title: "session-start: surface_workspace_concerns.py stages archives but does not commit them"
severity: low
status: raised
harness_ticket:
resolved_in:
---

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

## Harness disposition

(Filled by harness on promotion or rejection.)
