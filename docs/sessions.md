# Sessions

*(Rewritten each session by `/session-close`. Do not edit by hand.)*

---

## Current Phase & Status

*(Rewritten each session)*

**Phase 1 (Active):** Multi-workspace architecture build-out — harness evolves from single-project tool to multi-project orchestrator.

Gate requirements before Phase 2:
- [x] Workspace model designed and implemented (T001–T009)
- [x] All Opus review findings fixed
- [ ] First real workspace created and used for a live session

---

## Active Work

**S1 — workspace multi-project architecture (T001–T009) + 20 Opus findings fixed**

Files changed:
- `scripts/tools/workspace_config.py` (new) — CWD-based workspace detection, isolation enforcement
- `scripts/tools/workspace.py` (new) — create/list/archive CLI
- `scripts/tools/portfolio.py` (new) — cross-workspace metadata view
- `scripts/tools/generate_client_progress.py` (new) — client-facing progress.md
- `scripts/tools/run_static_analysis.py` — multi-repo scanning, boundary checks
- `scripts/tools/harness_config.py` — added workspaces_dir() accessor
- `scripts/hooks/check_session_log.py` — workspace-scoped path routing; fixed project_root=os.getcwd() critical bug; workspace guards on research artefact checks
- `scripts/hooks/check_ticket_acs.py` — workspace-aware closed/ dir detection; workspace-relative Bash source path resolution
- `scripts/hooks/regenerate_ticket_index.py` — workspace path detection, narrowed exception
- `.claude/skills/session-start/SKILL.md` — workspace detection step, portfolio call, path table
- `.claude/skills/session-close/SKILL.md` — workspace scoping, multi-repo Opus, client progress step
- `harness.yaml` — workspaces_dir key
- `.gitignore` — workspaces/*/internal/, workspaces/*/client/, workspaces/archive/
- `docs/architecture_invariants.md` — Invariant 5 (workspace isolation)
- `tests/test_workspace_isolation.py`, `tests/test_hooks_workspace_scoping.py`, `tests/test_workspace_extra.py` — 45 workspace tests

Tickets closed: none (harness infrastructure session)
Tickets opened: none

Remaining open items: create first real workspace for live use

---

## Session Log

*(Append one line per session: `S[N] YYYY-MM-DD: <one-line summary>`. Never edit existing lines.)*

S000 2000-01-01: template initialized
S1 2026-05-25: multi-workspace architecture (T001–T009) + fixed 20 Opus review findings
