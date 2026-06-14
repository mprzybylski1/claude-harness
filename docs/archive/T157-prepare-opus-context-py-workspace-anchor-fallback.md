---
id: T157
title: prepare_opus_context.py workspace anchor fallback
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-02
closed: S30 2026-06-14
source: menu-planner/SR-001
---

## Problem

When --repo targets a workspace project repo with no 'docs: S' session-close commits, the script falls back to git diff main...HEAD which produces 0 lines on a single-branch repo. /implementation-review runs against an empty diff and produces no findings.

## Acceptance Criteria

- [x] When anchor grep returns no results and --repo is set, fall back to diff-from-initial-commit or accept --base SHA
- [x] Test added: workspace repo with no session-close commits produces non-empty diff
- [x] Stderr warning when fallback path is used

## Resolution
Added --base SHA flag and an initial-commit (empty-tree) fallback to prepare_opus_context.py. When no session-close anchor exists and no --base is given, the diff now runs from the canonical empty tree (4b825dc...) so a fresh workspace repo's first session produces a non-empty diff instead of an empty main...HEAD. A stderr WARNING naming the fallback and pointing at --base is emitted. New tests in tests/test_prepare_opus_context_base.py.

Closed S30 2026-06-14.
