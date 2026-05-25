---
id: T027
title: classify_session.py --repo flag is effectively a no-op
severity: medium
status: open
phase: 2
layer: infra
opened: S5 2026-05-25
closed:
---

## Problem

`classify_session.py --repo <path>` routes git operations to the workspace repo but
`CODE_PREFIXES` and the session-close commit prefix are still read from the harness's
own `harness.yaml`. Two consequences:

1. `CODE_PREFIXES` contains harness paths (`src/`, `lib/`) — a workspace repo with
   `app/`, `server/`, etc. never matches, so every file change classifies as "docs".
2. `_get_last_session_close_sha` searches the workspace repo's git log for
   `"docs: S\d+ session close"` — workspace projects never have this pattern, so
   `sha = ""` and the conservative "code" fallback fires every time.

Combined: workspace code sessions are always classified `"code"` (via fallback, not
via actual file matching), so the logic is accidentally correct for the common case
but the wrong reason. A docs-only workspace session with a missing session-close
anchor would also fall back to "code" and trigger a full Opus review unnecessarily.

No tests exist for `classify_session.py` at all (`grep classify_session tests/`
returns empty).

Opus S5 findings #3 and #7.

## Acceptance Criteria

- [ ] `classify_session.py --repo` reads workspace-specific code paths from
      `workspace.yaml` (or falls back to harness defaults when not configured)
- [ ] Session-close anchor search uses a configurable prefix, not a hardcoded
      harness pattern, when `--repo` is a workspace repo
- [ ] At least 3 tests in `tests/test_workspace_path_flags.py` (or new file)
      covering: (a) correct "docs" classification for docs-only changes in workspace
      repo, (b) correct "code" classification for code changes, (c) fallback to
      "code" when no anchor found
- [ ] `scripts/tools/README.md` workspace-awareness matrix updated if semantics change

## Notes

Related to T028 (wrong invariants with `--repo` in `prepare_opus_context.py`) —
both stem from workspace-specific config not being plumbed through.

The SKILL.md for session-close (finding #9) also calls `classify_session.py`
without `--repo` for workspace sessions — should be updated once this ticket is
done so the SKILL matches actual capability.

## Resolution

(Fill in on close.)
