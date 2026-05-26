---
id: T078
title: Background Opus agent denied filesystem access to workspace repo
severity: medium
status: closed
phase: 2
layer: process
opened: S16 2026-05-26
closed: S17 2026-05-26
---

## Problem

Spawning the post-session Opus review agent with `run_in_background: true` fails for
workspace sessions: the agent reports `Read` and `Bash` denied for the workspace repo
path (e.g. `/Users/mprzybylski/Documents/Projects/ScrabbleScore/`). A foreground retry
with the same prompt and paths succeeds.

**Hypothesis:** Background agents inherit a more restrictive permission set than the main
session. The workspace repo path is not in the implicit allow-list (only the harness repo
path is covered).

**Impact:** Forces synchronous (foreground) Opus review on every workspace session-close,
doubling session-close latency.

**Fix options (choose one):**
1. Add the workspace repo to the background-agent permission allow-list, reading the path
   from `workspace.yaml` at session-close time.
2. Change `session-close` SKILL to use foreground review for workspace sessions as a
   short-term workaround, with a comment pointing at this ticket.

Option 1 is the correct fix; option 2 is an acceptable interim if option 1 is complex.

## Acceptance Criteria

- [ ] Post-session Opus review agent with `run_in_background: true` can read files in the
  workspace repo path declared in `workspace.yaml`.
- [x] OR: `session-close` SKILL is updated to use foreground review for workspace sessions
  with a `# TODO T078` comment, and this ticket is updated to reflect the workaround.

## Notes

See `docs/workflow_review_S4_findings.md` finding #5. This is the second-highest-value
fix (finding #2 / T075 is highest) because it doubles session-close latency every
workspace session.

## Resolution

Implemented option 2 (acceptable interim): updated session-close SKILL.md to use foreground Opus review for workspace sessions. Removed run_in_background: true from the workspace Opus agent spawn instruction and added a HTML comment block (TODO T078) documenting the root cause — background agents inherit a more restrictive permission set and cannot access workspace repo paths outside the harness. Harness-root sessions are unaffected and may still use background. Option 1 (programmatic permission allow-list) deferred: the Agent tool has no permissions parameter to set at spawn time.

Closed S17 2026-05-26.
