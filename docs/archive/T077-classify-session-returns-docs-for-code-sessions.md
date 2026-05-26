---
id: T077
title: classify_session.py returns docs for code-changing workspace sessions
severity: low
status: closed
phase: 2
layer: process
opened: S16 2026-05-26
closed: S16 2026-05-26
---

## Problem

`classify_session.py --repo <ws>` returns `docs` for sessions where code commits were
made to the workspace repo. Observed in scrabble-score S4: three commits to
`<ws>/ScrabbleScore/view/GameView.swift` were present before session-close, but the
classifier returned `docs`.

**Root cause hypothesis:** The script inspects `git diff` at invocation time (dirty
working tree) rather than commits since the last session-close boundary. By session-close
time, the working tree is clean, so no code changes are detected.

**Fix:** Classify based on commits since the last `docs:` session-close commit on master
(or the equivalent boundary marker), not the current dirty diff.

## Acceptance Criteria

- [x] `classify_session.py --repo <ws>` returns `code` when code commits (non-docs files)
  have been made since the last session-close commit, even if the working tree is clean.
- [x] Returns `docs` only when all commits since the last session-close touch docs paths
  exclusively.
- [x] Test covering the workspace case with a mocked commit history.

## Notes

No harm caused in S4 (operator overrode the result), but flow-critical if SKILL-following
is stricter in future sessions. See `docs/workflow_review_S4_findings.md` finding #4.

## Resolution

Added _classify_no_config() to classify_session.py: when --repo is given but the repo has no harness.yaml, classifies any committed non-docs file (not .md/.rst/.txt and not under docs/) as 'code'. main() now checks for harness.yaml presence and routes to _classify_no_config() vs classify() accordingly. Root cause was harness-root code_paths allowlist being applied to arbitrary workspace repos — Swift files under MyApp/View/ don't match scripts/, src/, etc. Two tests added.

Closed S16 2026-05-26.
