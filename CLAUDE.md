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

<!-- TODO: what does this system NOT do well? What are the real risks?
     Being honest here saves future debugging time.

- [Limitation 1]
- [Limitation 2]
-->

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

Hook commands use `$(git rev-parse --show-toplevel)` to locate the harness root at
runtime, making the config portable across machines:

```
bash -c 'python3 "$(git rev-parse --show-toplevel)/scripts/hooks/<name>.py"'
```

`$CLAUDE_PROJECT_DIR` was empty in the hook subshell (diagnosed S3 2026-05-26), so we
avoid it. The `$(...)` is inside single quotes, which prevents the outer shell from
expanding it; `bash -c` then runs the string in a fresh shell where the substitution
is evaluated correctly.

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

---

## Test-Driven Development

TDD is the default for any work touching safety-critical paths or invariant/trust-boundary
changes. Write the failing tests first, then implement.

Exempt: exploratory research, configuration wiring, UI/dashboard changes.
