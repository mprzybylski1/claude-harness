---
id: T030
title: small consistency fixes from Opus S5 review (batch)
severity: low
status: open
phase: 2
layer: process
opened: S5 2026-05-25
closed:
---

## Problem

Six small inconsistencies found by Opus S5 review — each a 1–5 line fix:

**a) `prepare_opus_context.py` — check_test_syntax/check_utcnow return PASS with
zero files (F4).** When no test files exist in the repo, `check_test_syntax`
returns `PASS  0 test files compile cleanly` — a misleading false positive.
Should return `SKIP` when the search finds nothing to check.

**b) `session-close/SKILL.md:121` — calls bare `classify_session.py` without `--repo`
for workspace sessions (F9).** The README workspace matrix says `--repo` should be
passed; the SKILL doesn't. Update SKILL to pass `--repo <primary-repo-path>` once
T027 is done, or remove the README claim.

**c) `scripts/tools/harness_config.py:76` — stale docstring (F10).** Lists
`eval_exec`, `sql_mutations` as example check names; both deleted by T021. Update to
`test_syntax`, `utcnow`, `bash_blocks`.

**d) `archive_session_log.py` docstring/behavior mismatch (F12).** Docstring promises
a print on under-threshold; code silently returns 0. Either restore the print or
update the docstring.

**e) `prepare_opus_context.py:389` — `--opus PATH` silently skipped if missing (F13).**
If the user typos the path, the context is generated without opus_notes — no warning.
Add `print(f"WARNING: --opus {opus_path} not found, skipping", file=sys.stderr)`.

**f) `test_workspace_gitignore.py` — no test for `repo_root == ROOT.resolve()` skip
branch (test gap F8).** Easy add: create workspace with docs_path inside harness repo,
call `_add_opus_context_to_gitignore`, assert no write to `.gitignore`.

## Acceptance Criteria

- [ ] `check_test_syntax` returns `SKIP` (not `PASS`) when zero test files found
- [ ] Same for `check_utcnow` when none of the searched directories exist
- [ ] `harness_config.py` docstring updated to current check names
- [ ] `archive_session_log.py` docstring updated to match silent-success behavior
- [ ] `prepare_opus_context.py` warns to stderr when `--opus PATH` doesn't exist
- [ ] Test added to `test_workspace_gitignore.py` for same-repo skip branch
- [ ] `session-close/SKILL.md` updated once T027 is resolved (may be deferred to T027)

## Notes

Sequence (b) after T027 since it depends on workspace `classify_session.py` support.

## Resolution

(Fill in on close.)
