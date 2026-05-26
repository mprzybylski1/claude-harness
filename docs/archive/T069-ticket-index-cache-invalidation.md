---
id: T069
title: regenerate_ticket_index cache never invalidated
severity: medium
status: closed
phase: process
layer: process
opened: S13 2026-05-26
closed: S14 2026-05-26
---

## Problem

`scripts/tools/generate_ticket_index.py` (called via `regenerate_ticket_index.py`)
uses `_get_docs_path_map()` to build a mapping of ticket IDs to docs paths. This
cache is computed once per process run and never invalidated.

When multiple tickets are closed in the same session (common in multi-ticket sessions),
the cache state from the first close operation is reused for subsequent closes. If a
ticket file moves on disk between calls (e.g. via concurrent agent operations), the
stale cache produces an INDEX.md that references the wrong paths or omits recently
moved tickets entirely.

This has appeared as a 2-session carry-forward in Opus notes: INDEX.md showing stale
state after multi-close sessions.

The fix depends on usage pattern:
- If called once per process invocation (current), the cache is fine and the issue is
  elsewhere (e.g. the `PostToolUse` hook calling `regenerate_ticket_index.py` being
  invoked at the wrong time).
- If called multiple times per session from the same process, the cache should be
  invalidated by clearing the module-level dict before each call, or by rebuilding
  per-invocation.

Investigation needed to confirm which case applies before implementing.

## Acceptance Criteria

- [x] Root cause of stale INDEX.md after multi-close sessions is confirmed and
  documented (is it the cache or a different issue?).
- [x] If the cache is the culprit: `_get_docs_path_map()` is called fresh per
  invocation, or the module-level state is cleared at the start of each
  `generate_ticket_index()` call.
- [x] A test covers the multi-close scenario: close two tickets in sequence and verify
  INDEX.md reflects both closures correctly.
- [x] Opus carry-forward for this issue is cleared in the next review.

## Notes

2-session Opus carry-forward (S12, S13). No ticket previously. Root cause ambiguous —
investigate before implementing.

## Resolution

Root cause confirmed: the cache is NOT the culprit. _docs_path_cache in regenerate_ticket_index.py is per-process — the hook spawns a fresh subprocess per PostToolUse event, so the cache resets on every invocation. generate_ticket_index.py has no caching at all; it reads tickets from disk fresh on every call. The stale INDEX.md issue was worktree state divergence (same root cause as T067): worktree agents each generated INDEX.md from their own open/ snapshot, which overwrote the main repo's INDEX.md when copied back. Added clarifying comment to _docs_path_cache. Added TestMultiCloseIndexFreshness (2 tests) confirming load_tickets and render_index produce correct output after sequential closes. S14.

Closed S14 2026-05-26.
