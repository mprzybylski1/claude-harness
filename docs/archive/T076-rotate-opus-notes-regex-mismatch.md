---
id: T076
title: rotate_opus_notes.py regex mismatch — never rotates workspace notes
severity: medium
status: closed
phase: 2
layer: process
opened: S16 2026-05-26
closed: S16 2026-05-26
---

## Problem

`rotate_opus_notes.py` reports "0 section(s) — no rotation needed" on workspace
`opus_notes.md` files even when multiple review sections are present.

**Root cause hypothesis:** Workspace `opus_notes.md` uses `## Opus Review — S<N>` (h2
headings). The script likely scans for `# Opus Review` (h1). The regex never matches, so
nothing is rotated and `opus_notes.md` grows unbounded.

Observed in scrabble-score S4: two `## Opus Review — S1/S2` sections present; script
reported 0 sections.

**Fix:** Update the regex to match `^## Opus Review` (h2). Verify against both harness-root
opus_notes.md (which may use h1) and workspace opus_notes.md (h2) — handle both forms.

## Acceptance Criteria

- [x] Script correctly detects `## Opus Review — S<N>` (h2) sections in workspace
  `opus_notes.md` and rotates when the threshold is exceeded.
- [x] Script continues to handle `# Opus Review` (h1) form used at harness root (if
  applicable), or the h1 form is confirmed unused and the regex is updated unambiguously.
- [x] Test: a workspace opus_notes.md with 2 h2 sections triggers rotation; script reports
  correct section count.

## Notes

See `docs/workflow_review_S4_findings.md` finding #3. Without rotation, opus_notes.md
grows unbounded — becomes a token-cost issue within 10+ workspace sessions.

## Resolution

Fixed _SECTION_RE in rotate_opus_notes.py line 28: changed r'^# Opus Review' to r'^#{1,2} Opus Review' so both h1 (harness-root) and h2 (workspace) section headers are detected. All existing h1 tests continue to pass. Two new h2 tests added: rotation of two-section workspace file, and single-section no-op with correct count reported.

Closed S16 2026-05-26.
