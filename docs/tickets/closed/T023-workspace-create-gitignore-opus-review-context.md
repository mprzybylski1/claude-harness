---
id: T023
title: workspace.py create should scaffold .gitignore for opus_review_context.md
severity: low
status: closed
phase: 1
layer: infra
opened: S4 2026-05-25
closed: S5 2026-05-25
---

## Problem

The harness root `.gitignore:9` already excludes `docs/opus_review_context.md` because
it is an ephemeral file regenerated each session. When a workspace uses `docs_path`
to live inside the project repo (e.g. scrabble-score at
`~/Documents/Projects/ScrabbleScore/.harness/`), the same ephemeral file gets written
to `<docs_path>/opus_review_context.md` — which is in a different repo and is NOT
gitignored. It shows up as an untracked file in the project repo on every session.

## Acceptance Criteria

- [x] `scripts/tools/workspace.py` `cmd_create` adds `<docs_path-relative>/opus_review_context.md` to the project repo's `.gitignore` when `docs_path` is set and lives inside a different git repo than the harness.
- [x] If a `.gitignore` doesn't exist at the project repo root, create it.
- [x] If the entry is already present, no-op (idempotent).
- [x] Test in `tests/`: fresh project repo gets the line added; existing `.gitignore` gets appended; second invocation is a no-op.
- [x] All existing tests still pass.

## Notes

Surfaced during scrabble-score S1 when `opus_review_context.md` appeared as untracked
in the project repo after `/implementation-review`. Low severity — clutter, not
breakage.

## Resolution

Fixed in S5. Added `_add_opus_context_to_gitignore(docs_path)` helper to `workspace.py`. `cmd_create` calls it after scaffolding when `docs_path_resolved` is set. The helper finds the project repo root via `git rev-parse --show-toplevel`, skips if same repo as harness, computes the relative path, and appends idempotently. Tests in `tests/test_workspace_gitignore.py` (5 tests covering create, append, idempotent, nested path, non-git skips).
