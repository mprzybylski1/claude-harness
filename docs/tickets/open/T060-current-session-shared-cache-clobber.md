---
id: T060
title: current_session.py persists shared cache regardless of --sessions arg
severity: medium
status: open
phase: 2
layer: infra
opened: S12 2026-05-26
closed:
---

## Problem

`scripts/tools/current_session.py:43-48` (`persist_session`) writes the computed session number to `.git/CLAUDE_SESSION_ID` every time, regardless of which `--sessions` path was passed. This is the root cause of T057: workspace-aware callers and harness-root callers fight over the same cache file, and whoever wrote last wins.

T057 fixed the *consumer* (the telemetry hook no longer reads the cache), but the *producer* is still broken. Any future caller that consults `.git/CLAUDE_SESSION_ID` will hit the same clobbering behaviour. `session_close_commit_msg.py` still reads it (per T057 ticket Notes), so the latent footgun is live.

## Acceptance Criteria

- [ ] `persist_session` is called only when `current_session.py` runs without `--sessions` (i.e. the harness-root case), OR the cache is removed entirely (callers re-derive from sessions.md).
- [ ] If kept, the cache is namespaced (e.g. `.git/CLAUDE_SESSION_ID.<hash-of-sessions-path>`) so workspace and harness don't share a file.
- [ ] Test: call `current_session.py --sessions /path/A.md` then `current_session.py --sessions /path/B.md`; the harness cache is unchanged (or both caches are correct).
- [ ] `session_close_commit_msg.py` (the remaining consumer) is updated if the cache shape changes.

## Notes

Smallest fix: skip `persist_session(n)` when `args.sessions` was provided. Caller of `current_session.py --sessions X` doesn't need the cache; it's there for harness-internal fallback only. Roughly 2 LoC.

Surfaced by /workflow-review S12.

## Resolution

(Fill in on close.)