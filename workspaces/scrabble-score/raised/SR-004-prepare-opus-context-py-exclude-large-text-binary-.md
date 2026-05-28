---
id: SR-004
from: scrabble-score
raised: S9 2026-05-28
title: prepare_opus_context.py: exclude large text/binary resources from diff
severity: low
status: raised
harness_ticket:
resolved_in:
---

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

## Harness disposition

(Filled by harness on promotion or rejection.)
