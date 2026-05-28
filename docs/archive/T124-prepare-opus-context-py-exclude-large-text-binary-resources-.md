---
id: T124
title: prepare_opus_context.py: exclude large text/binary resources from diff
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S22 2026-05-28
closed: S22 2026-05-28
source: scrabble-score/SR-004
---

## Problem

Promoted from scrabble-score/SR-004.

## Context

S9 added `ScrabbleScore/Resources/sowpods.txt` (267,751 lines, 2.6 MB) as a
bundled wordlist for dictionary validation. `prepare_opus_context.py` includes
all changed files in the priority-ordered diff, capped at 600 signal lines.
The wordlist alone consumed the entire cap, so all seven modified source/test
files appeared as "truncated — not shown" in the review context. The Opus
reviewer could not make confirmed findings against any of the actual
implementation changes this session.

Not a blocker (session closed normally), but the implementation-review is
effectively bypassed whenever a large resource file is added or modified.
This will recur on any future session that touches wordlists, fixture files,
or other data assets.

## Proposed change

`prepare_opus_context.py` should exclude files matching patterns like
`*.txt`, `*.json` (non-code), `*.csv`, `*.plist` from the priority-ordered
diff when they exceed a configurable line threshold (e.g., 1000 lines).
Alternatively, move `Resources/` and other asset directories to the bottom
of the priority ordering (below `*.swift`, `*.py`, `*.md`), so source and
test files always appear first within the cap.

The stat section (file-level change counts) can keep the full list —
removing large files only from the *diff body*, not the summary.
## Acceptance Criteria

- [x] prepare_opus_context.py excludes large data-file diff blocks from the displayed diff body (default extensions: .txt, .json, .csv, .plist, .xml, .yaml, .yml, .lock)
- [x] Exclusion is gated by a line-count threshold (1000) so small config edits are unaffected
- [x] Excluded files are listed in a "Large data files" section so Opus knows they changed
- [x] Stat section (`git diff --stat`) still shows the full list — exclusion is diff-body-only
- [x] Regression: under-cap diffs with no large assets return unchanged
- [x] Regression: the 267k-line wordlist scenario no longer truncates code (5×30-line code blocks all visible under 600-line cap)

## Resolution
Added _LARGE_ASSET_EXTS (.txt/.json/.csv/.plist/.xml/.yaml/.yml/.lock) + _LARGE_ASSET_LINE_THRESHOLD=1000 to prepare_opus_context.py. _apply_diff_cap now identifies large-asset diff blocks early and returns them as a 4th tuple element (large_asset_paths); the displayed diff body strips them entirely, even when under cap. Both call sites in main() surface a new 'Large data files (diff body excluded)' section when the list is non-empty. Stat section is unaffected so Opus still sees the file-level change count. 12 new unit tests in tests/test_prepare_opus_context_large_assets.py (TestIsLargeAsset + TestApplyDiffCapLargeAssets) cover: extension match, threshold gating, source-code exemption, lock-file recognition, under-cap stripping, over-cap exclusion, regression preservation, and the original 267k-line sowpods.txt scenario.

Closed S22 2026-05-28.
