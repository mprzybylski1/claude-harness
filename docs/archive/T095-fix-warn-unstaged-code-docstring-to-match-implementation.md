---
id: T095
title: Fix _warn_unstaged_code docstring to match implementation
severity: low
status: closed
phase: 2
layer: tooling
opened: S19 2026-05-26
closed: S19 2026-05-26
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] Docstring updated to accurately describe behavior (warns on any unstaged code, not just non-files paths)

## Resolution
Updated _warn_unstaged_code docstring to accurately state it warns on any unstaged or untracked code files in the repo, including those unrelated to --files.

Closed S19 2026-05-26.
