---
id: T157
title: prepare_opus_context.py workspace anchor fallback
severity: medium
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-02
closed:
---

## Problem

When --repo targets a workspace project repo with no 'docs: S' session-close commits, the script falls back to git diff main...HEAD which produces 0 lines on a single-branch repo. /implementation-review runs against an empty diff and produces no findings.

## Acceptance Criteria

- [ ] When anchor grep returns no results and --repo is set, fall back to diff-from-initial-commit or accept --base SHA
- [ ] Test added: workspace repo with no session-close commits produces non-empty diff
- [ ] Stderr warning when fallback path is used

## Resolution
(Fill in on close.)
