---
id: T117
title: fix promote_raised_concern.py _extract_body: stop at any unknown H2 header
severity: high
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S21 2026-05-28
closed: S21 2026-05-28
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] `_extract_body` toggles `in_section` off on any H2 header not in `copy_on` (`stop_on` allowlist removed)
- [x] H3+ subheadings inside a copy section are preserved (not falsely matched as H2 — guard `startswith("## ") and not startswith("### ")`)
- [x] Regression test uses a multi-section SR fixture (`## Principle`, `## Boundary slot`, `## File format`, `## CLIs to build`, `## Guardrails` between/around Context and Proposed change) and asserts those sections do NOT appear in the ticket body
- [x] Existing `test_body_copied_to_problem_section` and `test_proposed_change_copied` still pass
- [x] H3 preservation covered by `test_h3_subheadings_inside_copy_section_are_preserved`

## Resolution
Replaced the 3-item stop_on allowlist in _extract_body with 'any H2 terminates section' logic. H2 detection guards against H3+ false-matches via 'startswith("## ") and not startswith("### ")'. Unknown sections (## Principle, ## Boundary slot, etc.) no longer bleed into the promoted ticket body. Added TestExtractBodyH2Boundary with 4 tests covering multi-section SRs and H3 subheading preservation.

Closed S21 2026-05-28.
