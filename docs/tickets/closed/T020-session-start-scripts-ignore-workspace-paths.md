---
id: T020
title: session-start scripts ignore workspace paths
severity: high
status: closed
phase: 1
layer: infra
opened: S4 2026-05-25
closed: S5 2026-05-25
---

## Problem

Three scripts called by `/session-start` hardcode harness-root paths and ignore the
`--sessions` / `--opus` flags that `.claude/skills/session-start/SKILL.md` documents
as the intended usage. The result is that workspace session briefings show the wrong
session number and the wrong content (harness-root work instead of the empty
workspace). Surfaced during the scrabble-score S1 live session, where
`current_session.py` returned `S4` instead of `S1`.

- `scripts/tools/current_session.py:22` — `SESSIONS_MD = Path(__file__).resolve().parents[2] / "docs" / "sessions.md"`. No argparse at all.
- `scripts/tools/extract_session_brief.py:23` — same hardcoded path. SKILL passes `--sessions <INTERNAL>/sessions.md`; flag is silently ignored.
- `scripts/tools/extract_opus_key_sections.py:111-112` — argparse only handles `--with-carry-forwards`. SKILL passes `--opus <INTERNAL>/opus_notes.md`; unknown flag falls through `parse_known_args` and the script reads the default harness path.

`scripts/tools/generate_ticket_index.py` already correctly resolves the workspace
session via `--sessions-file` (used by the `regenerate_ticket_index.py` PostToolUse
hook), so the fix pattern is established.

## Acceptance Criteria

- [x] `current_session.py` accepts `--sessions <path>`; when set, reads from that path; when omitted, reads harness-root default.
- [x] `extract_session_brief.py` accepts `--sessions <path>` with the same fallback semantics.
- [x] `extract_opus_key_sections.py` accepts `--opus <path>` with the same fallback semantics (alongside the existing `--with-carry-forwards`).
- [x] Test in `tests/` per script: invoking with a temp `sessions.md` / `opus_notes.md` outside the harness root reads the temp file.
- [x] All existing tests still pass.

## Notes

Discovered during scrabble-score S1 (first live workspace session). Main agent had to
manually note the session was actually S1 despite scripts reporting S4.

## Resolution

Fixed in S5. Added `--sessions PATH` to `current_session.py` and `extract_session_brief.py`; added `--opus PATH` to `extract_opus_key_sections.py`; threaded the opus path through to `extract_carry_forwards.main()` so `--with-carry-forwards` also reads the workspace file. All three fall back to harness-root defaults when the flag is omitted. Tests in `tests/test_workspace_path_flags.py` (6 tests across the three scripts).
