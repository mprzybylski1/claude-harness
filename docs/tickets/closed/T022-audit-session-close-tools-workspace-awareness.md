---
id: T022
title: audit remaining session-close tools for workspace awareness
severity: medium
status: closed
phase: 1
layer: infra
opened: S4 2026-05-25
closed: S5 2026-05-25
---

## Problem

The `/session-close` SKILL calls several scripts whose workspace-awareness was not
exercised during scrabble-score S1 (the main agent either worked around them or they
happened to be no-ops on an empty workspace). Their behavior on a real workspace
session is unknown:

- `scripts/tools/update_system_state.py` — SKILL says it reads `docs/sessions.md` for global phase status; behavior for workspace sessions is undefined.
- `scripts/tools/rotate_opus_notes.py` — SKILL passes `--opus` / `--archive`; flag support unverified.
- `scripts/tools/archive_session_log.py` — SKILL passes `--sessions`; flag support unverified.
- `scripts/tools/session_close_commit_msg.py` — SKILL doesn't pass workspace paths; behavior unclear.
- `scripts/tools/classify_session.py` — SKILL says it checks workspace repos; current behavior may check harness root.

Each script needs a quick audit (`grep argparse` + `grep cwd=`) and either confirmation
that it already honors workspace paths or a fix.

## Acceptance Criteria

- [x] For each of the five scripts above: confirm via inspection whether it accepts the workspace paths the SKILL passes (`--sessions`, `--opus`, `--archive`, etc).
- [x] Document the result for each in a workspace-awareness matrix — either in `scripts/tools/README.md` (see T024) or as a `# workspace:` comment header in each script.
- [x] For any script that needs flag support but lacks it: either fix inline (small) or file a child ticket (larger).

## Notes

Follow-on from T020/T021 which covered the high-severity workspace-blind tools.
Result of this audit may produce additional tickets.

## Resolution

Audited and fixed in S5. Results: `archive_session_log.py` — added `--sessions`/`--archive` flags (SKILL documents these). `rotate_opus_notes.py` — added argparse with `--opus`/`--archive` flags, parameterized `rotate()` signature. `classify_session.py` — added `--repo` flag; git operations now use that cwd. `session_close_commit_msg.py` — already workspace-compatible via `--session N` (no flags needed). `update_system_state.py` — intentionally harness-root only; SKILL does not pass workspace paths; generates global system_state.md. All documented in `scripts/tools/README.md` (T024). Tests for archive and rotate in `tests/test_workspace_path_flags.py`.
