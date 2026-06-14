---
id: T146
title: cwd-drift fragility in 'python scripts/tools/X.py' invocations after a cd elsewhere
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S26 2026-05-31
closed: S30 2026-06-15
---

## Problem

Bare `python scripts/tools/X.py` invocations resolve the path relative to cwd, so they
break after a `cd` into a workspace repo or elsewhere. A small cwd-independent wrapper
lets `h close_ticket ...` work from any directory.

## Acceptance Criteria

- [x] scripts/h (or equivalent ~5-line shell wrapper) resolves the tool path via $CLAUDE_PROJECT_DIR (with a self-location fallback) so 'h close_ticket T140 ...' works from any cwd
- [x] CLAUDE.md mentions the wrapper in a 'common gotchas' or 'commands' section so future sessions discover it
- [x] Verify by running the wrapper from /tmp and confirming it dispatches to the correct harness tool (verified manually + tests/test_h_wrapper.py)

## Resolution
Added scripts/h: a self-locating bash wrapper that resolves the harness root from $CLAUDE_PROJECT_DIR (falling back to the script's own location at scripts/h), so 'h <tool> ...' maps to scripts/tools/<tool>.py and runs from any cwd. Strips an optional .py suffix; errors (exit 2) on unknown tool or no args. Verified from /tmp with and without CLAUDE_PROJECT_DIR. CLAUDE.md Commands section documents it. tests/test_h_wrapper.py covers dispatch-from-foreign-cwd, .py-suffix, unknown-tool, and no-args.

Closed S30 2026-06-15.
