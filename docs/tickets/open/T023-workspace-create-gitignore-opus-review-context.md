---
id: T023
title: workspace.py create should scaffold .gitignore for opus_review_context.md
severity: low
status: open
phase: 1
layer: infra
opened: S4 2026-05-25
closed:
---

## Problem

The harness root `.gitignore:9` already excludes `docs/opus_review_context.md` because
it is an ephemeral file regenerated each session. When a workspace uses `docs_path`
to live inside the project repo (e.g. scrabble-score at
`~/Documents/Projects/ScrabbleScore/.harness/`), the same ephemeral file gets written
to `<docs_path>/opus_review_context.md` — which is in a different repo and is NOT
gitignored. It shows up as an untracked file in the project repo on every session.

## Acceptance Criteria

- [ ] `scripts/tools/workspace.py` `cmd_create` adds `<docs_path-relative>/opus_review_context.md` to the project repo's `.gitignore` when `docs_path` is set and lives inside a different git repo than the harness.
- [ ] If a `.gitignore` doesn't exist at the project repo root, create it.
- [ ] If the entry is already present, no-op (idempotent).
- [ ] Test in `tests/`: fresh project repo gets the line added; existing `.gitignore` gets appended; second invocation is a no-op.
- [ ] All existing tests still pass.

## Notes

Surfaced during scrabble-score S1 when `opus_review_context.md` appeared as untracked
in the project repo after `/implementation-review`. Low severity — clutter, not
breakage.

## Resolution

(Fill in on close.)
