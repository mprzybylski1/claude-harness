---
id: T159
title: close_ticket.py --files cross-repo support
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S30 2026-06-02
closed: S30 2026-06-14
---

## Problem

When ticket changes span the harness repo + a workspace project repo, the script rejects with 'out-of-repo --files'. For workspace sessions doing app work, this is the common case. Workaround is manual git commit in project repo then re-running close_ticket without --files.

## Acceptance Criteria

- [x] Group --files paths by containing git repo
- [x] Stage + commit per repo with a shared ticket-derived message
- [x] Reject only when a file path is not inside any known repo

### Invariant note (S30)

This reverses the T125 blanket reject, so **Architecture Invariant 3 was amended**
(approved this session): multi-repo `--files` is now permitted, but each repo is
committed *separately* (one commit per git root, shared message) — never a single
index spanning repos, and a path in no git repo is still rejected. The invariant's
teeth ("no silent, no single-index cross-repo commit") are preserved.

## Resolution
close_ticket.py --files may now span multiple git repos. Removed the T125 blanket cross-repo rejection (_check_cross_repo_files) and the multi-root --commit refusal (_refuse_multi_root_commit). _stage_extra_files already groups by git root; --commit now iterates roots and commits each separately with the shared ticket-derived message, running the index-clean guard per root. A --files path in no git repo is still rejected before the ticket moves. Architecture Invariant 3 amended to permit per-repo multi-repo closes (no silent/single-index cross-repo commit). Rewrote TestCloseTicketCrossRepoFiles; removed the obsolete TestCommitMultiRootRefusal unit class.

Closed S30 2026-06-14.
