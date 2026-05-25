---
id: T021
title: prepare_opus_context.py is workspace-blind
severity: high
status: open
phase: 1
layer: infra
opened: S4 2026-05-25
closed:
---

## Problem

`scripts/tools/prepare_opus_context.py:71` — `_run()` calls
`subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)` with `ROOT` hardcoded
to the harness root. All git operations (log, diff, diff-stat) run there, so for any
workspace session the captured diff is the harness diff, not the workspace's primary
repo diff. The script also takes no `--sessions` / `--opus` / `--output` flags despite
`.claude/skills/session-close/SKILL.md` documenting them:

```
python scripts/tools/prepare_opus_context.py \
  --repo <primary-repo-path> \
  --sessions <INTERNAL>/sessions.md \
  --opus <INTERNAL>/opus_notes.md \
  --output <INTERNAL>/opus_review_context.md
```

During scrabble-score S1, the main agent had to hand-build `opus_review_context.md`
twice (once for `/implementation-review`, once for `/session-close`) because the
documented invocation does not work. Reproducible workspace post-session reviews
require this fix.

## Acceptance Criteria

- [ ] Add `--repo`, `--sessions`, `--opus`, `--output` flags. All optional; defaults match current harness-root behavior so harness-root sessions are unchanged.
- [ ] `_run()` uses the `--repo` value as `cwd` when set; falls back to `ROOT` otherwise.
- [ ] Static-analysis section (currently runs harness-specific checks against `ROOT`) is repo-aware when `--repo` is set: for non-Python repos (e.g. Swift), print "static analysis N/A for this repo type" rather than running harness-specific checks.
- [ ] Test in `tests/` calling the script with `--repo` pointing at a temp git repo and verifying the captured diff is from that repo, not the harness.
- [ ] All existing tests still pass.

## Notes

Pairs with T020 — together they cover the workspace-blind tools called by
session-start and session-close SKILLs.

## Resolution

(Fill in on close.)
