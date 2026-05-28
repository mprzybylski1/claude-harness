---
id: T123
title: raise_for_harness.py: YAML-quote title field so colons in title don't silently break list_raised_concerns.py
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed: S22 2026-05-28
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] raise_for_harness.py writes title in a form that survives yaml.safe_load even when the title contains a colon
- [x] Regression test: a title with a colon round-trips through raise_for_harness.py write + yaml.safe_load and equals the original
- [x] SR-004 through SR-007 reparse cleanly; list_raised_concerns.py emits no WARNING for them

## Resolution
raise_for_harness.py now YAML-quotes the title field when a plain scalar would be misparsed (colon-space, hash-after-space, leading YAML indicator, embedded quote, etc.). Added _yaml_scalar helper + 4 regression tests (TestTitleQuoting). Also fixed SR-001 status (manually promoted in S20, never close-the-looped because T104-T112 carry no source: frontmatter) to resolved/S20, and re-quoted titles in SR-004..SR-007 so list_raised_concerns.py surfaces them.

Closed S22 2026-05-28.
