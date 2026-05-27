---
id: T103
title: generate_ticket_index.py: skip TEMPLATE.md/T000 sentinel + add --output to session-close Step 0
severity: high
status: closed
phase: process
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S20 2026-05-27
closed: S20 2026-05-27
---

## Problem

Two defects observed during S4 close of the Scrabble Score workspace (opus_notes.md
S4 review, concern #1):

1. **`generate_ticket_index.py` can parse `TEMPLATE.md` as a real ticket.** Opus saw a
   ghost `T000 | Short description (keep under 60 chars) | 2 | 3 | 4 | process | backend
   | frontend | fullstack | infra | process | 4 sessions` row in the uncommitted
   workspace INDEX.md diff at `<INTERNAL>/opus_review_context.md:370`. The T074 fix
   (auto-descend into `open/` when `--tickets-dir` points to the parent) prevents this
   in the parent-dir invocation, but the bug class is still possible when the dir
   passed to the generator contains a `TEMPLATE.md` and no `open/` subdir (or the
   subdir is transiently missing). `parse_frontmatter()` happily returns
   `id=T000, title=Short description (keep under 60 chars)` from the template, and
   `load_tickets()` only filters on `id` being non-empty.

2. **`.claude/skills/session-close/SKILL.md:75` invokes the generator without
   `--output`.** The command shown is:
   `python scripts/tools/generate_ticket_index.py --session <N> --tickets-dir <INTERNAL>/tickets`
   When run from harness root (which is the documented cwd for session-close), the
   default `--output` resolves to `<harness_root>/docs/tickets/INDEX.md`. Reproduced
   in this session: ran the command with the Scrabble workspace's `--tickets-dir`,
   it wrote T008 into the harness's own `docs/tickets/INDEX.md`. This is a
   workspace-isolation contamination — adjacent to Invariant 5 — and silently
   corrupts the harness's open-ticket dashboard.

Both are harness-tooling bugs, not Scrabble code.

## Acceptance Criteria

- [x] generate_ticket_index.py skips TEMPLATE.md / id=T000 entries regardless of how --tickets-dir is invoked
- [x] session-close SKILL.md Step 0 command passes --output so it does not clobber harness INDEX.md when run from harness root
- [x] regression test asserts T000 not in output when --tickets-dir contains TEMPLATE.md but no open/ subdir
- [x] regression test asserts running the SKILL.md Step 0 command from harness root writes to workspace INDEX, not harness INDEX

## Resolution
Defensive filter against TEMPLATE.md being parsed into INDEX.md, plus fix for session-close Step 0 clobbering harness INDEX.md when run from harness root.

generate_ticket_index.py load_tickets() now skips any file named TEMPLATE.md and any frontmatter id of T000. The T074 auto-descend fix prevented the common parent-dir invocation from hitting the bug, but Opus saw a ghost T000 row in the S4 workspace INDEX diff anyway; the precise call path was not reproducible. The defensive filter makes the sentinel impossible to surface regardless of how --tickets-dir is invoked.

session-close/SKILL.md Step 0 now passes --output <INTERNAL>/tickets/INDEX.md so the command writes to the workspace INDEX rather than defaulting to <harness_root>/docs/tickets/INDEX.md when run from harness root. Reproduced: pre-fix, running the documented command from harness root wrote workspace T008 into the harness's own INDEX.

Three regression tests added in tests/test_workspace_path_flags.py: TEMPLATE.md excluded when scanned directly (no open/ subdir), TEMPLATE.md-only dir yields zero tickets, and SKILL.md Step 0 command parser asserts --output is present.

Closed S20 2026-05-27.
