---
id: T152
title: Detect gitignored docs_path location at session-start
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S29 2026-06-01
closed: S29 2026-06-01
---

## Problem

A workspace can configure docs_path to point inside a repo whose .gitignore excludes that directory (e.g. docs_path: ~/SubTracker/.harness with .gitignore containing .harness/). Tickets and sessions written there are untracked and lost on machine sync. Caught by advisor mid-session in sub-tracker S1; would have been a lost-tickets incident otherwise.

## Acceptance Criteria

- [x] session-start or a new helper runs git check-ignore against docs_path and surfaces a high-severity warning if the path is ignored
- [x] Warning text: docs_path is gitignored — workspace docs will not sync across machines
- [x] Skipped silently when docs_path is not configured

## Resolution
New check_docs_path_gitignored.py runs git check-ignore on workspace docs_path. Wired into session-start as step 9 (workspace sessions only). Surfaces high-severity warning when docs_path is gitignored.

Closed S29 2026-06-01.
