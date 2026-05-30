---
id: SR-011
from: scrabble-score
raised: S13 2026-05-30
title: Hooks fail-closed and block ALL Edit/Write/Bash when session cwd moves into a workspace repo
severity: high
status: resolved
harness_ticket: T138
resolved_in: S25
---

## Context

Surfaced in S13 (scrabble-score). Every hook in `.claude/settings.json` locates its
script via `bash -c 'python3 "$(git rev-parse --show-toplevel)/scripts/hooks/<name>.py"'`,
evaluated at the **session's current working directory**. When a Bash command does
`cd <workspace-repo>/… && <cmd>` and the cwd does **not** auto-reset (observed after a
`cd …/ScrabbleScore/.harness/tickets/open && mv …`), the session cwd stays inside the
workspace repo. From there `git rev-parse --show-toplevel` resolves to the *workspace*
repo (`/Users/…/ScrabbleScore`), where the harness hook scripts do not exist →
`python3: can't open file …` → non-zero exit.

For **PreToolUse** hooks (`check_ticket_acs` on Edit|Write|Bash, `check_cross_layer_writes`
on Edit|Write, `check_fix_commit_has_code` on Bash) a non-zero exit **fail-closed-blocks
the tool**. Net effect: once the cwd is wedged into a workspace repo, *every* Edit, Write,
and Bash is blocked — including the `cd` that would un-wedge it. Read survives (PostToolUse
only, non-blocking). **Hard deadlock**; recovered only by the operator typing
`!cd <harness root>` (the `!` shell bypasses tool hooks). Blocked ~mid-session for several
turns. **Blocking: yes** (recoverable only with operator help).

This is the same root cause the S3 CLAUDE.md note worked around for `$CLAUDE_PROJECT_DIR`,
and a sibling of the SR-008/009/010 workspace-blind-tooling family: harness tooling assumes
cwd == harness root.

Secondary, lower-severity: `raise_for_harness.py` stamped this SR `raised: S14` when the
raising session is **S13** — it computed "current" as last-logged+1, and the S13 session-log
line had already been appended during close. SR/session stamping should resolve to the
session that is *running*, not the next one. (Fixed by hand here.)

## Proposed change

Make hook root-resolution independent of cwd. Options (harness picks):
1. Resolve the harness root once at hook-install/settings level and pass it via env
   (e.g. a wrapper that records the harness root), rather than `git rev-parse` at run time.
2. Have each hook walk up from its own script path (`$0`/`__file__`) to find the harness
   root, instead of trusting cwd's git toplevel.
3. At minimum, make PreToolUse hooks **fail-open** (warn, exit 0) when their own script
   path can't be resolved, so a cwd accident can't hard-deadlock the session.
Also: `raise_for_harness.py` (and any session-stamping helper) should stamp the *running*
session, not last-logged+1.

## Harness disposition

Promoted → T138 (S25 2026-05-30); fixed same session.

Primary deadlock fixed: hook commands no longer use `$(git rev-parse --show-toplevel)`.
They resolve the harness root via `$CLAUDE_PROJECT_DIR` (set in every hook process,
fixed for the session — verified present on Claude Code 2.1.158, contradicting the
stale S3 note) and dispatch through `scripts/hooks/run_hook.sh`, which fails open
(exit 0) if a script can't be found. A cwd accident can no longer hard-deadlock the
session. Goes live next session start (hook config is snapshotted at start).

Secondary (session-stamping last-logged+1, the S13→S14 mis-stamp) → split to T139.
