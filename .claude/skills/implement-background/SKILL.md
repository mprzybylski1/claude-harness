---
name: implement-background
description: Run the Python orchestrator to implement a ticket in the background. Main thread stays free.
---

# /implement-background

Usage: `/implement-background T###`

Runs the Python state machine in the background. The main session stays interactive while the
agent works. When notified, run `/check-workflow` to see the outcome and diff.

## What happens

The orchestrator (`scripts/workflows/implement_ticket.py`) does everything:

1. Takes a git snapshot (HEAD SHA)
2. Reads the ticket from `docs/tickets/open/T###-*.md`
3. Spawns `claude -p <prompt>` as a subprocess
4. Monitors the working tree every 0.5s — kills the agent if denied paths are touched
5. After agent exits: checks for unauthorized commits, hash-guards orchestrator scripts,
   runs tests, runs static analysis
6. Routes to AWAITING_REVIEW or AWAITING_ARCHITECTURE_REVIEW if clean
7. On any failure: reverts to snapshot, writes result, cleans working tree

Working tree is ALWAYS clean on any non-AWAITING_* exit. Human approval required before commit.

## Precondition — working tree must be clean

**Run only when `git status` shows nothing uncommitted.**

The orchestrator uses `git reset --hard` + `git clean -fd` on any failure path — this
destroys uncommitted operator work. If the tree is dirty the workflow refuses to start
and returns `DIRTY_WORKING_TREE`. Commit or stash first.

## Steps

1. Run the orchestrator in the background:
   ```bash
   python -m scripts.workflows.implement_ticket T###
   ```
   Use the **Bash tool** with `run_in_background: true`.

2. Continue the conversation normally while the agent works.

3. When the background notification arrives, run `/check-workflow` to see the outcome.

## Denied paths (agent is killed immediately if touched)

- `scripts/workflows/` — never modify the orchestrator itself
- `docs/architecture_invariants.md` — immutable governance
- `config.yaml` — production config
- `infra/audit_log.py` — append-only audit log

## Safety-critical paths (routes to AWAITING_ARCHITECTURE_REVIEW)

- `core/`, `execution/`, `strategies/runtime.py`, `strategies/specs/`, `infra/audit_log.py`

## Fallback if credit exhausted

Set `ANTHROPIC_API_KEY` in the shell environment — the CLI will use API billing instead
of the subscription metered pool. No other change needed.

## Fallback if binary unavailable

Set `CLAUDE_CLI_PATH` to an alternative binary path. The orchestrator wraps any binary
with the same watcher / hash-guard / revert logic.
