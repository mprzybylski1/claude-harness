---
id: T015
title: Fix AC pre-lint Bash branch silently no-ops for docs_path workspaces
severity: critical
status: closed
phase: 2
layer: hooks
opened: S4 2026-05-25
closed: S4 2026-05-25
---

## Problem

`check_ticket_acs.py` Bash branch (lines 139-171) resolves ticket source paths relative
to `ws_dir` (workspaces/<slug>/) and `REPO_ROOT`. When a workspace has `docs_path` set,
the actual ticket lives at `<docs_path>/tickets/...` which is in neither location. The
bounds check rejects it as "outside REPO_ROOT and workspace", emits a WARNING, and
continues — unchecked ACs are never blocked.

This is a silent fail-open regression introduced by T014: the AC pre-lint is the only
guard preventing tickets from moving to closed/ with unchecked items.

## Acceptance Criteria

- [x] Absolute source paths are accepted when they resolve inside the docs root
  (`_get_closed_dir().parent.parent`)
- [x] Relative source paths try the docs root as a candidate before falling back to
  `REPO_ROOT`
- [x] Bounds check allowlist includes the docs root
- [x] Test: Bash `mv` in docs_path workspace with unchecked AC is blocked (exit 2)
- [x] Test: Bash `mv` in docs_path workspace with all ACs ticked passes (exit 0)
- [x] All existing tests still pass

## Resolution

S4 2026-05-25: AC pre-lint now correctly blocks unchecked items in docs_path workspaces — Bash source path resolution and bounds check both account for the docs root.

Computed `docs_root = _get_closed_dir().parent.parent` once at the top of the Bash branch. For relative paths: docs_root-relative candidate tried before ws_dir and REPO_ROOT. For the bounds check: docs_root added to the allowed-roots set alongside REPO_ROOT and ws_dir. 2 new tests in TestDocsPathRouting; 65/65 pass.
