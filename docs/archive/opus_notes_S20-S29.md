# Opus Review Notes — Archive S20–S29

Archived from `docs/opus_notes.md`. All findings are either fixed or tracked in `docs/tickets/`.
Use `grep` to search. Do not load into session context.

---

# Opus Review — S20 2026-05-27

Scope: closed T104–T112 (9 tickets) implementing the full SR-001 workspace↔harness separation tooling. Net: 5 new tools, 1 new PreToolUse hook, 1 new SKILL.md pattern, ~860 LoC production + ~1240 LoC tests. Round-trip pipeline works in the happy path; tests cover the obvious shapes. Several safety-critical gaps in the hook + an Invariant 5 hole; one concrete bug in body extraction; and a session-id conflation that taints the audit trail this SR system was supposed to provide.

## Invariant Violations

**Invariant 5 (workspace isolation) — VIOLATED at the hook layer for cross-workspace writes.** `check_cross_layer_writes.py` blocks workspace→harness and harness→workspace-internal, but does **not** block workspace-A→workspace-B writes. In a workspace session with `.active_workspace=A`, writing to `workspaces/B/internal/sessions.md`:

- Is not in `_HARNESS_PROTECTED` → not blocked by the workspace branch
- Is not in `_is_boundary_slot` (parts[1] is "internal", not "raised") → not exempt
- Falls through to `sys.exit(0)` because the `else: if _is_workspace_internal` branch only triggers for harness-root sessions

The hook is named "cross-layer" but it implements layer separation, not workspace isolation. The architecture_invariants.md invariant 5 says scripts may only read paths in the active workspace's repos list; the hook should symmetrically block writes to other workspaces' internal/. Concrete attack: a Scrabble workspace agent could legitimately want to copy a template from another workspace and overwrite by accident, or maliciously exfiltrate client A's notes by reading them (reads are out of scope here, but writes should be blocked since `workspaces/*/internal/` is gitignored and per-workspace private).

Fix: in the workspace branch, also block any write to `workspaces/<other_slug>/internal/` where `other_slug != workspace_slug`.

## Architectural Concerns

1. **`scripts/hooks/check_cross_layer_writes.py:43-47, 102-121` — the hook fails open when `.claude/.active_workspace` is missing or empty.** [Concrete safety bug, high impact] The state file is the *sole* mechanism the hook uses to determine session type. The session-start SKILL.md instructs Claude to `echo -n "<WORKSPACE_SLUG>" > .claude/.active_workspace` at Step 0 — but this is documentation, not enforcement. If the agent skips Step 0 (no /session-start invoked, manual session start, a forgotten `echo`), the hook reads an empty file, infers "harness-root session", and **silently permits the workspace session to write `docs/tickets/`, `docs/sessions.md`, `docs/opus_notes.md`**. That is precisely the failure mode T103 documented and SR-001 was raised to prevent. The state file is also `.gitignored` so a fresh clone or new branch has no state file at all. The hook should fail closed: if the state file is absent or empty, block writes to both `docs/` *and* `workspaces/*/internal/` and emit a message instructing the operator to run `/session-start`. Or better, derive session type from CWD (matching `workspace_config.active_workspace_dir()`) so detection works without an out-of-band file.

2. **`scripts/hooks/check_cross_layer_writes.py` — two competing definitions of "active workspace" now exist in the codebase.** [Architectural fragility, moderate] The new hook reads `.claude/.active_workspace` (state-file); `scripts/tools/workspace_config.active_workspace_dir()` and `raise_for_harness._active_workspace_slug()` use CWD detection. These can disagree silently: `cd workspaces/A/` then forget to update the state file → CWD-tools say "workspace A", hook says "harness-root". The two systems should agree, ideally by having the hook delegate to `workspace_config.active_workspace_dir()` (which already exists, is tested, and is what the rest of the codebase uses). The state file adds a second source of truth that has to be kept in sync manually.

3. **`scripts/tools/raise_for_harness.py:60, scripts/tools/reject_raised_concern.py:62` — `_current_session()` invokes `current_session.py` without `--sessions <INTERNAL>/sessions.md`, so SRs created/rejected in a workspace are stamped with the HARNESS session number, not the workspace session number.** [Concrete bug, high impact on audit trail] `current_session.py` defaults to `<harness_root>/docs/sessions.md`. A workspace session running `raise_for_harness.py "..."`  gets a `raised: S<harness_N>` stamp; meanwhile the workspace's own sessions.md is on a completely independent counter. The actual SR-001 file shows `raised: S5 2026-05-27` (workspace S5) — the user clearly intended workspace numbering. Future SRs created by the new tool will silently use harness numbering, breaking the `[session_status: abandoned]` resumption pattern in session-close SKILL.md ("WIP branch wip/S[N]-blocked" → which N?). Fix: when the script detects a workspace slug, resolve `<INTERNAL>/sessions.md` and pass `--sessions` to `current_session.py`. Same fix for `reject_raised_concern.py` — but rejection runs in harness-root, so that one is correct to use harness session. So really the asymmetry is: `raise_for_harness.py` (workspace-side) needs workspace session; `reject` and `promote` (harness-side) need harness session.

4. **`scripts/tools/promote_raised_concern.py:59-73` — `_extract_body` does not stop at unknown H2 headers, so any SR with intermediate H2 sections (e.g. `## Principle`, `## Boundary slot`) copies *everything* from `## Context` through whatever the next recognised stop header is.** [Concrete bug] The function uses an allowlist for `copy_on` and a 3-item allowlist for `stop_on` (`harness disposition`, `acceptance criteria`, `related`). Any other `## ...` header in the middle does not toggle `in_section` off. SR-001 itself has `## Principle`, `## Boundary slot`, `## File format`, `## Status lifecycle`, `## One-cycle visibility / auto-archive`, `## CLIs to build`, `## Guardrails`, `## Abandoned-session pattern`, `## Session-start integration` — all 9 would be copied into the ticket Problem section. The test `test_body_copied_to_problem_section` uses a synthetic SR with only Context + Proposed change + Harness disposition, so it passes regardless. Fix: toggle `in_section` off on *any* `## ` line that's not in `copy_on`. Add a regression test using a multi-section SR fixture.

5. **`.claude/skills/session-close/SKILL.md:308-310` — the bash block has a backslash continuation that the static analysis runner can't parse standalone (bash block 10 syntax error in opus_review_context.md).** [Doc bug, low impact] The block:
   ```
   python scripts/tools/raise_for_harness.py "Description of blocker" \
     --severity high --workspace <WORKSPACE_SLUG>
   ```
   parses as two separate statements when the static analyser extracts and runs each line — line 2 begins with `--severity` and breaks. Either change the fence to `text` (which is what bash block 9 already does in the file) or collapse to a single line. The static-analysis FAIL surfacing this is now visible in every Opus review until fixed.

6. **`scripts/tools/promote_raised_concern.py:163-176` — promote always defaults to `--layer tooling` and never propagates the SR-suggested layer.** [Schema gap, low impact] The SR template has no `layer:` field, so there's no source. But the actual SR-001 promotion broke into 9 tickets — some are tooling (raise_for_harness scripts), some are process (session-close docs), some are infra (hooks). Hardcoding `tooling` is mostly right today but is fragile: future SRs about backend features should not be tagged `tooling`. Either accept `--layer` on promote_raised_concern.py to override, or add `layer:` to the SR template.

7. **`scripts/tools/close_ticket.py:497-511` — close-the-loop silently no-ops when SR file is missing.** [Defense-in-depth] The current behavior is "WARNING, ticket still closes" (test_missing_sr_file_warns_but_closes covers this). That is the right *default* for many cases (SR was manually archived, workspace was renamed), but it also means a typo'd `source: scrubble/SR-001` field stamped at promotion time will silently fail to resolve when the ticket closes, leaving the real SR stuck in `promoted` forever. Consider: emit a clearer error message including a `--ignore-missing-sr` flag for the manual case, and exit 2 (block close) by default. Or: validate `source:` field references a real file at promotion time so the typo case can't happen.

8. **`scripts/tools/surface_workspace_concerns.py:159-160` — terminal items are archived via `shutil.move` immediately after printing, with no git staging.** [Audit-trail gap, low impact] The SR-001 design explicitly says "Lives in the harness repo, tracked in git (audit trail)". When session-start moves an SR from `raised/` to `raised/archive/`, git sees a delete + add at the next commit, but nothing in the new tooling stages or commits this move. The session-start protocol does not include a "commit archived SRs" step. Effect: the archived SRs accumulate as uncommitted changes until the next time someone runs `git add -A`, possibly conflated with other unrelated work. Fix: either stage the move inside `surface_workspace_concerns.py` and let the session-close commit pick it up, or add an explicit "commit archived raised/ files" step in session-start SKILL.md.

9. **`scripts/tools/raise_for_harness.py:40-50` — `_next_sr_number` scans `raised/` and `raised/archive/` but not other workspaces' raised/.** [By design, but worth noting] SR IDs are workspace-scoped. Two workspaces can both have `SR-001`. The promote/reject tools take `<slug>/SR-NNN` so the namespace is fine — but cross-workspace ambiguity could cause confusion in `list_raised_concerns.py` output (which prints just `SR-001` per workspace group). The current format is unambiguous because of the workspace group header, but verbal references like "go promote SR-001" become ambiguous. Cosmetic; document or rename.

## Architectural Concerns — Test Gaps

1. **No test for the cross-workspace write case (Invariant 5 violation).** Add `test_workspace_A_blocks_workspace_B_internal_write` — sets `.active_workspace=A`, attempts write to `workspaces/B/internal/sessions.md`, asserts rc=2. Currently this passes (exit 0) because the hook doesn't block it.

2. **No test for the empty-state-file fail-open (Concern #1).** Add `test_missing_state_file_blocks_harness_writes_in_workspace_context` — does NOT write the state file, attempts write to `docs/sessions.md` while CWD is inside `workspaces/A/`, asserts rc=2 (currently fails: hook permits the write).

3. **No test for `_extract_body` with multi-section SR (Concern #4).** Synthetic SR with `## Context`, `## Principle`, `## Proposed change`, `## Harness disposition` — assert that `## Principle` content is NOT in the resulting ticket body. Currently passes because it IS in the body.

4. **No test that `raise_for_harness.py` stamps workspace session number, not harness session (Concern #3).** The current test mocks `current_session.py` with `print('S9')` — both layers' sessions return the same value, so the bug is invisible.

5. **No round-trip integration test.** Each script is unit-tested in isolation. A test that: (a) raises SR, (b) promotes via promote_raised_concern, (c) closes the ticket via close_ticket, and (d) asserts the SR ends up `resolved` with correct `resolved_in:` — would catch the session-id conflation, the body-extraction bug, and the staging coordination all at once.

## Suggested Next Session Focus

1. **Fix the Invariant 5 hole + the state-file fail-open (Concerns #1, #2, Invariant Violation).** This is the single highest-priority item: the entire SR system was supposed to *enforce* the boundary that T103 surfaced, but the hook fails open in the most realistic miss-mode (session-start not run, state file not written). ~15 LoC + 3 tests. Either delegate to `workspace_config.active_workspace_dir()` or fail closed when the state file is missing. Also extend the workspace branch to block cross-workspace internal writes.

2. **Fix `raise_for_harness.py` session-id source (Concern #3, Test Gap #4).** ~10 LoC. When workspace slug is detected, call `current_session.py --sessions <INTERNAL>/sessions.md` and use that. The audit-trail value of the SR system collapses without this — every SR-NNN file lies about when it was raised in the workspace timeline.

3. **Fix `_extract_body` H2 boundary detection (Concern #4, Test Gap #3).** ~5 LoC + 1 test. Treat any `## ` header not in `copy_on` as a section terminator. The actual SR-001 promotion produced a ticket body that copied 9 unrelated sections; the bug was invisible because no one read the resulting ticket bodies (they were replaced by manual `--resolution`).

## Carry-forwards (issues unresolved ≥ 2 sessions)

- **`architecture_invariants.md` is a placeholder file.** Now 3 sessions of acknowledgment without action. The S20 work added a concrete, testable invariant (workspace isolation via the new hook) but `docs/architecture_invariants.md` still has `[Name]` placeholders for invariants 1–2 and conditional language for 3–4. Invariant 5 (workspace isolation) is now demonstrably wrong as written — the new hook protects layer separation but not workspace separation; the doc should reflect what the code actually enforces.

# Opus Review — S21 2026-05-28

Scope: closed T113–T122 (10 tickets) — SR-002 + SR-003 from scrabble-score plus all 8 S20 Opus backlog items + trading-app hygiene. Net: substantial hook rewrite (cross-workspace blocking + fail-closed undeclared state + `__harness__` sentinel), workspace-session-id resolution in `raise_for_harness.py`, H2-boundary fix in `_extract_body`, `--layer` flag on promote, fail-closed missing-SR on `close_ticket.py`, git staging of archive moves, repo_hygiene trading-app guards. ~340 LoC production + ~470 LoC tests. Strong, focused follow-through — every S20 priority concern is addressed at the code level. A few residual edges remain; no invariant violations introduced.

## Invariant Violations

None. Invariant 5 (workspace isolation) is now *strengthened* at the hook layer by T115: workspace A writing to `workspaces/B/internal/` is rejected (`test_cross_workspace_internal_write_blocked`), closing the S20 hole. Invariant 4 (fail-closed) is also strengthened — T115 fails closed on missing/empty state file, T120 fails closed on missing source SR.

Caveat: the `docs/architecture_invariants.md` doc still has `[Name]` placeholders for Invariants 1–2 — now 3 sessions of carry-forward. Not a violation of the harness's own rules (the doc is intentionally a placeholder), but Opus has no concrete invariants 1–2 to check against. This is structural debt, not new in S21.

## Architectural Concerns

1. **`scripts/tools/raise_for_harness.py:80` — `_workspace_sessions_md` silently returns `None` when `<INTERNAL>/sessions.md` is missing, and `_current_session(None)` falls back to harness-wide session numbering.** [Concrete bug, moderate impact on audit trail] T116 fixes the happy path, but the failure mode is silent: a workspace with `workspace.yaml` present but `internal/sessions.md` missing (e.g. fresh workspace not yet session-logged, typo in `docs_path`, file deleted) gets a harness-stamped SR with no warning. Confirmed from the diff: `sessions_md if sessions_md.is_file() else None` returns `None`, then `_current_session(None)` constructs `cmd` without `--sessions`, then `current_session.py` defaults to harness `docs/sessions.md`. The S20 Concern #3 was about exactly this audit-trail lying problem; the fix narrows the window but leaves a silent fallback. Fix: when `_workspace_sessions_md` would return `None` for a real workspace (i.e. `workspaces/<slug>/` exists), emit a WARNING naming the missing path and the harness session number that will be used, so the operator sees the audit-trail break instead of discovering it later.

2. **`scripts/hooks/check_cross_layer_writes.py:97` — `__harness__` sentinel string collides with any workspace named `__harness__`.** [Diff suggests; low confidence — namespace hygiene] The sentinel is a magic string in `.claude/.active_workspace` content space, but `workspace.py create` does not (visible from the diff alone) reject `__harness__` as a slug. If a workspace gets that slug, the hook reads `__harness__` and treats the session as harness-root, permitting writes to *any* `workspaces/*/internal/` including this one's. Mitigation: reject the slug `__harness__` in `workspace.py create`, or change the sentinel to something that's not a valid slug pattern (e.g. include a `/` or start with `!`). Test coverage for this is absent in the new TestUndeclaredSession class.

3. **`scripts/tools/promote_raised_concern.py:158` — argparse handles the positional, then a manual `"/" not in args.sr_ref` check runs *after* parsing.** [Cosmetic, low impact] The post-argparse validation prints a custom usage line on missing `/`, but argparse has already accepted the value. Result is fine for behaviour (still exit 1 with usage). However the printed usage line `"Usage: promote_raised_concern.py <slug>/SR-NNN\nExample: ..."` duplicates what argparse already prints on its own errors, and the two messages will diverge as flags are added. Either fold the slash-validation into a `type=` callable on the positional or rely on a custom argparse `error` override. Trivial.

4. **`scripts/tools/repo_hygiene.py:90-118` — five trading-app artifact directories are hard-coded as STALE_FILES at the harness layer.** [Architectural fragility, low impact] `core/`, `execution/`, `data/`, `strategies/`, `risk_engine/` are project-specific names from the previous trading-app codebase. The harness aspires to be project-agnostic — these hard-coded names will be wrong noise for the next workspace that legitimately uses `data/` or `strategies/` at the harness root (unlikely but possible) and will be irrelevant dead config for every other workspace. Better long-term shape: move trading-app-specific stale entries into a workspace-local config (e.g. `workspaces/<slug>/repo_hygiene.yaml`) and have `repo_hygiene.py` merge them; or, since these dirs *should never exist* at harness root regardless of workspace, lift the check into a generic "harness root must not contain top-level dirs outside an allowlist" rule. The current shape works but bleeds project-specific knowledge into the harness.

5. **`scripts/tools/close_ticket.py:509-533` — fail-closed branch reports `len(matches)` matches but logs `"no matching file"` only when `matches` is empty.** [Cosmetic, low impact] When `len(matches) > 1` (multiple SR files match the glob — possible if the SR ID is reused or filename was duplicated), the `detail` says e.g. "found 3 matches" which is correct, but the message still says "SR file not found" which contradicts itself. Should distinguish "not found" (0 matches) from "ambiguous" (≥2 matches) and emit different remediation guidance — for the ambiguous case, advise listing and de-duplicating; for the missing case, advise fixing `source:` or `--ignore-missing-sr`. The conjoined branch handling masks the ambiguous-match case as if it were missing.

6. **`scripts/tools/surface_workspace_concerns.py:175-189` — `git add` after `shutil.move` runs even when not inside a git repo.** [Diff suggests; low confidence — minor] If the harness root somehow isn't a git repo (test fixture, copied tree), the `git add --` invocation fails with returncode != 0, the WARNING fires, and the user sees a "stage manually" instruction that won't work. Detection of "is this a git repo at all?" before attempting to stage would let the script silently skip staging in non-git contexts. Not a real failure mode in production, but the new tests would need a git-init in the temp dir to exercise the happy path.

## Architectural Concerns — Test Gaps

1. **No test for the silent harness-session fallback when `<INTERNAL>/sessions.md` is missing (Concern #1).** The new `TestSessionIdSource` tests verify the happy path (sessions.md present → workspace session used). Add a test: workspace.yaml present, `internal/sessions.md` deleted, assert (a) WARNING printed naming the missing path and (b) the SR gets harness-stamped (current behavior with no warning is the bug to fix).

2. **No test that `__harness__` is rejected as a workspace slug (Concern #2).** Add a test in test_workspace.py: `workspace.py create __harness__` should exit nonzero with an error naming the reserved sentinel.

3. **No test for the ambiguous-match case in `close_ticket.py --ignore-missing-sr` (Concern #5).** The new tests cover 0-match (fail closed) and the override flag, but not the ≥2-match case where `len(matches) > 1` and the message conflates with "not found".

4. **No round-trip integration test** (carried forward from S20 Test Gap #5). Still no end-to-end raise→promote→close test asserting (a) workspace session number on raise, (b) ticket body correctly extracted, (c) SR resolved with correct `resolved_in`. Each piece is unit-tested in isolation; the integration shape is uncovered.

## Suggested Next Session Focus

1. **Fix the silent harness-fallback in `raise_for_harness._workspace_sessions_md` (Concern #1, Test Gap #1).** ~10 LoC + 1 test. The S20 fix (T116) narrowed the window for audit-trail lies but didn't close it — when `internal/sessions.md` is absent, the SR still gets harness-stamped silently. Emit a WARNING naming the missing file and the fallback session being used. Without this, the same class of audit-trail bug T116 was created to fix can still happen, just in a narrower miss-mode.

2. **Reject `__harness__` as a workspace slug and add the test (Concern #2, Test Gap #2).** ~5 LoC + 1 test in `scripts/tools/workspace.py` create-validation. The sentinel collision is unlikely but real, and the cost of fixing it now is much smaller than recovering from a workspace named `__harness__` later.

3. **Reconcile `architecture_invariants.md` (3-session carry-forward).** Either fill in Invariants 1–2 with concrete harness rules (e.g. "no writes to `.claude/.active_workspace` outside session-start", "all hook scripts must `sys.exit(2)` on block — not 1") and update Invariant 5's verification clause to reference `check_cross_layer_writes.py` (which actually enforces the workspace-write side now), or delete the placeholder file and point Opus at `docs/tickets/TEMPLATE.md` as the schema-of-record. Every Opus review since S18 has noted this; the structural value of an "Invariant Violations" section depends on having real invariants.

## Carry-forwards (issues unresolved ≥ 2 sessions)

- **`architecture_invariants.md` placeholder.** S18, S19, S20, S21 — 4 consecutive review acknowledgments. T115 added enforcement for a *real* workspace-isolation rule but the doc still says "[Name]" for Invariants 1–2 and the verification clause for Invariant 5 still references the non-existent `workspace_config.assert_workspace_boundary()` rather than the new hook.

- **No round-trip integration test for the SR pipeline.** S20 Test Gap #5 flagged this; S21 added unit tests for the individual fixes but no end-to-end test. As more SR-pipeline scripts accrete (raise → promote → close → resolve), unit-test-only coverage will miss the cross-script regressions.


