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

# Opus Review — S22 2026-05-28

## Invariant Violations

None. Invariant 4 (fail-closed) is strengthened by T125 (`_check_cross_repo_files` refuses cross-repo `--files` rather than silent split-staging) and T124 (large-asset stripping prevents Opus context from silently truncating signal). Invariant 5 unchanged from S21 — workspace-isolation enforcement holds.

The `docs/architecture_invariants.md` placeholder is now 5 consecutive review acknowledgments (S18–S22); T131 was opened this session to address it. Treating as tracked, not carry-forward.

## Architectural Concerns

1. **Divergent twins: `_workspace_sessions_md` + `_current_session` now exist in both `scripts/tools/surface_workspace_concerns.py:32-98` and `scripts/tools/raise_for_harness.py:35-95` with opposite failure semantics.** [High impact, regression of S21 Concern #1] T126 introduced the pair in `surface_workspace_concerns.py` and the new `_current_session(sessions_md)` *intentionally does not* fall back to harness session when `sessions_md is None` (returns `None`, archive commit omits session ID). The pre-existing pair in `raise_for_harness.py` (T116) *does* silently fall back to harness session number when `internal/sessions.md` is missing — exactly the audit-trail-lying behaviour S21 Concern #1 flagged. After S22 the codebase ships two same-named helpers with contradictory safety stances. Until T128 consolidates them into `session_lookup`, the next caller can't tell which behavior they're getting from the name. Fix order: (a) make `raise_for_harness._current_session` fail-closed too (warn-and-omit or warn-and-error), (b) then consolidate via T128. Doing T128 first locks in whichever semantics the consolidator picks without an explicit decision.

2. **`scripts/hooks/check_cross_layer_writes.py` `__harness__` sentinel collision still unaddressed (S21 Concern #2, 2-session carry-forward).** No diff in S22 touches `workspace.py` create-validation; a workspace slug `__harness__` would still be accepted, and the hook would treat that workspace's session as harness-root, permitting writes to any `workspaces/*/internal/` including its own. Trivial fix (reserved-slug list in `workspace.py`); the cost grows with every session that ships the sentinel pattern without a guard.

3. **`scripts/tools/close_ticket.py:556-616` `_check_cross_repo_files` silently skips paths that aren't inside any git repo.** [Diff confirms; low-moderate impact] The check is `if ef_root is not None and ef_root != ticket_root` — a `--files` path outside all git repos (typo, accidentally absolute path to `/tmp`, a deleted file's stale path) bypasses the cross-repo guard entirely. Downstream `_git_stage` will fail with a "not in a repo" error, but only *after* other cross-repo siblings have already been rejected, producing confusing partial-validation output. Either treat `ef_root is None` as its own explicit error class with a clear "path not in any git repo" message, or fold the check into `_git_stage` so the validation is single-pass. Less urgent than #1 but the new guard widens the surface where this matters.

4. **`scripts/tools/surface_workspace_concerns.py:262-282` auto-commit prints the SAME warning to stdout AND stderr on failure.** [Diff confirms; cosmetic but real] The `print(warning); print(warning, file=sys.stderr)` pattern intentionally duplicates the message — comment says "stdout — visible in session-start briefing." This means in a normal terminal run the operator sees the multi-line warning twice in a row (stdout and stderr interleave on most terminals), which is confusing UX and looks like a script bug. Pick one: if session-start truly only reads stdout, send only there; if both are read, gate on `sys.stdout.isatty()` to avoid duplication when they merge. The duplication was an impl-review fix per the session log, so this is a known trade-off — but worth revisiting once the session-start consumer behavior is documented.

5. **`scripts/tools/prepare_opus_context.py:55-58` `_LARGE_ASSET_EXTS` includes `.json` and `.yaml` — risk of stripping legitimate config diffs.** [Diff suggests; low impact] T124 lists `.txt, .json, .csv, .plist, .xml, .yaml, .yml, .lock` and triggers at 1000 lines. A monster `tsconfig.json`, `package.json` lockfile, or a workspace `workspace.yaml` schema migration could legitimately exceed 1000 lines and *should* appear in the Opus review. Threshold + extension is a coarse filter; a path-based allowlist (e.g. only strip data files in `data/`, `resources/`, `fixtures/`, plus `*-lock.{json,yaml}`) would catch the actual sowpods.txt failure mode without risking stripped governance configs. Mitigation: stat section still names the file, so Opus knows it changed; this is about *content review* getting silently skipped.

6. **`scripts/tools/raise_for_harness.py:97-114` `_yaml_scalar` enumerates an incomplete set of YAML-unsafe constructs.** [Diff confirms; low impact] The helper quotes when title contains `": "`, trailing `:`, `" #"`, or starts with a YAML-reserved char. Misses: titles that parse as YAML booleans/null (`"yes"`, `"no"`, `"on"`, `"off"`, `"null"`), numeric-looking strings (`"1.0"`, `"0x10"`), and strings starting with whitespace inside a value (caught by `!= value.strip()`, OK). Production risk is small — titles are descriptive prose, not the literal string "yes" — but the safer shape is to always quote (defensive) or to delegate to a real YAML emitter (`yaml.dump({"title": value})` and lift the line). The bug that motivated T123 was "didn't quote at all"; the fix narrows that to "quotes most cases." The cheap robust fix is "always quote."

## Suggested Next Session Focus

1. **Resolve the divergent-twins safety asymmetry before T128 consolidates them (Concern #1).** ~10 LoC + 1 test. Make `raise_for_harness._current_session` fail-closed (warn-and-omit, matching `surface_workspace_concerns.py`) before T128 picks a consolidator. Otherwise T128 silently locks in whichever semantics the consolidator chooses without an explicit decision. The audit-trail-lying mode S21 Concern #1 flagged is still live in `raise_for_harness.py`.

2. **T131: reconcile `architecture_invariants.md` (5-session carry-forward).** This is the longest-running unresolved Opus finding in the project. With T115 (Invariant 5 enforcement at hook) and T120 (fail-closed close-the-loop) now shipped, the doc has concrete enforcement to reference. Either fill in Invariants 1–2 with real harness rules or delete the placeholder and point Opus reviews at a different schema-of-record. Currently the "Invariant Violations" section of every review is half-empty by construction.

3. **Reject `__harness__` as a workspace slug (S21 Concern #2, 2-session carry-forward).** ~5 LoC + 1 test in `scripts/tools/workspace.py`. Cheap to fix now, expensive to fix after a workspace named `__harness__` exists in the wild.

# Opus Review — S23 2026-05-28

Scope: closed T127–T134 (8 tickets) — full Opus S22 backlog plus T132–T134 opened and closed in-session. Net: new `session_lookup.py` consolidator (T128) absorbs 5 callers; `raise_for_harness._current_session` now fail-closes on missing workspace `sessions.md` (T132); `architecture_invariants.md` finally rewritten with grep-anchored rules and renumbered (Invariant 5 → 4) with name-anchor replacement everywhere live code references the old number (T131); `_extract_proposed_change_acs` carries SR bullets into ticket ACs (T127); `list_raised_concerns.py` buckets unparseable SRs into a dedicated section (T130); Stop hook gains `run_active_work_check` to catch the session-close prepend regression (T134, opened from the workflow-review that found S22→S23 produced an orphan in the Active Work section); session-close skill rewritten to specify REPLACE semantics for Active Work (T133). ~480 LoC production + ~310 LoC tests; 455 passing (+15 net). Strong follow-through — every S22 suggested item landed plus two self-found tickets. A small set of brittleness edges remain in T134's check and T127's section detection.

## Invariant Violations

None.

Checking the new Inv 1–4 against the diff:
- **Inv 1 (workspace↔harness session-number separation):** verification grep #1 (`current_session.py|--sessions` in scripts/tools/*.py) holds — `session_lookup.call_current_session` routes `--sessions PATH` when `sessions_md is not None`, and all four named callers (`raise_for_harness.py`, `surface_workspace_concerns.py`, `create_ticket.py`, `close_ticket.py`) construct the workspace path via `resolve_workspace_sessions_md` or the `internal` argument. Verification grep #2 (`sessions_md is None` in both `raise_for_harness.py` and `surface_workspace_concerns.py`) holds — `raise_for_harness._current_session` exits 2, `surface_workspace_concerns._current_session` returns None. The two semantics are intentionally divergent (tracked-field vs commit-message) and documented in the new Inv 3 verification.
- **Inv 2 (session-type declaration required):** no S23 change touches `_STATE_FILE`, `_HARNESS_PROTECTED`, or `STATE_UNDECLARED` (T131 follow-up renamed Invariant 5 references in this file, but did not alter enforcement). Tests in `tests/test_check_cross_layer_writes.py` were touched only for the name-anchor rename.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** verification grep `sys.exit(2)` in `raise_for_harness.py` + `close_ticket.py` holds — T132 added one in `raise_for_harness._current_session`, T125 from S22 left one in `close_ticket._check_cross_repo_files`. Verification test `tests/test_raise_for_harness.py::TestSessionIdSource::test_refuses_to_fall_back_when_internal_sessions_md_missing` is named in the diff stat (test_raise_for_harness.py: +34 lines, inverted broken-fallback test per the session log).
- **Inv 4 (workspace isolation):** verification grep `_workspace_internal_slug|may not write to other workspace` in `scripts/hooks/check_cross_layer_writes.py` holds — diff only changes the user-visible error string from "Invariant 5 (workspace isolation)" to "the Workspace Isolation invariant".

**Opus S22 Concern #2 retired.** Implementer is correct: `_slug_valid` rejects `__harness__`. The S21/S22 Opus reviews both flagged this as low-confidence (S21: "Diff suggests; low confidence — namespace hygiene"; S22 just carried it forward without re-verifying). Diff confirms the implementer reinvestigated and the regex `^[a-z0-9][a-z0-9-]*$` excludes leading underscore. Removed from carry-forwards.

The placeholder-invariants carry-forward (S18–S22, 5 reviews) is also retired — T131 replaced placeholders with concrete grep-anchored rules and the per-invariant verification commands are reproducible.

## Architectural Concerns

1. **`scripts/hooks/check_session_log.py:155` — `active_work.count("Tickets closed:")` is a substring search with two foreseeable false-positive vectors.** [Medium impact] (a) Narrative content inside Active Work that names the literal phrase — e.g. "Tickets closed: line was duplicated by the bug T134 fixes" — would inflate the count and block session-close. The implementer hit this exact failure mode in S23 per the prompt. (b) A future session author who writes prose like "Tickets closed in earlier sessions:" would also trip the check. Tighter shape: anchor at line start with a regex `re.compile(r"^Tickets closed:", re.MULTILINE)` so only the canonical reporting line counts, not narrative substrings. As-is, the check punishes any session that talks about itself at the meta level — including this Opus review section if it appeared inside Active Work. Fix: replace `.count(...)` with `len(re.findall(r"^Tickets closed:", active_work, re.MULTILINE))`.

2. **`scripts/hooks/check_session_log.py:124-131` — `_extract_active_work_section` terminates at the first `\n---` found in the body.** [Medium impact, latent] The section terminator search picks whichever comes first between `\n## ` and `\n---`. If a session author writes a thematic break (`---`) inside their Active Work narrative (e.g. between "Files changed" and "Tests"), the function silently truncates and the integrity check operates on a partial section — drift after the truncation point goes undetected. Also: if Active Work ever contains a fenced code block whose body contains `---` (YAML frontmatter sample, hook config snippet, the embedded ticket template), the section ends mid-fence. The Stop hook then fails open for everything past the cut. Fix: scan for `\n## ` only (the next H2 is the canonical terminator since `## Session Log` always follows); the `---` arm exists because of the current docs/sessions.md layout where `---` precedes `## Session Log`, but H2 is the more reliable anchor and `## Session Log` will always be there in a well-formed file.

3. **`scripts/tools/promote_raised_concern.py:115` — `## Proposed change` matched only by exact lowercased equality.** [Low impact, brittleness] `stripped.lower() == "## proposed change"` will fail for any reasonable variant: `## Proposed change:`, `## Proposed Changes` (plural), `## Proposed change (urgent)`, trailing whitespace beyond `.strip()`'s trim. When the match fails, `_extract_proposed_change_acs` silently returns `[]` and `create_ticket.py` falls back to the default `- [ ] (fill in)` placeholder — same as if the SR had no Proposed change section. Two failure modes converge into one observable behavior, so the operator can't tell from outside which case they're in. Loosen to `stripped.lower().rstrip(":").startswith("## proposed change")` or emit a debug log when the section is found but yields zero items.

4. **`scripts/tools/session_lookup.py:35-37` — bare `except Exception` for YAML parse errors with a comment "yaml.YAMLError and unexpected parse errors".** [Low impact] The `import yaml` is inside the try block (line 29), so an `ImportError` on `yaml` import would fall through `except ImportError` correctly, but a `KeyError`/`AttributeError` inside `cfg.get("docs_path")` would also be swallowed by the bare-Exception arm with a misleading "could not parse" message. Tighten to `except yaml.YAMLError` and let unexpected errors crash visibly. The risk surface is small (we already validated `cfg` is from `yaml.safe_load`), but defensive bare-Exception in shared infra is the kind of thing that hides a real bug for sessions.

5. **`scripts/tools/list_raised_concerns.py:67` — `sorted(raised_dir.glob("*.md"))` introduces a deterministic order, but `_severity_key` `sort` was already applied per-workspace.** [Cosmetic, low impact] The new `sorted()` call at glob time is good (filename-deterministic) but the in-workspace `items.sort(key=_severity_key)` is INSIDE the for-loop on line 80, so it re-sorts after every item is appended. That's O(N² log N) for a per-workspace list — fine at current scale (single-digit SRs per workspace) but a code-smell pattern. Move `items.sort` outside the loop. Diff confirms this is pre-existing (the `items.sort` line wasn't changed in T130), so it's not a new defect, but T130 modified surrounding logic without fixing it.

6. **`scripts/tools/raise_for_harness.py:79` — the fail-closed error message names `workspaces/<slug>/internal/sessions.md` as the lookup target even when `workspace.yaml` declares a `docs_path` override.** [Low impact] When `resolve_workspace_sessions_md` returns None because the `docs_path`-overridden path is missing, the error message in `_current_session` interpolates the *default* `ROOT / workspaces / slug / internal / sessions.md`, not the actual override target the user configured. Operator chases the wrong path. Either thread the resolved-but-missing path through, or have `resolve_workspace_sessions_md` return a sentinel-or-pair distinguishing "no yaml override, default missing" from "yaml override declared, override missing". Diff confirms only the slug is passed into `_current_session`, so the error path doesn't know which target failed.

## Suggested Next Session Focus

1. **Tighten the T134 substring check (Concern #1) and the section terminator (Concern #2).** ~10 LoC + 2 tests. These are coupled: both are brittleness in the same new hook check that the implementer already hit a false positive on. Use `re.MULTILINE` anchored matches for "Tickets closed:" and prefer `## ` over `---` as the section terminator. The hook is the last line of defense against the prepend regression — when it false-positives, operators will be tempted to bypass it; when it false-negatives, the regression that motivated T134 returns silently.

2. **Loosen `_extract_proposed_change_acs` section matcher (Concern #3).** ~3 LoC + 1 test. Variants of "## Proposed Change" / trailing colon / pluralization should all match. The current strict match makes the new T127 capability silently no-op on most real SRs that don't use the exact-case canonical heading.

3. **Lock the docs_path-aware error message in `raise_for_harness._current_session` (Concern #6).** ~5 LoC. If we're going to fail closed and tell the user which file to create, name the actual file. Currently misleads when `docs_path` is in play. Low priority but easy.

No multi-session carry-forwards remain after S23. Both the placeholder-invariants and the `__harness__` slug carry-forwards retired this session — first time in 6 reviews the carry-forward list is empty.

---

# Static Analysis — S24 2026-05-30

Docs-only session (SR triage + analysis). No code changed; full Opus review skipped per protocol.

```
PASS  30 test files compile cleanly (no SyntaxError)
PASS  no datetime.utcnow() in production code
PASS  9/9 bash blocks in SKILL.md files syntax-valid
All 3 checks PASS.
```

No new findings. S23 Opus carry-forwards remain as the Suggested Next Session Focus above.

---

# Opus Review — S25 2026-05-31

Scope: closed T135/T136/T137/T138/T139 — the full scrabble-score SR-008/009/010/011
workspace-blind-tooling sweep. Net: telemetry attribution rewritten from per-file-path
(T057) to active-session via `workspace_config.read_session_state` + a new
`claude_session_uuid` live join key (T137); `analyze_tool_log` gains a `(workspace,
session)` pair filter with gated auto-detect (T137); `create_ticket._next_id` scoped
per-layer (T135); `generate_ticket_index` fail-closes on bare workspace/undeclared
invocation (T136); new `run_hook.sh` wrapper resolves hook paths cwd-independently via
`$CLAUDE_PROJECT_DIR` + `$0` (T138); `raise_for_harness --session` bypasses the
last-logged+1 off-by-one during close (T139). ~1556 insertions / 547 deletions across
32 files; 477 tests pass (+22 net). Clean, well-documented sweep — every SR in the
batch landed, and the implementer left honest in-code notes on the residual skew and
the duplicated tri-state reader. Two spin-outs (T140/T141) correctly deferred.

## Invariant Violations

None.

Per-invariant verification against the S25 diff:
- **Inv 1 (workspace↔harness session-number separation):** grep #1 holds —
  `close_ticket.py:221` and `create_ticket.py:117` both route `--sessions
  <internal>/sessions.md`; `session_lookup.py:42-46` is the single consolidator that
  appends `--sessions PATH` only when given a workspace path. T135's `_next_id(internal)`
  rework keeps the per-layer counter (its docstring explicitly cites the
  `current_session.py --sessions` per-layer model). No harness `S<N>` is written into
  workspace state and vice versa in the diff.
- **Inv 2 (session-type declaration required):** grep #2 holds — the
  `check_cross_layer_writes` matcher is still registered on `Edit|Write`
  (settings.json:34), now dispatched through `run_hook.sh`. The hook body is unchanged:
  `_STATE_FILE`, `_HARNESS_PROTECTED`, `STATE_UNDECLARED` all present, `sys.exit(2)` at
  line 96 on the mismatch/undeclared path. The new T136 `workspace_config.read_session_state`
  reads the SAME `.claude/.active_workspace` tri-state (see Concern #2). Enforcement logic
  untouched — but its *invocation wrapper* changed; see Concern #1.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** grep #3 holds —
  `raise_for_harness.py:194` exits 2 on a malformed `--session` value (T139's new flag
  validates `S\d+` before stamping the tracked `raised:` field, so the explicit-value
  path can't smuggle garbage in), plus the pre-existing exits at 83/88. `close_ticket.py`
  retains its cross-repo guards (12 `sys.exit(2)` sites). T136's `generate_ticket_index`
  bare-invocation path also fail-closes (`sys.exit(2)`) for workspace/undeclared sessions
  rather than overwriting the harness INDEX — a new, correct application of this invariant.
- **Inv 4 (workspace isolation):** grep #4 holds — `check_cross_layer_writes.py:155`
  still blocks workspace-A→workspace-B `internal/` writes via `_workspace_internal_slug`.
  No diff change to the isolation logic; same wrapper caveat as Inv 2 (Concern #1).

Test suite: `477 passed` (ran with `--ignore=tests/test_workflow_orchestrator.py` per
the prompt).

## Architectural Concerns

1. **T138 inverted the enforcement hook's failure mode from fail-closed to fail-open
   — `scripts/hooks/run_hook.sh:31` + `.claude/settings.json:34`.** [Medium impact,
   defense-in-depth gap] T138 correctly fixed the SR-011 deadlock (cwd drifting into a
   workspace repo made `git rev-parse --show-toplevel` resolve to a repo with no harness
   hooks → `python3: can't open file` → exit 2 → every tool blocked). The fix —
   `$CLAUDE_PROJECT_DIR` to locate the wrapper, `$0`-relative to locate the script — is
   sound, and a *deliberate* `exit 2` still propagates correctly (`exec python3` replaces
   the process, so the python exit code is returned verbatim; I verified this). But the
   *script-not-found* path now changes behavior asymmetrically by hook type. Pre-T138, a
   missing/unresolvable hook script produced a non-zero exit → the write was **blocked**.
   Post-T138, `[ -f "$script" ] || exit 0` (and the settings.json `|| exit 0`) means a
   missing script → **silent exit 0** → write proceeds. For `log_tool_usage` and
   `regenerate_ticket_index` this fail-open is correct (best-effort telemetry/index must
   never block a tool). But the SAME blanket fail-open is applied to
   `check_cross_layer_writes` — the *enforcer* of Invariant 2 and Invariant 4. If that
   one script ever fails to resolve (rename, partial checkout, perms, a future refactor
   that moves it), workspace isolation silently vanishes instead of blocking. In normal
   operation the `$0`-relative resolution makes the script always present, so this is a
   defense-in-depth gap rather than an active hole — but the harness's own threat model
   (Inv 4: "cross-workspace data leakage is a confidentiality violation") is exactly the
   case where you want loud failure. Recommendation: differentiate enforcement hooks from
   best-effort hooks. The enforcement hooks (`check_cross_layer_writes`, and arguably
   `check_ticket_acs`/`check_fix_commit_has_code`) should fail closed — or at minimum emit
   a visible stderr warning AND exit 2 — when their script can't be resolved; only the
   telemetry/index hooks should silently `exit 0`. A small allowlist of fail-open hook
   names in `run_hook.sh`, defaulting to fail-closed, would express the policy in one place.

2. **Two parallel copies of the `.active_workspace` tri-state reader now exist, and one
   of them is the Inv 2/4 enforcer.** [Low-Medium impact, tracked debt] T136 added
   `workspace_config.read_session_state()` (workspace_config.py:147-163), which the
   implementer's own comment (lines 131-132) notes "Mirrors the tri-state read in
   `scripts/hooks/check_cross_layer_writes.py`; a future pass could have the hook import
   these instead of keeping its own copy." The hook's copy is at
   check_cross_layer_writes.py:34-57. They agree today (same sentinel `__harness__`, same
   `.strip()`, same empty→undeclared rule), but they are the attribution authority (which
   layer a telemetry record / index / SR is stamped with) and the enforcement authority
   (which writes get blocked). If they ever drift — a future fourth state, different
   whitespace handling, a sentinel rename done in one file — the tool that *attributes* and
   the hook that *blocks* would disagree about what layer the session is, and the
   disagreement would be silent. The implementer flagged this honestly as deferred debt,
   so this is tracked, not a missed defect. Recommendation: have the hook import
   `workspace_config.read_session_state` (the hook already manipulates `sys.path` for ROOT;
   the import is cheap and fail-open-able), collapsing to a single source of truth. T136's
   note already anticipates this — promote it to a ticket so it doesn't rot.

3. **`claude_session_uuid` join key rests on an unverified Claude Code internal
   assumption — `log_tool_usage.py:266`.** [Low impact] The new field stores
   `os.environ.get("CLAUDE_CODE_SESSION_ID", "")` on the documented premise that this value
   "IS the native JSONL transcript filename" (line 23). If that premise is wrong (env var
   unset in the hook subshell — note CLAUDE.md records `$CLAUDE_PROJECT_DIR` was *empty* in
   a hook subshell as of S3, later found present on 2.1.158; env availability in hooks has
   bitten this harness before — or the filename≠UUID), the field is silently dead weight: it
   degrades to `""` and the deferred T141 join finds nothing. Low risk because it fails
   gracefully and the join is explicitly deferred. Recommendation: before building T141,
   empirically verify the env var is populated in the `log_tool_usage` subshell AND that a
   live `.git/session_tool_log.jsonl` record's uuid matches an actual transcript filename
   on disk. One `/verify`-style check, not a code change. If it's empty in practice, drop
   the field rather than carry a dead join key.

Note (acknowledged, not a concern): the `_session_from_sessions_md` last-logged+1
off-by-one (log_tool_usage.py docstring) is pre-existing (path-based stamping had it too),
documented in-code, and explicitly deferred — the `claude_session_uuid` field is the
intended future reconciliation key (T141). Correctly out of scope for T137.

## Suggested Next Session Focus

1. **Differentiate enforcement vs. best-effort hooks in `run_hook.sh` (Concern #1).**
   ~8 LoC + 2 tests (script-present → runs; enforcement-script-missing → exit 2 + stderr;
   best-effort-script-missing → exit 0). This is the only Medium finding and it sits
   directly on the Inv 2/4 trust boundary that T138 touched. The existing
   `tests/test_hook_command_resolution.py` is the natural home for the cases.

2. **Collapse the duplicated tri-state reader (Concern #2).** Promote workspace_config.py's
   line 131-132 note to a ticket and have `check_cross_layer_writes.py` import
   `read_session_state`. ~10 LoC net negative. Single source of truth for the
   attribute-vs-block layer decision; closes the silent-divergence risk before a fourth
   state or a rename introduces it.

3. **Verify the `claude_session_uuid` premise before investing in T141 (Concern #3).**
   A read-only `/verify`: confirm `CLAUDE_CODE_SESSION_ID` is populated in the hook subshell
   and that a logged uuid maps to a real transcript filename. Cheap insurance against
   building the T141 join on a `""` field.

No multi-session carry-forwards remain (S23's three items were the carry-forward and S24
was docs-only). All three S25 items are net-new from this session's diff.

---

# Opus Review — S27 2026-05-31

Scope: promoted SR-012/SR-013 → closed T147 (`close_ticket.py --commit`) and T148
(`create_ticket.py --problem`); impl-review added an index-clean guard + fail-closed
`_apply_problem`; `/simplify` deduplicated test boilerplate into a new `tests/conftest.py`
(net –226 test lines). The feature surface is small and well-factored: `--commit` runs
`git commit` after staging, refusing (exit 2) on multi-root spans and on an index that
holds staged changes beyond what close_ticket staged; `--problem` fills the `## Problem`
placeholder, failing closed (exit 1) if the placeholder is absent. The helper extraction
(`_ac_section_bounds`, `_resolution_section` reuse, `_rel`, module-level `defaultdict`) is
clean. One real test gap on the headline feature (Concern #1); everything else holds.

## Invariant Violations

None.

Per-invariant verification against the S27 diff:
- **Inv 1 (workspace↔harness session-number separation):** Holds. The one new write
  surface is `commit_msg = f"{prefix} {title}"` (close_ticket.py:858) — `prefix` is
  `fix(T###):`/`docs(T###):` from `_commit_prefix`, `title` is the ticket frontmatter
  title; no session ID is embedded, so `--commit` cannot leak an `S<N>` into a commit
  message. `--sessions` routing is untouched. `create_ticket --problem` only substitutes
  body text and does not touch the session-ID lookup.
- **Inv 2 (session-type declaration required):** Holds, unchanged. No S27 change touches
  `.claude/settings.json`, `check_cross_layer_writes.py`, or `workspace_config.read_session_state`.
  Note: both new write paths bypass the Edit/Write hook because they write via `os.replace`
  / `git`, but that is the pre-existing tool-write model (same as every other close/create
  operation) — not a regression introduced this session.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** Holds, and *strengthened*. The
  new `_refuse_multi_root_commit` (close_ticket.py:174) exits 2 when staged paths span >1
  git root before any commit — a direct extension of the T125 cross-repo case the invariant
  names. `_check_index_clean` (close_ticket.py:188) adds a further exit-2 site: a bare `git
  commit` would fold any pre-existing staged change into the ticket commit, so it refuses
  unless the index contains only the paths close_ticket staged. `git status` failure /
  non-zero also exits 2 (no silent proceed). `create_ticket._apply_problem` exits 1 — not 2 —
  when the placeholder is missing; correct, since create_ticket is not a tracked-audit-state
  write at that point and exit 1 simply aborts the create.
- **Inv 4 (workspace isolation):** Holds, unchanged. No diff touch to `_workspace_internal_slug`
  or `assert_workspace_boundary`. The multi-root refusal incidentally reinforces it: a close
  whose staged set spans a workspace repo and the harness repo cannot be auto-committed.

## Architectural Concerns

1. **`--commit` — the session's headline feature — has zero end-to-end test coverage.**
   [Medium impact, test gap on a new git-mutating path] `tests/test_close_ticket_commit.py`
   is entirely mocked unit tests of the helpers in isolation: `_commit_prefix` (pure),
   `_collect_staged_roots` (patches `_git_root_for`), `_refuse_multi_root_commit` (called
   directly), `_check_index_clean` (patches `subprocess.run` with canned porcelain). Nothing
   in the suite invokes `close_ticket.py --commit` against a real temp repo. sessions.md
   records that the refactor *deleted* `TestCommitMainPath` as "tested mocks" — so the
   `main()` composition (close_ticket.py:868-881) that wires `_collect_staged_roots` →
   `_refuse_multi_root_commit` → `_check_index_clean` → real `git commit` and prints
   `Committed:` is now untested. `grep -rn -- "--commit" tests/` returns only docstring
   lines. The guards are individually correct, but their integration in the commit path —
   the part that actually mutates HEAD — has no coverage, on the one feature this session
   shipped to do exactly that. The masking risk is concrete: a wiring bug (wrong `staged_paths`
   passed to `_check_index_clean`, `commit_msg` not threaded, `git -C git_root` root mismatch)
   would pass every existing test. Fix: one integration test using the new conftest helpers
   (`make_harness_tree` + `run_close_ticket(..., "--files", "x.py", "--commit")`) asserting
   `git rev-parse HEAD` advanced and `git log -1 --format=%s` equals `fix(T###): <title>`,
   plus a second asserting `--commit` with a pre-existing unrelated staged file exits non-zero
   and leaves HEAD unmoved. ~15 lines; the conftest scaffolding for it already exists.

## Notes (decisions, not defects)

- **SR-013 AC#3 vs. implementation — `--problem --ac` is not fully "close-ready."** SR-013
  AC#3 reads "a single create invocation produces a close-ready ticket (no unchecked-AC ...
  residue)." The implementation (and `test_close_ticket_commit`'s own docstring) deliberately
  leaves `- [ ]` boxes unchecked — "criteria to verify, not auto-ticked." So a
  `create --problem --ac` ticket still needs `--tick-acs`/`--force` at close. This is the
  correct call (auto-ticking ACs at create time would defeat the AC gate), but it diverges
  from the AC's literal wording. Recording as a decision so it isn't re-litigated, not a bug.
- **No carry-forwards.** All three S26 concerns were retired during S26 close, before the
  S27 baseline (3c42a45): Concern #1 (`--append` fresh-ticket guard) fixed in `42e7512`;
  Concern #2 (`\n##\s` non-fence-aware terminator) commented in `3bc8169`; Concern #3
  (`--harness` bypass) was a recorded decision. The live `close_ticket.py` still contains
  `_resolution_section` with the `\n##\s` terminator and the append guard, but both are
  addressed — not open.

## Suggested Next Session Focus

1. **Add end-to-end `--commit` coverage (Concern #1).** Two integration tests via the new
   conftest helpers: (a) `--files x.py --commit` advances HEAD with `fix(T###): <title>`;
   (b) `--commit` with an unrelated staged file exits 2 and leaves HEAD unmoved. ~15 LoC.
   This is the only Medium finding and it closes a coverage hole on the session's one
   git-mutating feature.
2. **Pick up a deferred ticket** — T141 (telemetry↔transcript join, deferred under YAGNI
   since S25) or T146 (cwd-drift fragility in `python scripts/tools/X.py` invocations).
   T146 sits closest to the harness trust boundary that recent sessions have been hardening.

---

# Opus Review — S28 2026-06-01 (static analysis, docs session)

**Session type:** docs-only — portfolio layer creation, app workspace scaffolding, idea research. No code changes.
**Static analysis:** 3/3 PASS — 35 test files compile cleanly, no `datetime.utcnow()`, all 9 CLAUDE.md bash blocks valid.
**Stale `.active_workspace` at close:** Found `scrabble-score` in `.active_workspace` at session-close time, blocking harness docs writes. Reset manually to `__harness__`. This is a recurring risk — a crashed or improperly-closed workspace session leaves stale state that blocks subsequent harness-root closes. Worth a low-priority ticket: session-start should set `.active_workspace` and session-close should reset it atomically, so stale state cannot persist across sessions.

---

# Opus Review — S26 2026-05-31

Scope: cleared the full S25 Opus backlog and both spin-outs — closed T142/T143/T140/T144/T145,
verified+deferred T141, opened T146. Net: `run_hook.sh` keeps its default fail-OPEN but gains
an explicit `FAIL_CLOSED` allowlist (exactly `check_cross_layer_writes`) so a missing enforcement
script stderr-warns + exit-2-blocks (T142, directly answering S25 Concern #1); the cross-layer
hook drops its private `_read_session_state`/`_HARNESS_SENTINEL` and imports
`workspace_config.read_session_state` as the single source of truth, mapping import failure to
exit 2 (T143, S25 Concern #2); `create_ticket.py` bare invocation is now session-aware —
fail-closed for workspace/undeclared, with a new explicit `--harness` bypass for programmatic
callers (T140, Inv 3 extension); `close_ticket.py` gains `--append` to preserve work-authored
Resolution content (T144) and a clearer no-placeholder error (T145); T141's join-key premise was
verified and deferred under YAGNI (S25 Concern #3 retired). One impl-review fix updated Invariant
2's verification grep for the T143 refactor. ~894 insertions / 74 deletions; static analysis
clean (33 test files compile, no `datetime.utcnow()`, 9/9 SKILL bash blocks valid). A focused,
high-discipline session — every S25 concern was retired at its root, and the T142 narrowing
(3 hooks → 1) is backed by an explicit matcher-by-matcher deadlock analysis rather than a
blanket policy. One real defect in the new `--append` path (Concern #1 below) and a recurring
section-terminator pattern (Concern #2).

## Invariant Violations

None.

Per-invariant verification against the S26 diff:
- **Inv 1 (workspace↔harness session-number separation):** Holds. No S26 change touches the
  `--sessions` routing in `create_ticket.py`/`close_ticket.py` (T140 changed only *layer
  selection*, not the session-ID lookup). The `--harness` bypass question resolves cleanly:
  `_current_session(internal=None)` reads the **harness** `sessions.md`, so a `create_ticket
  --harness` invocation stamps a **harness** `S<N>` into a **harness** ticket — no cross-layer
  number leak even if the flag is misused from a workspace session.
- **Inv 2 (session-type declaration required):** Holds, and the verification grep was correctly
  updated this session to match the refactor. First grep (`read_session_state|STATE_UNDECLARED`):
  diff confirms the hook imports `workspace_config as _wc`, re-exports `STATE_UNDECLARED`/
  `STATE_HARNESS`/`STATE_WORKSPACE` from it (lines 86-88), and calls `_wc.read_session_state(ROOT)`
  at the decision point (replacing the deleted private `_read_session_state`). Second grep
  (`_HARNESS_PROTECTED|sys\.exit`): `_HARNESS_PROTECTED` list is intact; `sys.exit(2)` now also
  guards the import-failure path (line 84), in addition to the unchanged undeclared/mismatch
  blocking paths (`main()` body below line 125 is untouched). The matcher is still `Edit|Write`
  (settings.json unchanged this session). The S25 Concern #2 silent-divergence risk is closed:
  one reader, with a test (`test_hook_has_no_private_tri_state_reader`) asserting the private copy
  and `_HARNESS_SENTINEL` are gone.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** Holds. The verification grep's two
  named tools (`raise_for_harness.py`, `close_ticket.py`) are untouched by S26 in their boundary
  exits, and `close_ticket.py`'s new `_append_resolution` adds *more* exit-2 sites (no
  Resolution header → exit 2; empty/placeholder-only section under `--append` → exit 2). T140
  extends the same principle to a new surface: `create_ticket._resolve_bare_layer` exits 2 for
  both `STATE_WORKSPACE` (refuse to create a harness ticket from a workspace session) and
  `STATE_UNDECLARED`, returning the harness layer only for an explicit `STATE_HARNESS` — a
  correct, idiomatic application of fail-closed-on-ambiguity that mirrors T136's
  `generate_ticket_index`.
- **Inv 4 (workspace isolation):** Holds. The `_workspace_internal_slug` / "may not write to
  other workspace" logic in `check_cross_layer_writes.py` is unchanged by the T143 refactor (the
  diff touches only the tri-state *reader* extraction and the import-failure guard, not the
  cross-workspace block). The run_hook.sh `FAIL_CLOSED` allowlist now makes a missing
  `check_cross_layer_writes` script fail closed, *strengthening* this invariant's enforcement
  relative to S25 (the S25 Concern #1 defense-in-depth gap).

## Fail-closed direction audit (priority-2 check)

Both new fail-closed directions are exit 2 (block), not exit 1 (non-blocking), which is the
correct and load-bearing distinction:
- `run_hook.sh`: missing FAIL_CLOSED script → `exit 2` (lines 173-178). The `case
  "$FAIL_CLOSED" in *" $name "*` match is space-padded on both the list (`" check_cross_layer_writes "`)
  and the pattern, so a hook named e.g. `check_cross` cannot substring-collide into the list.
  Confirmed correct.
- `check_cross_layer_writes.py`: import failure → `sys.exit(2)` with a recovery-pointing stderr
  message (lines 78-84). The in-code comment correctly states the rationale: Claude Code treats
  exit 2 as a block but *any other* non-zero (an uncaught `ImportError` → exit 1) as non-blocking
  → the tool proceeds → fail OPEN. The `except Exception` → exit 2 maps that correctly. Confirmed.
- T142 narrowing (3 → 1 hooks) is sound: `check_ticket_acs` matches `Edit|Write|Bash`, so
  fail-closing it would block every recovery surface (the SR-011/T138 deadlock class).
  `check_cross_layer_writes` matches `Edit|Write` only, leaving Bash (`git checkout`) as a
  recovery surface. Both fail-closed sites point the operator at that Bash recovery in stderr.

## `--harness` bypass audit (priority-2 check)

The `--harness` flag is an unconditional bypass of the session-state check (sets `internal = None`,
the harness layer). It does **not** open a separation hole in the Invariant sense: stamping is
correct (harness `S<N>` into a harness ticket, per Inv 1 above), and the flag is an explicit,
non-default override — the *bare* path fails closed, so nothing silently routes a workspace
session's ticket to harness. The residual gap is policy-vs-mechanism, not invariant: because
`create_ticket` writes via plain `open()` (not Edit/Write), the PreToolUse cross-layer hook cannot
catch a misused `--harness`, so the *only* guard against a workspace session doing harness ticket
work is "don't pass the flag." That is acceptable for a programmatic-caller escape hatch
(`promote_raised_concern.py` is the sole intended user and always creates harness tickets), but it
is an unguarded surface — see Concern #3.

## Architectural Concerns

1. **`scripts/tools/close_ticket.py` `_append_resolution` (~L146-185, per diff hunk `@@ -143`;
   exact source line not verifiable without reading the file) — its "nothing to preserve" guard
   misses the real fresh-ticket shape; `--append` on a fresh ticket leaves the
   `(Fill in on close.)` placeholder in the closed ticket.** [Low impact (audit smudge,
   opt-in), but a confirmed correctness bug with a test that masks it] The guard is
   `if not body or re.fullmatch(r"\(Fill in on close[^)]*\)", body)`. But a *fresh* ticket's
   Resolution body is not the bare placeholder — per the embedded template (context lines
   1170-1175) it is the `> **Client-visible:**` blockquote *followed by* the placeholder.
   `body = section.strip()` therefore starts with `>`, so `re.fullmatch` against the
   `(Fill in...)` pattern returns `None`, `body` is non-empty, and the guard **does not fire**.
   `--append` then preserves the blockquote+placeholder and appends the summary after it,
   producing a closed ticket that still contains `(Fill in on close.)`. The asymmetry is the
   tell: replace-mode's `strict` regex explicitly accounts for the optional client-visible block
   (`(?:> \*\*Client-visible:\*\*.*?\n(?:> .*\n)*\n)?`), but the append guard does not. **Test
   gap (priority-4):** `test_append_errors_when_only_placeholder` uses `_ticket("(Fill in on
   close.)")` — a bare placeholder with no blockquote — so it passes while never exercising the
   shape a real ticket has. The new safety-relevant path has false-confidence coverage.
   Recommendation: reuse the same optional-blockquote-aware pattern as `strict` when deciding
   whether the section is "only the placeholder", and add a test whose Resolution body is the
   full template shape (blockquote + placeholder) under `--append`.

2. **`scripts/tools/close_ticket.py` `_resolution_section` (~L146-160, per diff hunk `@@ -143`;
   exact source line not verifiable without reading the file) — its `\n##\s` terminator is the
   same fenced-code false-terminator pattern Opus flagged in S23 Concern #2.** [Low impact,
   latent] `nxt = re.search(r"\n##\s", after)` treats the first `## ` at line start as the end of
   the Resolution section. A `## ` inside a fenced code block in the Resolution body — a commit
   message snippet, a diff hunk header is `@@` not `##` so that's safe, but a markdown sample or
   a shell heredoc with `## ` would trip it — truncates the section there, so the append lands
   before the fence and any real content after it gets shoved past the (mis-detected) section
   boundary. This is mitigated because Resolution is usually the last `##` section (`nxt` is then
   `None` and the whole tail is the section), so the bug only bites when a later `##` section
   exists *and* the Resolution body contains a fenced `## `. S23 Concern #2 flagged the identical
   shape in `_extract_active_work_section` (terminating at `\n---` inside a fence); this is a
   recurring section-parsing pattern in the same codebase. Recommendation: low priority given the
   last-section mitigation, but worth a fence-aware scan or at least a code comment naming the
   assumption, so the next section-parser author doesn't copy the pattern a third time.

3. **`scripts/tools/create_ticket.py` `main()` layer-selection branch + `_resolve_bare_layer`
   (per diff hunk `@@ -159` / `@@ -101`; exact source line not verifiable without reading the
   file) — `--harness` is an unguarded mechanism bypass; only
   `promote_raised_concern.py` is the intended caller.** [Low impact, policy-vs-mechanism] Covered
   in the bypass audit above. The flag is correct for its programmatic purpose and the bare-path
   fail-closed default is the right design, but there is no mechanism stopping an interactive
   workspace session from typing `create_ticket --harness` and writing a harness ticket (the
   `open()`-based write is invisible to the Edit/Write hook). Recommendation: no code change
   required this session — the explicit-flag-only surface is an acceptable escape hatch — but if a
   future session wants belt-and-suspenders, `--harness` could additionally assert
   `read_session_state(ROOT) != STATE_WORKSPACE` (allowing harness + undeclared, since the
   programmatic caller may run before declaration) and exit 2 otherwise. Flagging so the bypass is
   a recorded decision, not an unexamined hole.

## Cross-change interaction check (priority-5)

The five tickets touched four shared files; no seams left:
- `workspace_config.py` (T143) ↔ `check_cross_layer_writes.py` (T143): the hook now imports the
  reader the comment promised in S25; `workspace_config.py`'s deferred-debt note was replaced with
  a single-source statement. The two authorities (attribution + enforcement) now share one reader —
  the S25 Concern #2 divergence risk is closed at the source, not merely documented.
- `create_ticket.py` (T140) ↔ `promote_raised_concern.py` (T140): the promoter passes `--harness`
  so it keeps working under the new fail-closed bare default. This is necessary and correct — without
  it, promotion (a harness-layer operation often run mid-session before/independent of state) would
  have started exit-2'ing. Verified the promoter is the one caller updated.
- `run_hook.sh` (T142) ↔ `check_cross_layer_writes.py` (T143): T142 makes the *missing-script* case
  of this specific hook fail closed; T143 makes the *broken-import* case fail closed. The two cover
  complementary failure modes of the same enforcer — no overlap, no gap between them.

## Suggested Next Session Focus

1. **Fix the `_append_resolution` fresh-ticket guard and its masking test (Concern #1).** ~3 LoC +
   1 test. Make the empty/placeholder-only check blockquote-aware (reuse `strict`'s optional
   client-visible pattern) and add a test whose Resolution body is the full template shape under
   `--append`. This is the only confirmed defect and it silently degrades the audit trail (closed
   tickets retaining `(Fill in on close.)`).

2. **Add a fence-aware comment or scan to `_resolution_section` (Concern #2).** ~2 LoC comment now,
   or a small fence-skip later. Cheap insurance against the third recurrence of the section-terminator
   pattern S23 already flagged once.

3. **Record the `--harness` bypass decision (Concern #3).** Either add the
   `read_session_state != STATE_WORKSPACE` assertion, or leave a one-line code comment stating that
   `--harness` is a deliberate unguarded escape hatch for programmatic callers. Lowest priority —
   it's a documentation/decision item, not a fix.

No multi-session carry-forwards: all three S25 concerns were retired this session (Concern #1 → T142,
Concern #2 → T143, Concern #3 → T141 verify-and-defer). All three S26 items are net-new from this
session's diff, and two of the three are Low impact.

---


