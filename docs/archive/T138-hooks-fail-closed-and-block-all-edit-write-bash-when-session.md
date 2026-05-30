---
id: T138
title: Hooks fail-closed and block ALL Edit/Write/Bash when session cwd moves into a workspace repo
severity: high
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S25 2026-05-30
closed: S25 2026-05-30
source: scrabble-score/SR-011
---

## Problem

Promoted from scrabble-score/SR-011.

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
## Acceptance Criteria

- [x] Resolve the harness root once at hook-install/settings level and pass it via env — each settings.json command resolves the wrapper via `$CLAUDE_PROJECT_DIR`, which Claude Code sets in every hook process and keeps fixed for the session (drift-proof; verified empirically on 2.1.158 — the S3 CLAUDE.md "empty in hook subshell" note is stale).
- [x] Have each hook walk up from its own script path (`$0`/`__file__`) to find the harness — `run_hook.sh` re-derives the hooks dir from its own `$0`; the python hooks already self-resolve via `Path(__file__).resolve().parents[2]`, so the script path never depends on cwd or `git rev-parse`.
- [x] At minimum, make PreToolUse hooks **fail-open** (warn, exit 0) when their own script path can't be resolved — settings.json `[ -f "$H" ] && exec ... || exit 0` and `run_hook.sh`'s `[ -f "$script" ] || exit 0` both exit 0 when unresolvable; a hook's deliberate `exit 2` still propagates through the `exec` chain.

Secondary stamping bug (raise_for_harness last-logged+1) — DEFERRED to T139.

## Resolution
Replaced the cwd-dependent `bash -c 'python3 "$(git rev-parse --show-toplevel)/scripts/hooks/X.py"'`
hook commands with `$CLAUDE_PROJECT_DIR`-based dispatch through a new
`scripts/hooks/run_hook.sh` wrapper.

Root cause: `git rev-parse --show-toplevel` resolved against the *session cwd*. When
cwd drifted into a workspace repo, it found a repo with no harness hooks →
`python3: can't open file` → exit 2 → PreToolUse fail-closed-blocked every
Edit/Write/Bash, including the `cd` needed to recover. Hard deadlock.

Fix (two layers):
1. cwd-independent resolution. `$CLAUDE_PROJECT_DIR` (set in hook context, fixed for
   the session — confirmed by an empirical probe of `log_tool_usage` this session)
   locates `run_hook.sh`, which re-derives the hooks dir from its own `$0`. No
   `git rev-parse`, no cwd dependence. The git fallback was deliberately dropped: with
   `CLAUDE_PROJECT_DIR` reliable, a fallback only fires when it is unset — exactly the
   drift case where `git rev-parse` would resolve to the *wrong* repo and risk running
   a same-named foreign script.
2. Fail-open safety net. If the wrapper or hook script can't be found, the command
   exits 0 rather than erroring. `exec` ensures a hook's legitimate `exit 2` is
   returned directly to Claude Code and is not masked by the trailing `|| exit 0`.

Files: `.claude/settings.json` (7 hook commands), `scripts/hooks/run_hook.sh` (new),
`tests/test_hook_command_resolution.py` (new — 10 tests), plus the CLAUDE.md note.

NOTE: hook config is snapshotted at session start; this fix goes live next session.
Verification this session is via subprocess against the actual command strings
(deliberately drifting cwd would run the old command and reproduce the deadlock).
467 tests pass (incl. 83 existing hook tests); 13 pre-existing test_workflow_orchestrator
ImportError failures are unrelated.

Secondary stamping bug (raise_for_harness last-logged+1) → DEFERRED to T139.
Out of scope, on record: check_fix_commit_has_code runs `git diff --cached` against the
hook's cwd, so fixing script location doesn't fix script-internal cwd assumptions.

Closed S25 2026-05-30.
