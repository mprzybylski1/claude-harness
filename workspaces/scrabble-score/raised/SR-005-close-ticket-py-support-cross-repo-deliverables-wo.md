---
id: SR-005
from: scrabble-score
raised: S10 2026-05-28
title: "close_ticket.py: support cross-repo deliverables (workspace ticket → harness file)"
severity: medium
status: resolved
harness_ticket: T125
resolved_in: S22
---

## Context

A workspace ticket's deliverable sometimes lives in the **harness repo**
rather than the workspace's project repo — typical cases:

- An edit to `workspaces/<slug>/CLAUDE.md` (workspace-scoped instructions
  that live in the harness repo by design)
- An edit to a shared script in `scripts/tools/` that the workspace uses
- An edit to `workspaces/<slug>/workspace.yaml`

`close_ticket.py --files` only stages files inside the workspace repo
(detected via `git rev-parse --show-toplevel` against the ticket's repo).
There is no equivalent `--harness-files` flag. The operator must coordinate
manually:

1. Commit harness-side deliverable in the harness repo
2. Run `close_ticket.py` in the workspace repo (archive move only)
3. Hope they remember to mention the harness SHA in the workspace commit
   so future bisect/git-archeology can find both halves

S9 / T018 was the trigger case: the workspace CLAUDE.md edit lived in the
harness repo (commit `5f36dbc`), but the T018 ticket file lived in the
scrabble-score repo (commit `3c24ca5`). The two commits land in separate
git histories with no automatic cross-reference.

Not blocking — manual coordination works — but creates friction every time
a workspace ticket touches harness state. Will recur on any ticket that
edits the workspace's harness-side config or shared tooling.

## Proposed change

Option A (minimal): add `--harness-files <path>...` to `close_ticket.py`.
Stages the listed paths in the harness repo and creates a separate
`docs(T###):` commit there before the workspace archive-move commit. Print
the harness SHA in the workspace commit message so both halves are
mutually discoverable via `git log --all --grep=T###`.

Option B (lighter): just teach `close_ticket.py` to detect file paths
inside the harness repo passed to `--files` and refuse with a helpful
error message: "T018 has files in two repos. Commit `<harness-paths>` in
the harness repo first with message `docs(T###): ...`, then re-run
close_ticket.py without those paths."

Option C (process-only): no tool change — document the pattern in the
session-close SKILL.md and rely on operator discipline. Lower
implementation cost; doesn't help with the cross-reference traceability
problem.

Preferred: B for first iteration (cheap, makes the friction visible to the
operator at the right moment), then A if cross-repo close becomes routine.

## Harness disposition

(Filled by harness on promotion or rejection.)
