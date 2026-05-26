---
id: T040
title: Fix test isolation in test_exits_silently_when_both_off — use _make_fake_root
severity: medium
status: closed
phase: 2
layer: test
opened: S9 2026-05-26
closed:
---

## Problem

`tests/test_telemetry.py:88-109` — `test_exits_silently_when_both_off` mutates the
real `harness.yaml` and real `.git/workflow_telemetry_on` sentinel of the running
repository. The `try/finally` restores state on success, but if the test is interrupted
(SIGINT, OOM, runner timeout), `harness.yaml` is left with `workflow_telemetry: false`
and the sentinel is absent — silently disabling telemetry until the user manually fixes it.

Flagged as S7 Concern #5, still open at S8 (Finding #2).

The `_make_fake_root` helper already exists at lines 52-72 of the same file, unused.

## Acceptance Criteria

- [ ] `test_exits_silently_when_both_off` no longer reads or writes real `harness.yaml`
      or real `.git/workflow_telemetry_on`.
- [ ] Uses `_make_fake_root(tmp_path, telemetry_on=False, sentinel=False)` + `mock.patch.object`
      to redirect `ltu.ROOT`, `ltu._SENTINEL`, `ltu._LOG_PATH`, `ltu._ERR_PATH`.
- [ ] Still asserts exit code 0 and elapsed < 0.5s.
- [ ] No source change to `log_tool_usage.py` required.
- [ ] All other telemetry tests still pass.

## Resolution

Converted `test_exits_silently_when_both_off` from a subprocess-based test that mutated
real `harness.yaml`/sentinel to a unit test using `_make_fake_root` + `mock.patch.object`
to redirect `ltu.ROOT`, `ltu._SENTINEL`, `ltu._LOG_PATH`, `ltu._ERR_PATH` to `tmp_path`.
`ltu.main()` is called directly; `pytest.raises(SystemExit)` catches the `sys.exit(0)`.
No source change to `log_tool_usage.py`. 23/23 tests pass.

Closed S9 2026-05-26.
