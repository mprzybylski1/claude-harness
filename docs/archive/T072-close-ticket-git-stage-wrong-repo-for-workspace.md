---
id: T072
title: close_ticket.py _git_stage uses harness git root for workspace tickets
severity: high
status: closed
phase: process
layer: process
opened: S14 2026-05-26
closed: S15 2026-05-26
---

## Problem

`close_ticket.py::_git_stage` always runs `git -C str(ROOT)` where `ROOT` is the harness
root (`scripts/tools/close_ticket.py` → parents[2]). When closing a workspace ticket
whose `docs_path` points to an external project repo (e.g. ScrabbleScore), the ticket
path, dest, and INDEX.md path are all inside that external repo — outside the harness
git tree.

`git -C $HARNESS_ROOT add /path/outside/harness/...` exits non-zero, triggering the
`CalledProcessError` branch, printing a warning and calling `sys.exit(2)` even though
the atomic move and index regeneration succeeded.

Consequence: every workspace ticket close with an external `docs_path` fails at the
staging step. The ticket IS closed on disk but the process exits 2, which looks like
a full failure to callers and scripts.

This regression was introduced in S14 (T064). Tests only covered harness-root and
tmp_path-internal workspace cases; no test used a workspace with an external git repo.

## Acceptance Criteria

- [x] When `internal` is outside the harness git tree, `_git_stage` stages using the
  correct git repo root (the project repo that owns `internal`), not the harness root.
- [x] When `internal` is inside the harness git tree (harness-root tickets), behavior
  is unchanged.
- [x] A test covers the external-repo case (can use a real tmp git repo for the
  workspace, separate from the harness tmp repo).
- [x] `close_ticket.py T<N>` exits 0 on successful close+staging for both harness-root
  and workspace-external-docs_path tickets.

## Notes

Fix approach: detect the git root for `dest` (or `internal`) using
`git -C <internal_dir> rev-parse --show-toplevel`. Use that as the `git -C` root for
all staging operations. Fall back to `ROOT` if the detection fails.

Alternatively, if the workspace has its own git repo, stage using that repo's root.
The `git rev-parse --show-toplevel` approach is most robust.

## Resolution

Added _git_root_for(path) helper that runs git rev-parse --show-toplevel on the dest path to detect the correct git repo. _git_stage now uses the detected root instead of hardcoded ROOT. Also fixed dest.relative_to(ROOT) in the final print — falls back to absolute path when dest is outside the harness tree. Both issues found via the new test_external_docs_path_workspace_stages_in_project_repo test (S14/S15).

Closed S15 2026-05-26.
