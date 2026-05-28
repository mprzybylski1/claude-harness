---
id: T125
title: close_ticket.py: support cross-repo deliverables (workspace ticket → harness file)
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed: S22 2026-05-28
source: scrabble-score/SR-005
---

## Problem

Promoted from scrabble-score/SR-005.

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
## Acceptance Criteria

- [x] close_ticket.py refuses (exit 1) when any --files path resolves to a different git repo than the ticket
- [x] Refusal happens before any destructive operation (ticket stays in open/, archive not created)
- [x] Error message names the ticket repo, the offending paths, and gives a `git -C <root> add` + `git commit` recipe to commit them separately before re-running close_ticket.py
- [x] Mixed --files (some same-repo, some cross-repo) lists only the cross-repo paths as offenders
- [x] Existing workspace-ticket + workspace-project --files path still closes cleanly (regression)

## Resolution
Implemented Option B per SR-005 disposition. close_ticket.py now runs a pre-flight _check_cross_repo_files after --files validation: it resolves each --files path's git root and the ticket's git root, refusing (exit 1, before any destructive op) when any path lives in a different repo. Error message names ticket repo, offending paths (grouped by their out-of-repo root), and prints a concrete 'git -C <root> add ... && git -C <root> commit -m "docs(T###): ..."' recipe. 3 new tests in TestCloseTicketCrossRepoFiles (harness-rooted refusal, mixed-files lists only offenders, workspace-project-only still works). All 35 close_ticket tests pass.

Closed S22 2026-05-28.
