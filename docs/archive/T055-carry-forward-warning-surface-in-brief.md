---
id: T055
title: S10 — carry-forward warning swallowed in brief output (S9 #6)
severity: low
status: closed
phase: 2
layer: infra
opened: S10 2026-05-26
closed: S13 2026-05-26
---

## Problem

`scripts/tools/extract_carry_forwards.py` prints a warning to stderr when no session
reference pattern matches the opus_notes.md content. When called via
`extract_opus_key_sections.py` (which imports it), the warning is discarded — the user
sees an empty carry-forwards list with no explanation why.

S9 #6 flagged this; T053 only addressed the docstring (#5), not the warning surfacing (#6).

## Acceptance Criteria

- [x] When `extract_carry_forwards.py` emits its "could not determine current session"
      warning, the caller (`extract_opus_key_sections.py`) surfaces it as a `Note:` line
      in its stdout output OR captures and re-emits it to its own stderr.
- [x] The warning reaches the user regardless of whether the caller is used interactively
      or via subprocess.
- [x] All existing tests still pass.

## Notes

Low priority — only affects sessions where opus_notes.md lacks the expected session header
format. But silent empty lists are confusing at session-start.

## Resolution
Added run_with_carry_forwards() to extract_opus_key_sections.py; captures stderr from extract_carry_forwards.main() and re-emits any warning as a Note: line on stdout so the user sees it whether invoked interactively or as a subprocess.

Closed S13 2026-05-26.
