---
id: T114
title: session-close commit discipline guidance for shared-file tickets
severity: low
status: closed
phase: 2
layer: process
# repo: <name from workspace.yaml repos list>
opened: S21 2026-05-28
closed: S21 2026-05-28
source: scrabble-score/SR-003
---

## Problem

Promoted from scrabble-score/SR-003.

## Context

`session-close/SKILL.md` "Commit discipline" section establishes "one commit per
ticket" but does not address the case where two tickets edit the same file in
one session. Surfaced in scrabble-score S8: T015 and T016 both edited
`ScrabbleScoreTests.swift`. Closing in ticket order required a three-step manual
process — revert T015's test additions, close T016, re-add T015's tests, close
T015 — and produced a transient state where T015's source changes
(`BoardViewModel.swift`) were present without the corresponding tests.

The natural fix is sequence: write T016's test changes first → close T016 →
write T015's test changes → close T015. TDD order makes this fall out for free.
But the SKILL.md doesn't say so, and the natural failure mode is "write all the
tests first, then close tickets" — which is what happened.

Cost of the failure mode: ~5 minutes of manual file-state juggling per
multi-ticket session that touches a shared file. Risk: forgotten changes mid-
juggle.

Not blocking.

## Proposed change

Add one sentence to `session-close/SKILL.md` Commit discipline section, near
"one commit per ticket":

> **When two tickets edit the same file, close each ticket before writing the
> next ticket's changes to that file** — TDD sequence makes the per-ticket
> staging fall out naturally. Otherwise you'll have to revert-and-reapply to
> get clean per-ticket commits.

One sentence. No tooling change.
## Acceptance Criteria

- [x] `session-close/SKILL.md` Commit discipline section includes a directive on shared-file ticket sequencing
- [x] Guidance lives next to the per-ticket-commit pattern so it's visible at the relevant decision point

## Resolution
Added one sentence to session-close SKILL Commit discipline section directing the model to close each ticket before writing the next ticket's changes when both touch the same file. TDD sequence makes per-ticket staging fall out naturally; deviation requires revert-and-reapply.

Closed S21 2026-05-28.
