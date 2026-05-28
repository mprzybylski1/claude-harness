# Claude Harness

**A disciplined engineering workflow layered on top of [Claude Code](https://claude.com/claude-code).**
Structured sessions, a ticket system, invariant-enforcing git/agent hooks, and an automated
multi-agent review loop — built to catch the failure modes that show up when an AI agent
writes production code.

`Python 3.10+` · `MIT` · `~8.3k LOC + ~9.3k LOC of tests` · self-hosting

---

## Why it exists

AI coding agents are fast and *undisciplined*. Across a multi-session project they introduce a
class of failure that ordinary CI, linting, and human review don't reliably catch:

- **Invariant drift** — a constraint that held last week silently breaks this week.
- **Acceptance-criteria rot** — tickets close with boxes still unchecked.
- **Half-implemented features** — the happy path works; the edges were never written.
- **Untracked decisions** — *why* something was built a certain way evaporates between sessions.

Claude Harness adds the layer *above* your existing tooling. It gives an AI-assisted project the
memory, enforcement, and audit trail of a disciplined engineering org: sessions that brief and
close, tickets with enforced acceptance criteria, hooks that block bad state at the trust
boundary, and a post-session review loop that re-reads the diff with a stronger model.

---

## What it does

| Capability | How |
|---|---|
| **Session lifecycle** | `/session-start` briefs you (phase status, invariant violations, aging tickets); `/session-close` updates the log, runs a model review, and commits — every session has a clean open and close. |
| **Ticket system** | Frontmatter-driven Markdown tickets with severity triage, aging detection, an auto-regenerated index, and acceptance-criteria gating enforced by a hook. |
| **Enforcement hooks** | git + Claude Code hooks that *block* invalid state: closing a ticket with unmet ACs, fix-commits with no code, cross-layer writes, malformed commit messages. |
| **Multi-agent review loop** | Mid- and post-session reviews delegate the diff to a stronger model; findings are captured, rotated, and archived. |
| **Background implementation** | `/implement-background` runs ticket implementation as a background agent so the main thread stays free. |
| **One-file configuration** | A single `harness.yaml` adapts paths, checks, and behavior to any project; every key has a built-in default. |

---

## What this project demonstrates

Built as a personal system and used to manage its own development; included here as a worked
example of engineering judgment around autonomous agents.

- **Enforcement at the right layer.** Trust-boundary thinking: discipline is enforced by *hooks*
  (git `commit-msg`, Claude `PreToolUse` / `PostToolUse` / `Stop`) that block bad state
  mechanically — not by convention or hope.
- **Multi-agent orchestration.** A main working agent plus delegated review and
  background-implementation agents, with structured hand-off and result capture.
- **Test discipline on safety-critical paths.** ~30 test modules / ~9,300 lines of tests against
  ~8,300 lines of implementation — a >1:1 test-to-code ratio, with TDD mandated for any change
  touching an invariant or trust boundary.
- **It's self-hosting.** The harness manages its own development — 130+ tickets specced,
  implemented in tracked sessions, and reviewed by its own loop before merge. The git history
  *is* the worked example.

---

## Design decisions & hard-won lessons

A few of the non-obvious calls, kept honest — including the ones that bit:

- **`isolation: "worktree"` does not prevent main-repo writes.** Claude Code's worktree isolation
  is git-level only; an agent handed absolute main-repo paths in its prompt will happily write
  outside the worktree. Found the hard way when 3 of 5 parallel agents wrote to main-repo paths,
  leaving a ghost-tracked file and a stale `INDEX.md` committed to `master`. The harness now
  documents this as a hard constraint and avoids worktree isolation for parallel root work.
- **Hook paths resolve via `$(git rev-parse --show-toplevel)`, not `$CLAUDE_PROJECT_DIR`.** The
  latter was empty in the hook subshell; the former is wrapped in single quotes so the outer
  shell doesn't expand it, and `bash -c` evaluates it in a fresh shell. Keeps the hook config
  portable across machines.
- **One commit per ticket; session-close commits docs only.** Keeps diffs reviewable by the
  review model and `git bisect` useful — discipline that falls out of the constraint that a
  stronger model reads every diff.

> Honest limitations live in [`CLAUDE.md`](CLAUDE.md), not buried.

---

## Architecture

```
.claude/skills/      session + workflow skills (session-start, session-close, …)
scripts/hooks/       8 hook scripts (enforcement + telemetry + index regen)
scripts/tools/       ~33 CLI tools (ticketing, session lookup, static analysis, …)
scripts/workflows/   background-implementation orchestrator + libs
docs/tickets/        open / closed tickets + auto-generated INDEX
docs/                sessions.md, opus_notes.md, system_state.md, architecture_invariants.md
harness.yaml         single configuration file
```

---

## Getting started

Use it on a **new** project (GitHub *"Use this template"*), or **graft** it onto an existing repo.

```bash
# New project
git clone https://github.com/<you>/<your-project> && cd <your-project>
# 1. Edit harness.yaml — set code_paths + static_analysis_checks for your layout
# 2. Fill in CLAUDE.md (Commands, Architecture, Configuration)
# 3. Fill in docs/architecture_invariants.md with your project's hard constraints
# 4. Open Claude Code → run /session-start
```

<details>
<summary><b>Graft onto an existing project</b></summary>

```bash
git clone https://github.com/mprzybylski1/claude-harness /tmp/claude-harness
cd your-existing-project

cp -r /tmp/claude-harness/.claude/skills    .claude/
cp -r /tmp/claude-harness/scripts/tools      scripts/
cp -r /tmp/claude-harness/scripts/hooks      scripts/
cp -r /tmp/claude-harness/scripts/workflows  scripts/
mkdir -p docs/tickets/{open,closed} docs/archive

# Doc templates (only the ones you don't already have)
cp /tmp/claude-harness/docs/tickets/TEMPLATE.md docs/tickets/
cp /tmp/claude-harness/docs/tickets/INDEX.md    docs/tickets/
cp /tmp/claude-harness/docs/{sessions,opus_notes,system_state}.md docs/

# Config
cp /tmp/claude-harness/harness.yaml          ./
cp /tmp/claude-harness/.claude/settings.json .claude/   # merge if you have existing hooks
cp /tmp/claude-harness/CLAUDE.md             ./          # then customise

# commit-msg hook
printf '#!/bin/sh\npython3 scripts/hooks/commit_msg_check.py "$1"\n' > .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

Then configure `harness.yaml`, fill in `CLAUDE.md` and `docs/architecture_invariants.md`, and run
`/session-start`. Existing code is treated as-is — the first review reads the codebase as it stands.

</details>

---

## Configuration — `harness.yaml`

All keys are optional; scripts fall back to built-in defaults when a key is absent.

```yaml
session_close_prefix: "docs: S"     # prefix for session-close commit messages
code_paths:                         # paths that mark a session as code-touching → full review
  - "scripts/"
  - "tests/"
tickets_dir: "docs/tickets/open"
static_analysis_checks:             # run at session close
  - test_syntax
  - utcnow
  - bash_blocks
workflow_telemetry: true            # log tool calls to .git/session_tool_log.jsonl
```

---

## Hooks

| Event | Hook | Blocks / does |
|---|---|---|
| PreToolUse (Edit/Write/Bash) | `check_ticket_acs.py` | Moving a ticket to `closed/` while any `- [ ]` AC remains |
| PostToolUse (Edit/Write) | `regenerate_ticket_index.py` | Keeps `INDEX.md` current after any ticket write |
| PostToolUse (Edit/Write) | `check_skill_bash_blocks_hook.py` | Validates bash-block syntax in `SKILL.md` files |
| Stop | `check_session_log.py` | Ending a session when closed tickets lack `closed:` attribution |
| commit-msg | `commit_msg_check.py` | Enforces commit-message format |

The repo also ships cross-layer-write and fix-commit-has-code guards plus a tool-usage telemetry
hook (`scripts/hooks/`).

---

## Requirements

- Python 3.10+ · `pip install pyyaml`
- Claude Code (CLI or IDE extension) · Git

---

## License

MIT — see [LICENSE](LICENSE).