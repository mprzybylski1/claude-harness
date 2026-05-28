---
id: T116
title: fix raise_for_harness.py: use workspace session number for SR stamping
severity: high
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S21 2026-05-28
closed: S21 2026-05-28
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] When raise_for_harness.py detects a workspace slug, it resolves `<INTERNAL>/sessions.md` (honoring `docs_path` in workspace.yaml) and passes `--sessions` to current_session.py
- [x] SRs created in a workspace session are stamped with the workspace's session number, not the harness session number
- [x] reject_raised_concern.py and promote_raised_concern.py remain on harness session numbering — they call `current_session.py` without `--sessions` (unchanged); the asymmetry is intentional since both run from harness root
- [x] Test fixture: workspace at S5 raising an SR while harness is at S9 produces `raised: S5` (test_uses_workspace_session_number_when_internal_sessions_md_exists)
- [x] Edge case: missing workspace sessions.md falls back to harness session number (test_falls_back_to_harness_session_when_internal_sessions_md_missing)
- [x] Edge case: `docs_path` override in workspace.yaml redirects sessions.md lookup correctly

## Resolution
Added _workspace_sessions_md helper that resolves <INTERNAL>/sessions.md (honoring docs_path override in workspace.yaml). _current_session now accepts an optional path and forwards it as --sessions to current_session.py. SRs raised from a workspace now stamp the workspace's session number; when the workspace has no sessions.md yet, falls back to harness session number. reject/promote scripts unchanged — they continue to use harness session numbers since they run from harness root.

Closed S21 2026-05-28.
