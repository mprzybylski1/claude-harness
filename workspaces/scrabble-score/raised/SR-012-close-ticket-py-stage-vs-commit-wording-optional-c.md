---
id: SR-012
from: scrabble-score
raised: S14 2026-05-31
title: "close_ticket.py: stage-vs-commit wording + optional --commit flag"
severity: medium
status: raised
harness_ticket:
resolved_in:
---

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

Acceptance criteria:
- [ ] CLAUDE.md:132 wording clarifies that close_ticket stages, then the operator runs the printed suggested commit
- [ ] `close_ticket.py --commit` runs `git commit -m "<suggested>"` after a successful stage
- [ ] Without `--commit`, behavior is unchanged (suggested-commit print only)
- [ ] Suggested-commit subject prefix derives from ticket type (fix(T###): if code files present, else docs(T###):)

## Harness disposition

(Filled by harness on promotion or rejection.)
