# scripts/tools — Workspace-Awareness Matrix

This matrix documents which scripts in `scripts/tools/` honor workspace-specific
paths and which operate only on harness-root data. Snapshot taken at S6 2026-05-25;
update when adding new scripts.

## Workspace-aware scripts

These scripts accept flags documented in `session-start` and `session-close` SKILLs.
When no flag is supplied they fall back to the harness-root default — so harness-root
sessions are unaffected.

| Script | Workspace flags | Notes |
|--------|----------------|-------|
| `current_session.py` | `--sessions PATH` | Reads session log to derive session number |
| `extract_session_brief.py` | `--sessions PATH` | Reads phase/active-work/log sections |
| `extract_opus_key_sections.py` | `--opus PATH` | Reads last Opus review; `--with-carry-forwards` also workspace-aware |
| `extract_carry_forwards.py` | `notes_file` kwarg (called from `extract_opus_key_sections.py`) | Not intended to be called standalone for workspace sessions |
| `prepare_opus_context.py` | `--repo PATH`, `--sessions PATH`, `--opus PATH`, `--output PATH` | Git diff runs in `--repo`; static analysis skipped for non-Python repos |
| `archive_session_log.py` | `--sessions PATH`, `--archive PATH` | Moves old session log entries to archive |
| `rotate_opus_notes.py` | `--opus PATH`, `--archive PATH` | Archives old Opus review sections |
| `classify_session.py` | `--repo PATH` | Git ops run in `--repo`; code paths and session-close prefix loaded from `<repo>/harness.yaml` (falls back to harness root). SKILL passes `--repo <primary-repo-path>` for workspace sessions. |
| `generate_ticket_index.py` | `--sessions-file PATH` | Used by `regenerate_ticket_index.py` hook |

## Workspace-compatible scripts (no special flags needed)

| Script | Notes |
|--------|-------|
| `session_close_commit_msg.py` | Pass `--session N` explicitly (SKILL already does this); reads persisted `.git/CLAUDE_SESSION_ID` as fallback — does not need workspace paths |

## Intentionally harness-root only

| Script | Reason |
|--------|--------|
| `update_system_state.py` | Generates a global `docs/system_state.md` dashboard; reads harness-root `sessions.md` and `tickets/INDEX.md`; not workspace-specific by design |

## Infrastructure / library (not called directly per-workspace)

| Script | Notes |
|--------|-------|
| `workspace.py` | Workspace management CLI (`create`, `list`, `archive`) |
| `workspace_config.py` | Library; called by hooks and tools |
| `workspace_internal_path.py` | Resolves internal docs path for a given workspace slug |
| `portfolio.py` | Cross-workspace overview; always reads all workspaces |
| `surface_stale_tickets.py` | Reads harness-root `docs/tickets/INDEX.md`; needs workspace flag if workspace tickets are separate |
| `repo_hygiene.py` | Harness-root hygiene checks |
| `harness_config.py` | Library; loads `harness.yaml`; `load_for_repo(path)` for per-workspace config |
| `analyze_tool_log.py` | Reads `.git/session_tool_log.jsonl`; produces workflow efficiency report; `--log`, `--session` flags; opt-in via `workflow_telemetry: true` in `harness.yaml` |

## Adding a new script

When you add a script to `scripts/tools/`:
1. Decide: does it read session-specific data (sessions.md, opus_notes.md, tickets/)?
2. If yes: add `--sessions` / `--opus` / `--repo` / `--archive` flags with harness-root defaults.
3. Add a row to the table above.
4. Add a test in `tests/` verifying the flag reads from the supplied path, not ROOT.
