---
id: T132
title: raise_for_harness._current_session: fail-closed when workspace sessions.md missing (do not fall back to harness session)
severity: high
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S23 2026-05-28
closed: S23 2026-05-28
---

## Problem

Surfaced by Opus S22 review (Concern #1). `scripts/tools/raise_for_harness.py:_current_session` silently fell back to harness-global `current_session.py` when a workspace had no `internal/sessions.md` yet — stamping the harness session number into the SR file's `raised:` frontmatter field. That field is parsed by `list_raised_concerns.py` and `promote_raised_concern.py`, so the lie persists across the audit trail. The twin helper in `scripts/tools/surface_workspace_concerns.py` (T126) is already fail-closed (returns None, archive commit omits session); this ticket aligns `raise_for_harness.py` to the same posture before T128 consolidates the two helpers.

Note: chosen semantics for this call site are warn-and-error (exit 2), not warn-and-omit, because the value lands in a tracked frontmatter field rather than a commit message — wrong-value cost is higher.

## Acceptance Criteria

- [x] When workspace sessions.md is missing, _current_session does NOT call harness-global current_session.py
- [x] Tool exits 2 with clear error message naming the missing sessions.md path
- [x] No harness-session-format string can be written to a workspace raised/*.md frontmatter raised: field
- [x] Test covers missing-sessions.md path and asserts exit 2

## Resolution
Replaced silent fallback to harness session ID with fail-closed exit 2 in raise_for_harness._current_session. When workspace internal/sessions.md is missing, the tool refuses to write the SR rather than stamping a harness session number into the workspace audit trail (Invariant 1 — workspace↔harness session-number separation). Error names the expected path (workspaces/<slug>/internal/sessions.md + docs_path override). Caller signature now passes slug. Inverted test_falls_back_to_harness_session... → test_refuses_to_fall_back_when_internal_sessions_md_missing; _setup() now seeds workspace sessions.md by default. All 18 raise_for_harness tests pass. T128 (consolidate _current_session helpers) can now land safely — both call sites are explicitly fail-closed with semantics matched to their call-site sensitivity (warn-and-omit for commit messages; warn-and-error for tracked frontmatter).

Closed S23 2026-05-28.
