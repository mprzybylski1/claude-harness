---
id: T144
title: close_ticket.py --append mode preserves rich Resolution content written during the work
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S26 2026-05-31
closed: S26 2026-05-31
---

## Problem

`close_ticket.py` assumes the `## Resolution` section contains the
`(Fill in on close.)` placeholder and replaces it with `--resolution` text. But the
natural workflow (observed across T140/T142/T143 this session) is to grow the
Resolution section organically while the work is in flight — recording design
decisions, advisor pushback, scope changes — which deletes the placeholder. At close
time `--resolution` then fails with `ERROR: ## Resolution placeholder not found —
ticket format unexpected`, forcing the operator to either delete their rich content
or restore a placeholder just so the script can overwrite it with a one-liner. That
inverts the value: the rich content IS the resolution; `--resolution` is the one-line
commit summary. (Surfaced by S26 workflow review.)

## Acceptance Criteria

- [x] New --append flag keeps the existing `## Resolution` content and adds the
      --resolution text at the END of that section (content leads, one-line summary +
      close stamp trail). [Implemented as true-append rather than the original
      "immediately after the header" wording — content-first reads better in the
      archive; following sections like `## Notes` are left untouched.]
- [x] Default behavior unchanged: --resolution alone still replaces the '(Fill in on close.)' placeholder
- [x] When neither --append is passed nor the placeholder is present, error message names the remediation explicitly (restore placeholder OR pass --append), not 'ticket format unexpected'
- [x] Tests: --append preserves existing body; --append errors if section is empty / only-placeholder (nothing to preserve); default path still replaces placeholder; clarified error message fires when placeholder is missing

## Resolution

Split `_replace_resolution(content, resolution, append=False)` into two paths:
- **append=False (default, unchanged):** strict-then-permissive placeholder replace.
  The final no-placeholder branch now prints a two-bullet error naming both
  remediations (pass `--append`, or restore the placeholder) — that subsumes T145.
- **append=True:** new `_append_resolution` parses the `## Resolution` section via a
  shared `_resolution_section` helper (header / body-up-to-next-`##` / rest), and
  appends `resolution` after the existing body. Fails closed (exit 2) when the section
  is empty or only the placeholder (nothing to preserve → use default mode) or when
  there is no `## Resolution` header at all. The `rest` slice keeps any following
  section (e.g. `## Notes`) intact.

`--append` added to argparse (a plain flag, composes with `--resolution`/`--resolution-file`)
and threaded into the `main()` call site. 6 new unit tests in
`tests/test_close_ticket_resolution.py` exercise `_replace_resolution` directly
(replace happy-path, reworded missing-placeholder error, append-preserves-content,
append-leaves-following-sections, and the three append error paths). All 42
close_ticket tests pass.

This ticket and T145 were themselves closed using `--append` — dogfooding the feature.

Added close_ticket.py --append: keeps existing ## Resolution content and adds the one-line resolution at the end (content leads, summary trails). Default replace path unchanged; the no-placeholder error now names both remediations (subsumes T145). Split into _resolution_section/_append_resolution helpers; fails closed when nothing to preserve. 6 new unit tests; 42 close_ticket tests pass.

Closed S26 2026-05-31.
