---
id: T080
title: Pre-commit hook blocks fix(TXXX) commits with no code files staged
severity: medium
status: open
phase: process
layer: process
opened: S16 2026-05-26
closed:
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

- [ ] New hook `scripts/hooks/check_fix_commit_has_code.py` parses the `-m`
      message for `^fix\(T\d+\):` prefix.
- [ ] When the prefix matches, the hook runs `git diff --cached --name-only`
      and checks for at least one path matching the code prefixes
      (`scripts/`, `tests/`, `src/`, `lib/`, or whatever `harness.yaml`
      `code_paths` declares).
- [ ] If zero code files are staged, hook exits non-zero with a clear stderr
      message naming the parsed ticket ID and suggesting either
      `close_ticket.py --files` or `git add <code paths>`.
- [ ] Hook does not block commits without `fix(TXXX)` prefix (e.g. `docs:`,
      `chore:`, session-close commits).
- [ ] Hook does not block when `--no-verify` is passed (standard git behavior).
- [ ] Wired into `.claude/settings.json` `PreToolUse` `Bash` matcher.
- [ ] Test in `tests/test_check_fix_commit_has_code.py`: covers
      (a) `fix(T001):` with no code staged → blocked,
      (b) `fix(T001):` with `scripts/foo.py` staged → allowed,
      (c) `docs: ...` with no code staged → allowed,
      (d) `fix(T001):` with only `docs/archive/T001-...md` staged → blocked.

## Notes

S16 workflow-review finding #5. Defense-in-depth for [[T079]].
Mirrors the shape of existing `check_ticket_acs.py` PreToolUse hook.

## Resolution

> **Client-visible:** Git commits prefixed `fix(TXXX):` are now blocked
> automatically when no code files are staged, preventing accidental
> documentation-only "fix" commits.

(Fill in on close.)
