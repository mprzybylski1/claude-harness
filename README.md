# Claude Harness

A project-agnostic session management system for Claude Code. Structured sessions,
automated Opus post-session reviews, a ticket system, and hooks that enforce commit
discipline and invariant checks.

## What's included

- **Session lifecycle skills** (`/session-start`, `/session-close`) — structured briefing,
  Opus review loop, session log, ticket aging alerts
- **Background implementation** (`/implement-background`, `/check-workflow`) — run ticket
  implementation as a background agent; main thread stays free
- **Ticket system** — frontmatter-driven Markdown tickets with severity triage, aging
  detection, and an auto-generated INDEX
- **Static analysis hooks** — configurable per-project checks run at every session close
- **Harness configuration** — single `harness.yaml` file adapts the harness to your project

---

## New project workflow

On GitHub, click **"Use this template"** → create your repo. Then:

```bash
git clone https://github.com/you/your-new-project
cd your-new-project

# 1. Edit harness.yaml — set code_paths and static_analysis_checks for your project layout
# 2. Fill in CLAUDE.md placeholder sections (Commands, Architecture, Configuration)
# 3. Fill in docs/architecture_invariants.md with your project's hard constraints
# 4. Open Claude Code, run /session-start — Claude bootstraps S001
```

---

## Graft workflow (adding to an existing project)

```bash
# Clone the harness into a temp directory
git clone https://github.com/mprzybylski/claude-harness /tmp/claude-harness

cd your-existing-project

# Copy harness infrastructure
cp -r /tmp/claude-harness/.claude/skills        .claude/
cp -r /tmp/claude-harness/scripts/tools         scripts/
cp -r /tmp/claude-harness/scripts/hooks         scripts/
cp -r /tmp/claude-harness/scripts/workflows     scripts/
mkdir -p docs/tickets/{open,closed} docs/archive

# Copy doc templates (only the ones you don't already have)
cp /tmp/claude-harness/docs/tickets/TEMPLATE.md   docs/tickets/
cp /tmp/claude-harness/docs/tickets/INDEX.md       docs/tickets/
cp /tmp/claude-harness/docs/sessions.md            docs/
cp /tmp/claude-harness/docs/opus_notes.md          docs/
cp /tmp/claude-harness/docs/system_state.md        docs/

# Copy config files
cp /tmp/claude-harness/harness.yaml               ./
cp /tmp/claude-harness/.claude/settings.json      .claude/  # merge if you have existing hooks
cp /tmp/claude-harness/CLAUDE.md                  ./        # then customise

# Install the commit-msg hook
echo '#!/bin/sh\npython3 scripts/hooks/commit_msg_check.py "$1"' > .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg

# 2. Configure harness.yaml — set code_paths, tickets_dir, static_analysis_checks
# 3. Fill in CLAUDE.md placeholder sections
# 4. Fill in docs/architecture_invariants.md
# 5. Open Claude Code, run /session-start — Claude bootstraps S001
```

Existing code is context. The first Opus review treats the codebase as-is; no prior history
is inferred.

---

## Configuration — harness.yaml

All keys are optional. Scripts fall back to built-in defaults when `harness.yaml` is absent
or a key is missing.

```yaml
# Prefix for session-close commit messages (default: "docs: S")
session_close_prefix: "docs: S"

# Paths that classify a session as code-touching → full Opus review
code_paths:
  - "src/"
  - "tests/"

# Relative path to open tickets directory (default: "docs/tickets/open")
tickets_dir: "docs/tickets/open"

# Static analysis checks to run at session close
# Available: test_syntax, utcnow, eval_exec, sql_mutations,
#            exception_swallowing, bash_blocks, spec_status_enum
static_analysis_checks:
  - test_syntax
  - eval_exec
  - exception_swallowing
  - bash_blocks
```

---

## Session workflow

```
/session-start        → briefing: phase status, invariant violations, aging tickets
[do work]
/implementation-review   → mid-session Opus review (optional, code sessions)
/implement-background    → delegate ticket implementation to background agent (optional)
/session-close        → update sessions.md, rotate opus_notes.md, Opus review, commit
```

The session log in `docs/sessions.md` is the authoritative record. `docs/opus_notes.md`
holds the two most recent Opus reviews; older ones are archived to `docs/archive/`.

---

## Hooks

Four hooks run automatically via `.claude/settings.json`:

| Event | Hook | What it does |
|-------|------|--------------|
| PreToolUse (Edit/Write/Bash) | `check_ticket_acs.py` | Blocks moving a ticket to `closed/` if any `- [ ]` AC remains |
| PostToolUse (Edit/Write) | `regenerate_ticket_index.py` | Keeps `INDEX.md` current after any ticket write |
| PostToolUse (Edit/Write) | `check_skill_bash_blocks_hook.py` | Validates bash block syntax in SKILL.md files |
| Stop | `check_session_log.py` | Blocks session end if closed tickets lack correct `closed:` attribution |

The `commit-msg` hook (`scripts/hooks/commit_msg_check.py`) validates commit message format.
Install it manually: `echo '#!/bin/sh\npython3 scripts/hooks/commit_msg_check.py "$1"' > .git/hooks/commit-msg && chmod +x .git/hooks/commit-msg`

---

## Ticket format

Tickets live in `docs/tickets/open/` (filename: `T###-kebab-title.md`) and move to
`docs/tickets/closed/` when resolved. See `docs/tickets/TEMPLATE.md` for the full schema.

Required frontmatter fields: `id`, `title`, `severity` (critical/high/medium/low), `status`,
`opened` (format: `S### YYYY-MM-DD`).

---

## Requirements

- Python 3.10+
- `pip install pyyaml` (used by `harness_config.py` and `update_system_state.py`)
- Claude Code (CLI or IDE extension)
- Git

---

## License

MIT
