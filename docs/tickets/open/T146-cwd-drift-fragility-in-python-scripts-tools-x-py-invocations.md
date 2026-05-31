---
id: T146
title: cwd-drift fragility in 'python scripts/tools/X.py' invocations after a cd elsewhere
severity: low
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S26 2026-05-31
closed:
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [ ] scripts/h (or equivalent ~5-line shell wrapper) resolves the tool path via $CLAUDE_PROJECT_DIR so 'h close_ticket T140 ...' works from any cwd
- [ ] CLAUDE.md mentions the wrapper in a 'common gotchas' or 'commands' section so future sessions discover it
- [ ] Verify by running the wrapper from /tmp and confirming it dispatches to the correct harness tool

## Resolution
(Fill in on close.)
