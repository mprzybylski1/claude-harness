---
id: T051
title: close_ticket.py — three correctness bugs (S9 #1 #2 #3)
severity: high
status: closed
phase: 2
layer: infra
opened: S10 2026-05-26
closed: S10 2026-05-26
---

## Problem

Three bugs in `scripts/tools/close_ticket.py` flagged in S9 Opus review:

1. **S9 #1 — `_docs_paths()` uses stdlib regex instead of YAML loader.** `re.search` on
   `workspace.yaml` misparses quoted paths (includes quotes), multi-line values, and is
   inconsistent with the rest of the harness which uses `workspace_config.load_workspace`.

2. **S9 #2 — non-atomic write+rename.** `ticket_path.write_text(content)` then
   `ticket_path.rename(dest)` — if `rename` fails (cross-filesystem, permissions), the
   ticket is left in `open/` with closure changes already applied (frontmatter says
   `status: closed`, resolution placeholder gone). Next invocation exits on the missing
   placeholder, leaving the user stuck.

3. **S9 #3 — harness root wins on duplicate ticket IDs.** `_find_ticket` returns on first
   match; if a workspace and harness both have T100, the caller silently gets the harness
   one. No warning or disambiguation flag.

## Acceptance Criteria

- [ ] `_docs_paths()` uses `workspace_config.load_workspace` (yaml.safe_load) instead of regex.
- [ ] File move writes to `dest` first, then unlinks source — so a write failure leaves
      `open/` untouched and a successful write + failed unlink leaves both files (recoverable).
- [ ] `_find_ticket` collects all matches across all scopes; exits with an informative error
      if more than one is found (user must disambiguate with `--workspace`).
- [ ] `--workspace SLUG` flag added so user can override disambiguation.
- [ ] All existing tests still pass.

## Notes

Brand-new script (T045, S9). Easier to harden now than after it's in muscle memory.
Bundle all three fixes — they're all in `close_ticket.py` and share tests.

## Resolution

Fixed 3 correctness bugs in scripts/tools/close_ticket.py:
1. S9 #1: _docs_paths() now uses workspace_config.load_workspace (yaml.safe_load) instead of stdlib regex — handles quoted paths, multi-line YAML values, and stays consistent with rest of harness.
2. S9 #2: File move now writes to dest first, then unlinks source — a write failure leaves open/ untouched; a successful write + failed unlink leaves both files (recoverable).
3. S9 #3: _find_ticket collects all matches before returning; exits with disambiguation error if >1 match. Added --workspace SLUG flag to resolve duplicates.
Added 4 new tests covering all three fixes.

Closed S10 2026-05-26.
