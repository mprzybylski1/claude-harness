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

### Hook paths in `.claude/settings.json`

Hook commands use the **absolute** harness path
(`/Users/mprzybylski/PycharmProjects/claude-harness/...`) rather than
`$CLAUDE_PROJECT_DIR`. The env var was empty in the hook subshell on this Claude Code
build, so every hook (telemetry, ticket ACs, index regen, skill-bash check, session-log
check) silently failed with `python3: can't open file '/scripts/hooks/...'` — bash exits
non-zero before Python runs, and Claude Code discards the hook exit code, so nothing
surfaces in `.git/session_tool_log.errors`.

If the harness is ever cloned to a different path, update the five `command:` lines in
`.claude/settings.json` to match. Diagnosed S3 2026-05-26.

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
