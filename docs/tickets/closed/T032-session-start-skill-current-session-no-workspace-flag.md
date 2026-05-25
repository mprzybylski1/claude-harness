---
id: T032
title: session-start skill invokes current_session.py without --sessions in workspace mode
severity: medium
status: closed
phase: 2
layer: process
opened: S7 2026-05-25
closed: S7 2026-05-25
---

## Problem

`/session-start` skill (`.claude/skills/session-start/SKILL.md` Step 3)
documents the workspace-path substitution table for `sessions.md`,
`opus_notes.md`, and `tickets/INDEX.md` — but the line that invokes
`current_session.py` is plain:

```
Run `python scripts/tools/current_session.py` to get the session ID.
```

`current_session.py` was made workspace-aware in T020 (accepts `--sessions
PATH`), but the skill does not pass the workspace path. Result: in a
workspace session, the tool returns the harness-global session number
instead of the workspace-local one.

Live in scrabble-score S2: tool returned `S7` (harness-global) when the
workspace was on `S2`. The agent had to manually correct the briefing
based on the last entry in `sessions.md`.

## Acceptance Criteria

- [x] `session-start` SKILL Step 3 updated to invoke
      `python scripts/tools/current_session.py --sessions <INTERNAL>/sessions.md`
      when in a workspace, mirroring the pattern used for
      `extract_session_brief.py` and `extract_opus_key_sections.py` in
      Steps 1.2 and 1.3.
- [x] Behavior verified in a workspace and at harness-root.

## Notes

Low-effort fix — one-line markdown change in the SKILL. The tool itself
already supports the flag (T020 closed S5).

Worth a parallel check of any other SKILL or script that calls
`current_session.py` without a path — `prepare_opus_context.py`,
`session-close`, `regenerate_ticket_index.py` — to make sure the same
omission isn't lurking elsewhere. (Quick grep: `grep -rn "current_session.py"
scripts/ .claude/`.)

## Resolution

`session-start` SKILL.md Step 3 updated: workspace sessions now pass
`--sessions <INTERNAL>/sessions.md` to `current_session.py`.
`session-close` SKILL.md Step 0 also updated to show the optional flag.
Grep check confirmed no other skills have the omission (`workflow-review`
already has the workspace-aware form).
