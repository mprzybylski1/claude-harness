---
id: T091
title: Fix _parse_fix_commit to handle --git-dir= and --work-tree= flag forms
severity: high
status: closed
phase: 2
layer: tooling
opened: S19 2026-05-26
closed: S19 2026-05-26
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] =form tokens (--git-dir=path, --work-tree=path) are consumed correctly (single-token, startswith("-") branch; git_cwd intentionally stays None as these are not working-dir equivalents)
- [x] Space-separated --git-dir <path> and --work-tree <path> consume both tokens (i+=2); not setting git_cwd is correct since they differ semantically from -C
- [x] Tests cover: -C space, --git-dir space, --git-dir=, --work-tree space, --work-tree= forms

## Resolution
Investigation showed the implementation already correctly handles all flag forms: = form consumed by startswith('-') branch (single token, i+=1 correct); space form already consumes both tokens (i+=2). Not setting git_cwd for --git-dir/--work-tree is by design — they are not working-directory equivalents. Added 6 unit tests covering all forms via direct import of _parse_fix_commit.

Closed S19 2026-05-26.
