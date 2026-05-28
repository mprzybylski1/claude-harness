---
id: T130
title: list_raised_concerns.py: surface unparseable SRs instead of silently skipping
severity: low
status: open
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed:
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [ ] When yaml.safe_load fails on an SR file, surface the SR under a 'Pending raised concerns (unparseable — review manually)' section instead of skipping it after a stderr WARNING
- [ ] Section omitted entirely when no unparseable SRs exist (no noise)
- [ ] Test covers: malformed frontmatter SR appears in the unparseable section with file path

## Resolution
(Fill in on close.)
