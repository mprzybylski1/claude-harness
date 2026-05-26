---
id: T067
title: Worktree isolation for parallel agents doesn't hold
severity: high
status: open
phase: process
layer: process
opened: S13 2026-05-26
closed:
---

## Problem

Claude Code's `isolation: "worktree"` creates a separate git worktree per agent, but
agents receive absolute paths in their prompts (e.g. `docs/tickets/open/T058-*.md` at
the main repo path). When those paths are used via `Read`, `Edit`, or `Write`, the agent
operates on the main repo, not the worktree.

In S13, 3 of 5 parallel agents (T060, T061, T063) wrote directly to main-repo paths,
while T044 and T055/T056 wrote to their worktrees (requiring manual `cp` back to main).
T061 even committed directly to `master` from its worktree. This created a merge
inconsistency: the worktree commit's INDEX.md was generated from stale worktree state,
re-tracking ghost-deleted files in HEAD.

There are two possible strategies:

**Option A — Stop using worktrees for parallel harness work.** Run agents without
`isolation: "worktree"`, accept sequential merge risk, and coordinate via explicit file
locks or sequential task ordering. Simpler, avoids all isolation confusion.

**Option B — Enforce worktree isolation in prompts.** Always pass worktree-relative
paths to agents and never include main-repo absolute paths. This requires a reliable way
to know the worktree path at spawn time, which Claude Code doesn't expose directly.

Option A is recommended.

## Acceptance Criteria

- [ ] CLAUDE.md documents the worktree isolation limitation with a concrete recommendation
  (Option A preferred: don't use `isolation: "worktree"` for parallel harness-root work).
- [ ] CLAUDE.md or the relevant skill documents an alternative parallel strategy
  (e.g., "for N independent tickets, open N separate Claude Code instances each without
  worktree isolation, or run sequentially").
- [ ] A note is added to `.claude/skills/session-start/SKILL.md` or `CLAUDE.md` warning
  that `isolation: "worktree"` does not prevent agents from writing to main-repo paths
  when absolute paths appear in their prompts.

## Notes

Observed S13. The worktree mechanism works as designed — the isolation is at the git
level, not the filesystem level. Agents can still open absolute paths outside their
worktree directory.

If Option B is pursued instead, a prerequisite is a way to inject the worktree path into
the agent prompt at spawn time — currently not exposed by Claude Code's Agent tool.

## Resolution

(Fill in on close: what was done and in which session/commit.)
