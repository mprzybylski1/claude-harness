---
id: T046
title: expand_carry_forward.py — surface Opus archive context by finding ID
severity: medium
status: closed
phase: 2
layer: tooling
opened: S9 2026-05-26
closed: S9 2026-05-26
---

## Problem

When `extract_opus_key_sections.py` references a long-lived carry-forward like "S1 #3"
or "S3 #3", the actual description lives in `docs/archive/opus_notes_S0-S9.md`
(currently 1034 lines). To act on the carry-forward, the user has to grep the archive
and read surrounding context. S9 required 4 separate archive reads just to understand
3 carry-forward references before they could be ticketed.

A targeted extractor would replace those reads and could be invoked automatically by
session-start when long-lived carry-forwards exist.

Surfaced by workflow-review S9.

## Acceptance Criteria

- [x] `scripts/tools/expand_carry_forward.py <finding-id>` accepts IDs in flexible
      formats: `S1#3`, `S1 #3`, `S3#3`, `s1#3` (case-insensitive).
- [x] Searches all `opus_notes*.md` files — current (`docs/opus_notes.md`) and all
      files in `docs/archive/` matching `opus_notes*.md`.
- [x] Extracts: the matching finding heading line + all text up to the next numbered
      finding heading (or end of section).
- [x] If found in multiple files (carry-forward repeated), prints each occurrence with
      a source header `[From: <filename>]` and the session it appeared in.
- [x] Exits 1 with a clear message if the ID is not found in any file.
- [x] `--latest` flag: prints only the most recent occurrence (by session date in the
      file's `# Opus Review — S<N>` header).
- [x] Test: synthetic `opus_notes.md` + archive file; assert correct extraction,
      multi-file output, not-found exit code.
- [x] `extract_opus_key_sections.py --with-carry-forwards` output updated to include a
      hint: `(run expand_carry_forward.py S<N>#<M> to see full description)`.

## Notes

The session-start skill step 3 calls `extract_opus_key_sections.py --with-carry-forwards`.
If long-lived carry-forwards are listed, the briefing should prompt the user to run
`expand_carry_forward.py` for context — or the session-start skill can run it
automatically when the count is > 0.

## Resolution
Implemented scripts/tools/expand_carry_forward.py: searches docs/opus_notes.md and docs/archive/opus_notes*.md for numbered findings by ID (S1#3, 's1 #3', etc.), prints full text per occurrence with [From: filename — SN] headers, supports --latest to show only the most recent. HARNESS_ROOT env var for test isolation. Six tests in TestExpandCarryForward — all pass. extract_opus_key_sections.py --with-carry-forwards now prints a hint to run expand_carry_forward.py for details.

Closed S9 2026-05-26.
