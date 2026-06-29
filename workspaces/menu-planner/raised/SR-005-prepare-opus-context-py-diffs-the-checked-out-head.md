---
id: SR-005
from: menu-planner
raised: S17 2026-06-29
title: "prepare_opus_context.py diffs the checked-out HEAD, but with concurrent agents / worktree merges the session's work can live on a different branch (main) than the parked workspace checkout (a feature branch). Result: the prepared opus_review_context.md captured a session-old tree with NONE of the S17 work — a reviewer trusting it alone would review an empty diff. Consider: detect/parameterise the review base branch, or diff against origin/main / the branch where commits landed, or warn loudly when HEAD has no session commits."
severity: medium
status: raised
harness_ticket:
resolved_in:
---

## Context

(Why this matters, what workspace surfaced it, blocking yes/no.)

## Proposed change

(What the workspace thinks should happen. Harness may disagree.)

## Harness disposition

(Filled by harness on promotion or rejection.)
