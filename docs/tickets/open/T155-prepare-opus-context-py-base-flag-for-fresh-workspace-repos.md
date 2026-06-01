---
id: T155
title: prepare_opus_context.py --base flag for fresh workspace repos
severity: low
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S29 2026-06-01
closed:
---

## Problem

Workspace repos that have never received a session-close commit produce a 0-line diff because the anchor git log --grep finds nothing and the main...HEAD fallback is also empty on a single-branch repo. Operator had to hand-write a diff-injection script for /implementation-review.

## Acceptance Criteria

- [ ] --base SHA flag explicitly sets the diff base
- [ ] Without --base, fall back to first commit after the timestamp of the last sessions.md log line before giving up
- [ ] Warning message updated to point at the new flag

## Resolution
(Fill in on close.)
