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

**S13 — hook portability fix + closed T058–T063 + workflow review + impl-review hardening.**

Files changed:
- `.claude/settings.json` — all 5 hook commands switched from hardcoded `/home/marcin/...` paths to `$(git rev-parse --show-toplevel)` (cross-machine portability)
- `CLAUDE.md` — updated hook path documentation; added archive split note (T063)
- `tests/test_config.py` — new regression guard: no hardcoded paths in hook commands
- `scripts/hooks/log_tool_usage.py` — T058: inner-except logs instead of swallowing; `rsplit` for chained `=` tokens; T059: rate-limit `_log_error` at 10+1/60s; impl-review: fail-closed `_detect_workspace` on exception
- `tests/test_telemetry.py` — 8 new tests (T058/T059); 4 subprocess tests converted to in-process (T063); 213 total
- `scripts/tools/current_session.py` — T060: skip cache write when `--sessions` arg provided (workspace calls don't clobber `.git/CLAUDE_SESSION_ID`)
- `scripts/tools/extract_session_brief.py` — T061: `## Hook errors (last 5)` section; tail via deque (impl-review fix)
- `.claude/skills/session-start/SKILL.md` — T061: updated Step 1.2 and briefing template
- `scripts/tools/prepare_opus_context.py` — T044: `_is_within_root()` helper; `check_test_syntax` skips symlinks escaping workspace
- `tests/test_static_analysis_symlink_boundary.py` — T044: 8 integration tests
- `scripts/tools/extract_opus_key_sections.py` — T055: `run_with_carry_forwards` captures stderr, re-emits as `Note:`; impl-review: removed dead subprocess/importlib code, deduplicated `sys.path.insert`
- `scripts/tools/ticket_constants.py` — T056: new file with `AGING_EMPTY_MARKER = "*(none)*"`
- `scripts/tools/generate_ticket_index.py` — T056: use `AGING_EMPTY_MARKER` constant
- `scripts/tools/surface_stale_tickets.py` — T056: regex uses `re.escape(AGING_EMPTY_MARKER)`
- `docs/tickets/open/` — opened T064–T071 (workflow review + impl-review findings)

Tickets opened: T058, T059, T060, T061, T063, T064, T065, T066, T067, T068, T069, T070, T071
Tickets closed: T058, T059, T060, T061, T044, T055, T056, T063

Remaining open: T050, T064–T071

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
