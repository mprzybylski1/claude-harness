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


