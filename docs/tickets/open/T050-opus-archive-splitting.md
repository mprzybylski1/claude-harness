---
id: T050
title: Split opus_notes archive by session range when over line threshold
severity: low
status: open
phase: 2
layer: tooling
opened: S9 2026-05-26
closed:
---

## Problem

`docs/archive/opus_notes_S0-S9.md` is currently 1034 lines and was read 4× in S9 for
carry-forward archeology. As sessions accumulate, this file will grow linearly and become
a significant token cost at session-start/close (currently each read is the whole file).

The `T046` `expand_carry_forward.py` script will mitigate this by replacing full reads
with targeted extraction. This ticket is a complementary structural measure for when
T046's targeting is not enough — e.g. if the whole archive is read for an Opus review.

Surfaced by workflow-review S9.

## Acceptance Criteria

- [ ] `rotate_opus_notes.py` (or a new script) splits `opus_notes_S0-S9.md` into
      per-decade ranges (e.g. `opus_notes_S0-S9.md`, `opus_notes_S10-S19.md`) when the
      file exceeds a configurable line threshold (default: 1500 lines, configurable via
      `harness.yaml workflow_opus_archive_max_lines`).
- [ ] `expand_carry_forward.py` (T046) searches all archive files regardless of range.
- [ ] `prepare_opus_context.py` is updated to search by range when building Opus context.
- [ ] Test: verify split happens at threshold; verify T046 still finds findings across files.

## Notes

Low urgency — T046 reduces the need for full archive reads. Address when the archive
exceeds 1500 lines or T046 is complete, whichever comes first.

## Resolution
(Fill in on close.)
