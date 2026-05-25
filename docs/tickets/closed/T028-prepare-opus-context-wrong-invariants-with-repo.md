---
id: T028
title: prepare_opus_context --repo sends harness invariants not workspace's
severity: medium
status: closed
phase: 2
layer: infra
opened: S5 2026-05-25
closed: S6 2026-05-25
---

## Problem

`prepare_opus_context.py` lines 393 and 398 always load:
- `docs/architecture_invariants.md` from harness ROOT
- `docs/tickets/TEMPLATE.md` from harness ROOT

even when `--repo` points at a workspace project. Opus is then handed the harness's
invariants (safety-critical trading-era constraints) when reviewing workspace code,
which is misleading and produces off-topic review findings.

Invariants are project-specific by definition — sending the wrong set silently
degrades review quality for every workspace session.

Opus S5 finding #5.

## Acceptance Criteria

- [x] When `--repo` is provided, look for `<repo>/docs/architecture_invariants.md`
      first; fall back to harness root only if not found
- [x] Same lookup for `docs/tickets/TEMPLATE.md`
- [x] Existing test coverage for `prepare_opus_context.py` remains green
- [x] Test: when `--repo` has no `docs/architecture_invariants.md`, the harness
      fallback is used (no crash)

## Notes

Related to T027 (classify_session.py repo-flag config gaps).

## Resolution

S6 2026-05-25: Fixed `prepare_opus_context.py` to prefer `<repo_root>/docs/architecture_invariants.md` and `<repo_root>/docs/tickets/TEMPLATE.md` when `--repo` is given, falling back to harness root when absent. Also added missing-opus-path warning to stderr (T030e). Two tests added in `TestPrepareOpusContextInvariantPaths`.
