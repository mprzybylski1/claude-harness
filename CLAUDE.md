# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

---

## Commands

```bash
pytest tests/
```

---

## Key Constraints & Honest Limitations

### `isolation: "worktree"` does not prevent main-repo writes

**Do not use `isolation: "worktree"` for parallel harness-root work.** Worktree
isolation is git-level only — agents with absolute paths write to the main repo.
Use separate Claude Code sessions or run tickets sequentially. (See T038 for details.)

---

## Configuration

### Ticket archive directories

`docs/tickets/closed/` holds T001–T038 (legacy, before the S8 restructure). All tickets closed from T039 onward go to `docs/archive/` via `close_ticket.py`.

### Hook paths in `.claude/settings.json`

Hooks use `$CLAUDE_PROJECT_DIR` (not `git rev-parse`) to locate `scripts/hooks/run_hook.sh`.
**Do not change this to `$(git rev-parse --show-toplevel)`** — cwd drift causes deadlocks (T138).
`run_hook.sh` fails open when a script is missing; `exec` propagates deliberate exit 2 blocks.

---

## Session Start Protocol

At session start, invoke `/session-start`. See `.claude/skills/session-start/SKILL.md` for
the full protocol.

---

## Working Style

- Push back, ask questions, play devil's advocate, point out things that might be missing — be
  part of the decision-making process, not a rubber stamp.
- Don't smooth the edges. When something is wrong, say so directly — not "have you considered"
  but "no, that's wrong, here's why."
- Give genuine opinions. If something looks off, say it. If a direction is wrong, explain why.
  Don't give neutral observations when a real view is warranted.

---

## Commit Discipline

Commit after each ticket closes — one commit per ticket, before moving to the next.
Session-close commits `docs/` only. This keeps diffs reviewable by Opus and `git bisect` useful.
See `.claude/skills/session-close/SKILL.md` "Commit discipline" section.

Use `close_ticket.py --files <path> [<path>...]` to stage code and test changes together
with the archive move. The script stages everything and prints a suggested `git commit`
command; run it yourself, or pass `--commit` to have the script commit for you. Example:

```bash
python scripts/tools/close_ticket.py T099 \
  --resolution "Fixed the bug." \
  --files scripts/tools/myscript.py tests/test_myscript.py \
  --commit
```

Without `--files`, `close_ticket.py` warns about any unstaged code files it detects.

---

## Test-Driven Development

TDD is the default for any work touching safety-critical paths or invariant/trust-boundary
changes. Write the failing tests first, then implement.

Exempt: exploratory research, configuration wiring, UI/dashboard changes.
