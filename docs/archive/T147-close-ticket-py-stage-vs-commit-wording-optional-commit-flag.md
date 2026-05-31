---
id: T147
title: close_ticket.py: stage-vs-commit wording + optional --commit flag
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S27 2026-05-31
closed: S27 2026-05-31
source: scrabble-score/SR-012
---

## Problem

Promoted from scrabble-score/SR-012.

## Context

Both `close_ticket.py` and harness `CLAUDE.md:132` give the impression that
`close_ticket.py --files ...` commits, when it only **stages**. The script prints
`Suggested commit: git commit -m "..."` and exits 0 with everything staged but
HEAD unmoved; `CLAUDE.md:132` reads "to stage code and test changes together with
the archive move in a single commit." In S14 this cost ~15 min: a clean
`CLOSE_EXIT=0` was misread as "committed," and the work sat staged until a manual
`git commit` was run. Not blocking (the work was recoverable), but the wording
will mislead a new workspace, a new operator, or a fresh model.

Surfaced: S14 / T027 (scrabble-score), Turn N board-title indicator — closed via
close_ticket.py (scrabble commit a65aaf1); the stage-vs-commit confusion was the
bulk of the session's close-out friction.

## Proposed change

1. Clarify `CLAUDE.md:132` wording: close_ticket *stages* the code/test changes
   together with the archive move; the operator then runs the printed
   `Suggested commit` line. (Apply the same correction to the workspace CLAUDE.md
   cross-repo section if it implies an automatic commit.)
2. Add an optional `--commit` flag to `close_ticket.py` that runs the suggested
   `git commit` after a successful stage. Backwards compatible: without `--commit`,
   behavior is unchanged (suggested-commit print only).
3. Derive the suggested-commit subject prefix from ticket type: `fix(T###):` when
   code files are present in `--files`, else `docs(T###):`.

## Acceptance Criteria

- [x] CLAUDE.md wording clarifies that close_ticket stages, then the operator runs the printed suggested commit
- [x] `close_ticket.py --commit` runs `git commit -m "<suggested>"` after a successful stage
- [x] Without `--commit`, behavior is unchanged (suggested-commit print only)
- [x] Suggested-commit subject prefix derives from ticket type (fix(T###): if code files present, else docs(T###):)
- [x] `--commit` refuses (exit 2) when staged files span multiple git roots, printing per-root suggested commits

## Resolution
Clarified CLAUDE.md wording (stage, not commit). Added --commit flag with multi-root safety guard (exit 2 when staged files span >1 git root). Commit prefix derives from --files content: fix(T###) with code files, docs(T###) otherwise.

Closed S27 2026-05-31.
