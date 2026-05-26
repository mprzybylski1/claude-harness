---
id: T080
title: Pre-commit hook blocks fix(TXXX) commits with no code files staged
severity: medium
status: closed
phase: process
layer: process
opened: S16 2026-05-26
closed: S17 2026-05-26
---

## Problem

Even with [[T079]] landed, an operator can still bypass `close_ticket.py --files`
by running `git commit -m "fix(T999): ..."` directly with only `docs/archive/`
moves staged. The result is an empty fix commit that breaks `git bisect`,
hides the actual code change in an unrelated later commit, and violates the
"one commit per ticket" rule.

This is the exact failure mode that bit S16 four times. Adding a defensive
PreToolUse hook on `Bash(git commit *)` provides defense-in-depth without
requiring operators to remember [[T079]]'s flag.

## Acceptance Criteria

- [x] New hook `scripts/hooks/check_fix_commit_has_code.py` parses the `-m`
      message for `^fix\(T\d+\):` prefix.
- [x] When the prefix matches, the hook runs `git diff --cached --name-only`
      and checks for at least one path matching the code prefixes
      (`scripts/`, `tests/`, `src/`, `lib/`, or whatever `harness.yaml`
      `code_paths` declares).
- [x] If zero code files are staged, hook exits non-zero with a clear stderr
      message naming the parsed ticket ID and suggesting either
      `close_ticket.py --files` or `git add <code paths>`.
- [x] Hook does not block commits without `fix(TXXX)` prefix (e.g. `docs:`,
      `chore:`, session-close commits).
- [x] Hook does not block when `--no-verify` is passed (standard git behavior).
- [x] Wired into `.claude/settings.json` `PreToolUse` `Bash` matcher.
- [x] Test in `tests/test_check_fix_commit_has_code.py`: covers
      (a) `fix(T001):` with no code staged → blocked,
      (b) `fix(T001):` with `scripts/foo.py` staged → allowed,
      (c) `docs: ...` with no code staged → allowed,
      (d) `fix(T001):` with only `docs/archive/T001-...md` staged → blocked.

## Notes

S16 workflow-review finding #5. Defense-in-depth for [[T079]].
Mirrors the shape of existing `check_ticket_acs.py` PreToolUse hook.

## Resolution

Created scripts/hooks/check_fix_commit_has_code.py: parses git commit -m flags for fix(T\d+): prefix, runs git diff --cached --name-only to verify code files are staged, blocks with exit 2 + clear stderr message if none found. --no-verify bypasses the check. Wired into .claude/settings.json PreToolUse Bash matcher. 10 tests in tests/test_check_fix_commit_has_code.py covering all 4 AC scenarios plus edge cases (case sensitivity, --no-verify, tests/ prefix, error message content).

Closed S17 2026-05-26.
