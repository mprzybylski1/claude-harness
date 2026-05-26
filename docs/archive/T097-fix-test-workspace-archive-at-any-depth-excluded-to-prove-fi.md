---
id: T097
title: Fix test_workspace_archive_at_any_depth_excluded to prove filename-regex behavior
severity: medium
status: closed
phase: 2
layer: tooling
opened: S19 2026-05-26
closed: S19 2026-05-26
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] Test stages archive file + a code file and asserts commit is allowed (code counted, archive excluded)
- [x] Test name accurately reflects what it proves

## Resolution
Rewrote test to stage archive file + code file and assert commit is allowed, proving the filename-regex correctly excludes the archive while counting the code file. Test name now accurately reflects behavior being proved.

Closed S19 2026-05-26.
