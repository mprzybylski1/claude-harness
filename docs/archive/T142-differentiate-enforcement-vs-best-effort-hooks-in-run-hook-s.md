---
id: T142
title: Differentiate enforcement vs. best-effort hooks in run_hook.sh — enforcement hooks must fail-closed on script-not-found
severity: medium
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S26 2026-05-31
closed: S26 2026-05-31
---

## Problem

T138 (SR-011) made hook dispatch cwd-independent and **fail-open**: `run_hook.sh:31`
silently `exit 0`s when the named `<name>.py` is missing, so a resolution accident
(rename, partial checkout, perms, a future refactor that moves the script) can never
deadlock the session. Correct for best-effort hooks (telemetry/index must never block
a tool). But the SAME blanket fail-open applies to `check_cross_layer_writes` — the
enforcer of Invariant 2 (session-type declaration) and Invariant 4 (workspace
isolation). If that script ever fails to resolve, workspace isolation silently
vanishes instead of blocking — and Inv 4 calls cross-workspace leakage a
confidentiality violation, exactly the case where you want loud failure.
(S25 Opus review, Concern #1.)

## Scope narrowing (revised from the original Opus suggestion)

The original suggestion named three "enforcement" hooks (`check_cross_layer_writes`,
`check_ticket_acs`, `check_fix_commit_has_code`) and proposed a fail-OPEN allowlist
with a fail-CLOSED default. A matcher-by-matcher deadlock analysis (evidence Opus did
not have at suggestion time) shows that framing reintroduces the SR-011 deadlock class:

| Hook | Matcher | Fail-closed on missing script → |
|------|---------|----------------------------------|
| `check_cross_layer_writes` | `Edit\|Write` | Bash survives → `git checkout` recovers. **Recoverable.** |
| `check_fix_commit_has_code` | `Bash` | Edit/Write survive → semi-recoverable. |
| `check_ticket_acs` | `Edit\|Write\|Bash` | blocks **all three** → **unrecoverable deadlock.** |

So a fail-CLOSED *default* deadlocks via `check_ticket_acs`. Invert it: **default
fail-OPEN, with an explicit fail-CLOSED list.** The discriminator for that list is
two-pronged — *silent-skip is a confidentiality/safety harm* AND *fail-closed leaves
a recovery surface*. Only `check_cross_layer_writes` clears both bars (it is the sole
enforcer of the confidentiality boundary, and being `Edit|Write`-only it leaves Bash
as a recovery surface). The other two enforce process discipline, not confidentiality.

Two consequences for the original ACs:
- The settings.json `|| exit 0` (the *wrapper-itself-missing* guard) stays as-is: when
  the wrapper is gone, the allowlist logic is gone too, so there is nothing to
  differentiate with, and a blanket `exit 2` there deadlocks via `check_ticket_acs`.
  All differentiation lives in `run_hook.sh`, where the wrapper is present.
- Residual tradeoff (accepted): a *future* confidentiality enforcer fails open until
  added to the list. Mitigated by a guard test that names the fail-closed set — not by
  defaulting fail-closed. The deadlock cost outweighs the maintenance cost.

## Acceptance Criteria

- [x] `run_hook.sh` maintains an explicit fail-CLOSED hook-name list (currently just
      `check_cross_layer_writes`); the default for any other hook is fail-OPEN (exit 0)
- [x] When a fail-CLOSED hook's script cannot be resolved, `run_hook.sh` emits a visible
      stderr warning AND exits 2 (write blocked); all other hooks still exit 0 silently
- [x] `settings.json` is unchanged — its `|| exit 0` wrapper-missing guard stays fail-open
      (the allowlist logic lives in the wrapper, which is absent in that case); the
      existing `test_fail_open_when_project_dir_unset` stays green as the canary
- [x] `tests/test_hook_command_resolution.py` covers: missing `check_cross_layer_writes.py`
      → exit 2 + stderr; missing `check_ticket_acs.py` → exit 0 (proves no deadlock surface);
      a guard test names the fail-closed set

## Resolution
run_hook.sh now fail-CLOSES (stderr + exit 2) only when a hook in an explicit FAIL_CLOSED list has a missing script; every other hook stays fail-OPEN (exit 0). The list is exactly {check_cross_layer_writes}. CONSCIOUS NARROWING of the original 3-hook Opus suggestion: a matcher-by-matcher deadlock analysis (evidence Opus lacked) showed a fail-closed DEFAULT deadlocks via check_ticket_acs (matcher Edit|Write|Bash blocks every recovery surface). So the design is inverted — default fail-open, explicit fail-closed list — and only check_cross_layer_writes qualifies (sole Inv 2/4 confidentiality enforcer AND Edit|Write-only, leaving Bash as a git-checkout recovery surface). settings.json left unchanged: when the wrapper itself is missing the allowlist logic is gone too, and a blanket exit 2 there would deadlock; existing test_fail_open_when_project_dir_unset stays green as the canary. Accepted residual tradeoff: a future confidentiality enforcer fails open until added to the list, guarded by test_fail_closed_set_is_named_in_wrapper. 5 new tests in TestFailClosedDifferentiation; 482 pass.

Closed S26 2026-05-31.
