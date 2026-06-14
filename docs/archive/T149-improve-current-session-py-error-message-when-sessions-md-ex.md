---
id: T149
title: Improve current_session.py error message when sessions.md exists in wrong format
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S29 2026-06-01
closed: S30 2026-06-15
---

## Problem

When sessions.md exists but contains no S<N> YYYY-MM-DD: entries (e.g. markdown table format from manual scaffolding), the error message says only 'no entries found' without indicating the file was loaded or showing the expected format. This blocked create_ticket.py invisibly during sub-tracker S1.

## Acceptance Criteria

- [x] If the file exists and has content but no match, print the first non-blank line and the expected pattern
- [x] Existing happy-path behaviour unchanged
- [x] Unit test covering the wrong-format case (tests/test_current_session.py)

## Resolution
When sessions.md exists with content but no 'S<N> YYYY-MM-DD:' match, get_current_session now prints the first non-blank line, the byte count (file loaded), and the expected pattern with an example — instead of the bare 'no entries found'. Empty/whitespace-only files say so explicitly. Happy path and the missing-file path are unchanged. New tests/test_current_session.py covers wrong-format, empty, happy, and missing-file cases.

Closed S30 2026-06-15.
