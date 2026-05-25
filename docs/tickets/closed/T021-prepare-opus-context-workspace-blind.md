---
id: T021
title: prepare_opus_context.py is workspace-blind
severity: high
status: closed
phase: 1
layer: infra
opened: S4 2026-05-25
closed: S5 2026-05-25
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

- [x] Add `--repo`, `--sessions`, `--opus`, `--output` flags. All optional; defaults match current harness-root behavior so harness-root sessions are unchanged.
- [x] `_run()` uses the `--repo` value as `cwd` when set; falls back to `ROOT` otherwise.
- [x] Static-analysis section (currently runs harness-specific checks against `ROOT`) is repo-aware when `--repo` is set: for non-Python repos (e.g. Swift), print "static analysis N/A for this repo type" rather than running harness-specific checks.
- [x] Test in `tests/` calling the script with `--repo` pointing at a temp git repo and verifying the captured diff is from that repo, not the harness.
- [x] All existing tests still pass.

## Notes

Pairs with T020 — together they cover the workspace-blind tools called by
session-start and session-close SKILLs.

## Resolution

Fixed in S5. Added `--repo`, `--sessions`, `--opus`, `--output` flags to `prepare_opus_context.py`. `_run()` now takes `cwd` param; `main()` creates a local `run()` closure that passes `repo_root`. `_static_analysis()` short-circuits with SKIP for non-Python repos; `check_eval_exec` also guards against missing `strategies/`. `--opus` causes the workspace opus_notes.md to be embedded in the context. Tests in `tests/test_prepare_opus_context_workspace.py` (5 tests).
