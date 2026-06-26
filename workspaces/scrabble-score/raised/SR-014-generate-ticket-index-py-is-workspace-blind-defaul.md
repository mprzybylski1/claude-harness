---
id: SR-014
from: scrabble-score
raised: S16 2026-06-26
title: "generate_ticket_index.py is workspace-blind: defaults output to harness INDEX + harness session number"
severity: medium
status: raised
harness_ticket:
resolved_in:
---

## Context

Surfaced in S16 (scrabble-score) while closing T028. I ran
`generate_ticket_index.py --tickets-dir <workspace>/.harness/tickets` (no
`--workspace`). The tool **ignored the workspace context for the OUTPUT**: it wrote
the **harness** `docs/tickets/INDEX.md`, stamped it with the **harness** session
number (S31), and computed nonsensical ages (workspace ticket ages measured against
harness session numbers — "15–24 sessions" for tickets days old). Had to
`git checkout HEAD -- docs/tickets/INDEX.md` to revert harness-state pollution, then
re-run with `--workspace scrabble-score` (which works correctly).

Compounding gap: the cross-layer write hook (Invariant 2) only guards `Edit`/`Write`
tool calls — it did **not** catch a Python script writing into the harness-protected
`docs/tickets/INDEX.md` via Bash. So a workspace session silently wrote harness state
with no block.

Not blocking (workaround: always pass `--workspace <slug>`), but a real footgun — the
`--tickets-dir`-only invocation looks correct and silently corrupts harness state.

## Proposed change

1. `generate_ticket_index.py`: when `--tickets-dir` resolves to a workspace path (or
   more generally, when the open-tickets dir is outside harness `docs/`), derive the
   output INDEX path **and** session number from that workspace — never fall back to
   harness defaults. Better: fail-closed (exit non-zero) on an ambiguous target rather
   than defaulting to harness, mirroring Invariant 3's "no silent default" teeth.
2. Consider whether the cross-layer write hook can cover script-mediated writes to
   protected paths (it's a `PreToolUse` on `Edit|Write`; Bash-run scripts bypass it).
   If not feasible, document the gap so it's a known limitation, not a surprise.

## Harness disposition

(Filled by harness on promotion or rejection.)
