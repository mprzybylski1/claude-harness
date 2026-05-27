# Sessions

*(Rewritten each session by `/session-close`. Do not edit by hand.)*

---

## Current Phase & Status

*(Rewritten each session)*

**Phase 2 (Active):** Harness hardening and telemetry — fixing workspace session-start gaps, telemetry reliability, and tool correctness issues surfaced in first real workspace run.

Phase 1 gate: complete (S6 2026-05-25)
- [x] Workspace model designed and implemented (T001–T009)
- [x] All Opus review findings fixed
- [x] First real workspace created and used for a live session (Scrabble Score)

---

## Active Work

**S20 — closed T104–T112 (9 tickets): full workspace↔harness separation tooling from SR-001.**

Files changed:
- `scripts/tools/raise_for_harness.py` — NEW (T104): workspace-side SR creation; O_CREAT|O_EXCL retry, CWD slug detection
- `tests/test_raise_for_harness.py` — NEW (T104): 10 tests
- `scripts/tools/list_raised_concerns.py` — NEW (T105): harness aggregator of pending concerns grouped by workspace; impl-review: YAML parse warning, dead archive filter removed
- `tests/test_list_raised_concerns.py` — NEW (T105): 10 tests
- `scripts/tools/promote_raised_concern.py` — NEW (T106): SR→ticket promotion, stamps source: backref; impl-review: _stamp_source fatal on miss, _update_sr warns if harness_ticket absent
- `tests/test_promote_raised_concern.py` — NEW (T106): 12 tests
- `scripts/tools/reject_raised_concern.py` — NEW (T107): terminal rejection with reason + resolved_in
- `tests/test_reject_raised_concern.py` — NEW (T107): 11 tests
- `scripts/tools/close_ticket.py` — T108: _parse_source + _resolve_source_sr (close-the-loop SR resolution on ticket close); impl-review: slug validation, status guard (raised/promoted only), resolved_in warning
- `tests/test_close_ticket_source_sr.py` — NEW (T108): 7 tests
- `.claude/skills/session-start/SKILL.md` — T109: list_raised_concerns step (harness root); T110: surface_workspace_concerns step; state-file write step added
- `scripts/tools/surface_workspace_concerns.py` — NEW (T110): workspace own-concerns surface + auto-archive terminal items
- `tests/test_surface_workspace_concerns.py` — NEW (T110): 12 tests
- `scripts/hooks/check_cross_layer_writes.py` — NEW (T111): PreToolUse hook blocking workspace→harness and harness→workspace-internal writes; impl-review: resolved path constants, parse-error warning
- `tests/test_check_cross_layer_writes.py` — NEW (T111): 12 tests
- `.claude/settings.json` — T111: hook registered as PreToolUse Edit|Write
- `.gitignore` — T111: .claude/.active_workspace session state file
- `.claude/skills/session-close/SKILL.md` — T112: abandoned-session pattern; impl-review: bash→text fence on template blocks
- `workspaces/scrabble-score/raised/SR-001-*.md` — promoted (status: promoted, harness_ticket: T104–T112)

Tickets closed: T104–T112 (9 tickets from SR-001 child tickets)
Tickets opened: none (0 open at close)
Impl review: 8 findings fixed inline (path resolve, slug validation, status guard, resolved_in warning, _stamp_source fatal, _update_sr warn, dead filter, bash→text fence)

---

## Session Log

*(Append one line per session: `S[N] YYYY-MM-DD: <one-line summary>`. Never edit existing lines.)*

S000 2000-01-01: template initialized
S1 2026-05-25: multi-workspace architecture (T001–T009) + fixed 20 Opus review findings
S2 2026-05-25: fixed T010–T013 (all 4 Opus S1 findings) + 4 mid-session review fixes
S3 2026-05-25: implemented T014 — docs_path support for project-repo workspace docs
S4 2026-05-25: fixed T015–T019 (all 5 Opus S3 findings) + implementation-review test fixes
S5 2026-05-25: workspace-awareness flags (T020–T025) + dead trading-app code removal + /workflow-review skill
S6 2026-05-25: closed T026–T030 (telemetry hook, classify_session fix, invariants path fix, code_paths fix, batch consistency) + impl-review hardening (14 findings fixed, 18 new tests)
S7 2026-05-25: closed T031–T033 (workspace session-start gaps, telemetry overhead) + enabled telemetry by default + impl-review hardening (8 findings fixed)
S8 2026-05-25: closed T034–T038 (carry-forward fixes: ticket attribution, telemetry hardening, fail-closed YAML, retry session isolation, invariants labeling)
S9 2026-05-26: closed T039–T042, T045–T048 (hook abs paths, carry-forward tooling, close_ticket.py, expand_carry_forward.py); impl-review hardening; merged workflow-review skill
S10 2026-05-26: closed T043, T049, T051–T053 (S9 carry-forward backlog: close_ticket.py correctness, expand_carry_forward boundary bleed, YAML cache, misc); impl-review hardening (4 findings)
S11 2026-05-26: closed T054 (close_ticket.py: atomic move via os.replace, resolution permissive fallback, stamp regex fix, parse-failure warning)
S12 2026-05-26: closed T057 (telemetry workspace-aware session stamping); reverted hook paths to absolute; impl-review hardening (3 findings)
S13 2026-05-26: hook portability (git rev-parse); closed T044, T055, T056, T058–T063; workflow review opened T064–T071; impl-review fixed 4 findings
S14 2026-05-26: closed T064–T071 (S13 workflow-review backlog); cross-process rate-limit, close_ticket git-staging, worktree docs; impl-review fixed 2 findings
S15 2026-05-26: closed T072 (workspace git staging wrong repo) + T050 (opus archive tests); impl-review fixed 5 findings; all tickets closed
S16 2026-05-26: closed T073-T077 (log_tool_usage triad, generate_ticket_index, close_ticket workspace index, rotate_opus_notes h2, classify_session no-yaml); workflow-review opened T079-T082
S17 2026-05-26: closed T078-T085 (8 tickets: S16 workflow-review backlog + T083-T085 from S17 workflow-review); 0 open at close
S18 2026-05-26: closed T086-T090 (Opus S17 concerns + workflow-review T089-T090); impl-review 4 inline fixes; 0 open at close
S19 2026-05-26: closed T091-T102 (12 tickets: Opus S18 concerns + workflow-review T098-T102); impl-review 9 inline fixes; 0 open at close
S20 2026-05-27: closed T104-T112 (9 tickets: SR-001 workspace↔harness separation tooling); impl-review 8 inline fixes; 0 open at close
