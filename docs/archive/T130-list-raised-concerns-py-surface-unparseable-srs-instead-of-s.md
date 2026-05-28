---
id: T130
title: list_raised_concerns.py: surface unparseable SRs instead of silently skipping
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed: S23 2026-05-28
---

## Problem

Pre-T123, four SR files (SR-004..SR-007) silently disappeared from `list_raised_concerns.py`
output because their unquoted-colon titles tripped `yaml.safe_load`. `_parse_frontmatter`
caught `yaml.YAMLError`, printed a stderr WARNING, and returned `{}` — indistinguishable
from "no frontmatter present". The operator saw an empty stdout and no idea anything was
missing. Even with T123 quoting fixed for new SRs, the failure mode persists for any
hand-edited or migration-corrupted SR; the tool must surface it.

## Acceptance Criteria

- [x] When yaml.safe_load fails on an SR file, surface the SR under a 'Pending raised concerns (unparseable — review manually)' section instead of skipping it after a stderr WARNING
- [x] Section omitted entirely when no unparseable SRs exist (no noise)
- [x] Test covers: malformed frontmatter SR appears in the unparseable section with file path

## Resolution
Distinguished 'no frontmatter' from 'YAML parse error' in _parse_frontmatter (now returns dict | None). main() buckets None-returning paths into an 'unparseable' list and emits a 'Pending raised concerns (unparseable — review manually):' section with each path. Section is omitted entirely when no malformed SRs exist (no noise). Triage instructions only print when there are actually-pending parseable items. 3 new tests (TestUnparseableSurface): bad SR surfaced, section omitted when clean, bad SR coexists with clean SRs. All 13 tests pass.

Closed S23 2026-05-28.
