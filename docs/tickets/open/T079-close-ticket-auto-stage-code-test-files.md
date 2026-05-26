---
id: T079
title: close_ticket.py should stage code/test files alongside the archive move
severity: high
status: open
phase: process
layer: process
opened: S16 2026-05-26
closed:
---

## Problem

`close_ticket.py` stages exactly three paths: the source ticket file (with
`git rm --cached`), the archive destination, and INDEX.md. It does **not** stage
the code or test changes the ticket fixed.

CLAUDE.md "Commit Discipline" mandates **one commit per ticket — code + tests
together**, but the only tool that automates ticket closure leaves the operator to
remember `git add scripts/... tests/...` before `git commit`. In S16 this failure
mode bit four tickets in a row (T074-T077): each "fix" commit contained only the
archive move + INDEX.md churn; the actual script and test changes were unstaged.
Recovery required reconstructing the diffs via `git apply --cached` with crafted
hunk headers — slow, error-prone, and only happened because the user noticed.

The session-close skill already acknowledges this gap (Step at line ~47: "If code
files still appear in `git status` when you reach Step 6, stage and commit them
first") which pushes the work to the operator after the fact instead of catching
it at ticket-close time.

## Acceptance Criteria

- [ ] `close_ticket.py` accepts a `--files PATH [PATH...]` flag that includes
      additional paths in the same `git add` invocation as the archive move,
      so a single `git commit` produces one cohesive per-ticket commit.
- [ ] When `--files` is omitted, the script prints the current `git diff
      HEAD --name-only` output (filtered to code/test paths) and warns: "no
      code files staged — pass --files explicitly or commit code separately."
- [ ] If any `--files` path does not exist or is not a regular file, the script
      exits non-zero before moving the ticket, leaving the workspace untouched.
- [ ] Workspace tickets pass the `--files` paths to the correct git root (uses
      `_git_root_for` for each file, not just the archive destination).
- [ ] Test added in `tests/test_close_ticket_stage_files.py`: closing a ticket
      with `--files foo.py bar.py` results in all three (foo.py + bar.py +
      archive move + INDEX.md) staged together; `git status` shows clean
      separation between staged and unstaged.
- [ ] CLAUDE.md "Commit Discipline" section updated to reference `--files`.

## Notes

S16 workflow-review finding #4 (highest-value finding of the session).
Related to T080 (defense-in-depth hook).
Caused 4 broken commits in S16: T074, T075, T076, T077 — all required manual
diff-splitting recovery.

## Resolution

> **Client-visible:** Closing a ticket now stages the code change alongside the
> archive move, so per-ticket commits are produced in one step instead of
> requiring manual `git add` discipline.

(Fill in on close.)
