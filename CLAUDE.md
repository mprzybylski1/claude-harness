# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

---

## Commands

```bash
# TODO: fill in your run/test/build commands, for example:
# python main.py
# pytest tests/
# npm run dev
```

---

## Architecture

<!-- TODO: describe your system's key components, data flow, and trust boundaries.
     Be specific enough that Claude can make correct decisions without reading all source files.
     Example structure:

### Core components

- `src/core/` — safety-critical, fail-closed on all exceptions
- `src/api/` — HTTP layer, validates input before passing to core
- `tests/` — full test suite; run with `pytest tests/`

### Key constraints

- [Constraint 1: e.g. "No direct database writes from API layer — go through core/"]
- [Constraint 2: e.g. "Config values are read once at startup; runtime mutation not allowed"]
-->

---

## Key Constraints & Honest Limitations

### `isolation: "worktree"` does not prevent main-repo writes

Claude Code's `isolation: "worktree"` on the `Agent` tool creates a separate git
worktree, but isolation is at the **git level only** — it does not prevent agents
from reading or writing absolute paths outside the worktree directory. When agent
prompts contain absolute main-repo paths (e.g. ticket file paths, docs paths),
agents will operate directly on the main repo, not the worktree.

Observed S13: 3 of 5 parallel agents with `isolation: "worktree"` wrote to main-repo
paths, causing a ghost-tracked file and a stale INDEX.md committed to `master`.

**Do not use `isolation: "worktree"` for parallel harness-root work.**

**Recommended parallel strategy:** open N separate Claude Code sessions (terminal
tabs or IDE windows), each tackling one independent ticket, without worktree
isolation. Alternatively, run tickets sequentially within one session. Do not spawn
multiple `Agent` calls with `isolation: "worktree"` when their prompts contain
absolute main-repo paths.

---

## Phase Roadmap

<!-- TODO: optional — use if your project has discrete phases with gate criteria.
     Delete this section if you prefer a continuous backlog model.

**Phase 1 (Active):** [Goal and gate criteria]
**Phase 2 (Planned):** [Goal and gate criteria]
-->

---

## Configuration

<!-- TODO: describe key config files, dangerous settings, and environment variables.

`config.yaml` controls [what]. Changing [X setting] affects [Y behaviour].
-->

### Ticket archive directories

`docs/tickets/closed/` holds T001–T038 (legacy, before the S8 restructure). All tickets closed from T039 onward go to `docs/archive/` via `close_ticket.py`.

### Hook paths in `.claude/settings.json`

Hook commands locate the harness root via `$CLAUDE_PROJECT_DIR` and dispatch through
`scripts/hooks/run_hook.sh`:

```
bash -c 'H="$CLAUDE_PROJECT_DIR/scripts/hooks/run_hook.sh"; [ -f "$H" ] && exec bash "$H" <name> || exit 0'
```

**Do not use `$(git rev-parse --show-toplevel)` here.** That resolves against the
session cwd, which drifts when a Bash command does `cd` into another git repo (e.g. a
workspace repo). The old form caused SR-011/T138: a wedged cwd made `git rev-parse`
find a repo with no harness hooks → `python3: can't open file` → exit 2 → PreToolUse
fail-closed-blocked *every* tool (hard deadlock). `$CLAUDE_PROJECT_DIR` is set in every
hook process and stays **fixed for the session** — it does not drift with `cd`.
(The S3 2026-05-26 note that it was "empty in the hook subshell" is stale; verified
present and correct on Claude Code 2.1.158, T138.)

`run_hook.sh` re-derives the hooks dir from its own `$0` and **fails open** (exit 0)
when the named script is missing, so a resolution accident can never deadlock the
session. `exec` ensures a hook's deliberate `exit 2` (a real block) propagates to
Claude Code and is not masked by the trailing `|| exit 0`. See T138.

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
with the archive move in a single commit. Example:

```bash
python scripts/tools/close_ticket.py T099 \
  --resolution "Fixed the bug." \
  --files scripts/tools/myscript.py tests/test_myscript.py
```

Without `--files`, `close_ticket.py` warns about any unstaged code files it detects.

---

## Test-Driven Development

TDD is the default for any work touching safety-critical paths or invariant/trust-boundary
changes. Write the failing tests first, then implement.

Exempt: exploratory research, configuration wiring, UI/dashboard changes.
