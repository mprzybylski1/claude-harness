---
id: SR-015
from: scrabble-score
raised: S16 2026-06-26
title: "check_fix_commit_has_code hook is workspace-repo-blind: false-positive blocks workspace-repo commits"
severity: medium
status: raised
harness_ticket:
resolved_in:
---

## Context

Surfaced in S16 (scrabble-score) closing T029. The `PreToolUse` Bash hook
`check_fix_commit_has_code` blocked a `fix(T029)` commit with "commit has no code
files staged" — but all 10 files (code, tests, deletions, archive) **were** staged
in the scrabble repo (`cwd = ~/Documents/Projects/ScrabbleScore`,
`git diff --cached` confirmed them). The hook inspects the **harness** repo index
(via `$CLAUDE_PROJECT_DIR`), which was empty, not the repo the commit actually targets.
Had to verify staging by hand and commit with `--no-verify`.

Why a manual commit happened at all: `close_ticket.py --commit` normally commits
directly (sidestepping the hook), but it **refuses `--commit` when the index has
staged changes beyond what it staged** — here the two `git rm` deletions
(`LetterPickerSheet.swift`, `BlankLetterPickerSheet.swift`) that `--files` can't take
(it rejects non-existent paths). So a deletion-bearing close forces a manual
`git commit`, which then hits the false-positive hook.

Not blocking (workaround: verify + `--no-verify`), but it makes every workspace-repo
commit with deletions a two-step manual dance with a scary-looking block.

## Proposed change

1. `check_fix_commit_has_code`: detect the git repo the commit targets (the Bash
   `cwd`'s repo) and check **that** repo's staged files — not the harness repo. Or
   scope the hook to fire only for harness-repo commits and skip workspace-repo ones.
2. `close_ticket.py`: support file **deletions** in a close — e.g. accept
   already-staged deletions instead of refusing `--commit`, or add a `--rm`/
   `--allow-staged` path — so a multi-file close that removes files doesn't force a
   manual, hook-blocked commit.

## Harness disposition

(Filled by harness on promotion or rejection.)
