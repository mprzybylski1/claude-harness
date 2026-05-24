---
name: check-workflow
description: Read .git/workflow_result.json and surface the current workflow outcome after /implement-background.
---

# /check-workflow

Reads `.git/workflow_result.json` and reports the outcome from the most recent
`/implement-background` run.

## Steps

1. Read `.git/workflow_result.json`.

2. Report: outcome, timestamp, details, and diff preview (first 2000 chars).

3. Act based on outcome:

   **AWAITING_REVIEW**
   > Implementation complete, tests pass. Diff is ready for review.
   > Offer: "Shall I run `/review-and-commit` to stage and commit the diff?"

   **AWAITING_ARCHITECTURE_REVIEW**
   > Safety-critical files were modified. Must run `/architecture-review` on the diff FIRST.
   > Do NOT offer `/review-and-commit` until architecture review explicitly approves.
   > Run: `/architecture-review` passing the diff_preview as the input.

   **KILLED_DENYLIST_VIOLATION**
   > Agent was killed mid-run for touching a denied path. Working tree is clean.
   > Show which path was violated. User decides whether to retry or implement manually.

   **UNAUTHORIZED_COMMIT**
   > Agent made commits without authorization — reverted to snapshot. Working tree clean.

   **ORCHESTRATOR_MODIFIED**
   > Agent modified orchestrator scripts — reverted. Indicates a misbehaving agent.

   **TEST_FAILED**
   > Tests failed after implementation — reverted. Show test output from details field.

   **ANALYSIS_FAILED**
   > Static analysis failed — reverted. Show analysis output from details field.

   **WATCHER_CRASHED**
   > Monitoring thread died — agent was terminated as a precaution. Working tree clean.
   > Retry or investigate why git status polling failed.

   **TIMEOUT**
   > Agent exceeded the 30-minute budget — terminated and reverted. Working tree clean.

   **CREDIT_EXHAUSTED**
   > Metered credit pool exhausted. Set `ANTHROPIC_API_KEY` to switch to API billing,
   > or wait for next billing cycle. Working tree unchanged.

   **AGENT_UNAVAILABLE**
   > CLI binary failed to start. Check `CLAUDE_CLI_PATH` and subscription status.

   **ALREADY_RUNNING**
   > Another workflow is already running. Wait for it to complete or check for stale lock:
   > `rm .git/workflow.lock`

   **TICKET_NOT_FOUND**
   > No open ticket file matching T### found in `docs/tickets/open/`.

4. If file does not exist:
   > "No workflow result found — run `/implement-background T###` first."

## Audit log

The full audit trail is at `.git/workflow_audit.log` — append-only, one line per state
transition. Read it for debugging failed runs.
