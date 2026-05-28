---
id: T113
title: implementation-review SKILL missing --repo flag for workspace sessions
severity: medium
status: closed
phase: 2
layer: process
# repo: <name from workspace.yaml repos list>
opened: S21 2026-05-28
closed: S21 2026-05-28
source: scrabble-score/SR-002
---

## Problem

Promoted from scrabble-score/SR-002.

## Context

`.claude/skills/implementation-review/SKILL.md` Step 1 instructs the model to run:

```bash
python scripts/tools/prepare_opus_context.py
```

with no arguments. For workspace sessions this targets the harness repo's git
and produces a 0-diff context — the Opus reviewer then "reviews" an empty diff
and reports clean by definition. This is a silent correctness failure: the
mid-session review appears to run but covers nothing.

Surfaced in scrabble-score S8 — the first call produced `Written
docs/opus_review_context.md (10KB, 0 diff lines)`. Caught by inspection of the
output count; would have been silently wrong otherwise.

The session-close SKILL Step 5 has the correct workspace-aware invocation
(`--repo`, `--sessions`, `--opus`, `--output`). The implementation-review SKILL
needs the same treatment.

Not blocking — workaround is to spot the `0 diff lines` output and re-run with
flags — but the workaround relies on attentive reading of a normally-skipped
prepare-context message.

## Proposed change

Update `.claude/skills/implementation-review/SKILL.md` Step 1 to match the
session-close Step 5 pattern:

- Show the harness-root form (no flags) as the default.
- Show the workspace form with `--repo <primary-repo-path>`, `--sessions
  <INTERNAL>/sessions.md`, `--opus <INTERNAL>/opus_notes.md`, `--output
  <INTERNAL>/opus_review_context.md`.
- Tell the model to check the output line for diff size and re-run with the
  workspace form if 0 diff lines appear in a workspace session.

Three-to-five-line change. No script changes needed.
## Acceptance Criteria

- [x] `implementation-review/SKILL.md` Step 1 shows both harness-root and workspace forms of `prepare_opus_context.py`
- [x] Workspace form passes `--repo`, `--sessions`, `--opus`, `--output` matching session-close Step 5
- [x] SKILL tells the model to verify the diff line count and re-run with flags if 0 diff lines appear in a workspace session
- [x] Step 2 Agent prompt references the correct context path per session type (no hardcoded `docs/opus_review_context.md`)

## Resolution
Updated implementation-review SKILL Step 1 to show both harness-root and workspace forms of prepare_opus_context.py (matching session-close Step 5), with a check for 0 diff lines to catch missing flags. Also fixed Step 2's Agent prompt to reference the correct context path via <CONTEXT_PATH> placeholder instead of hardcoded docs/opus_review_context.md.

Closed S21 2026-05-28.
