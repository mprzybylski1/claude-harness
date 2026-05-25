# Opus Review Notes — Archive S0–S9

Archived from `docs/opus_notes.md`. All findings are either fixed or tracked in `docs/tickets/`.
Use `grep` to search. Do not load into session context.

---

# Opus Review — S001 YYYY-MM-DD

**Scope:** Template initialization — no production code reviewed.

**Files reviewed:** none (template placeholder)

---

## Invariant Violations

None. Template not yet in use.

## Architectural Concerns

None.

## Bugs & Implementation Issues

None.

## Session Notes Discrepancy

None.

## Tickets Opened This Session

None.

## Tickets Closed This Session

None.

## Suggested Next Session Focus

Fill in `docs/architecture_invariants.md`, complete CLAUDE.md placeholders, and open
your first ticket.

## Clean

N/A — template placeholder review.

---

# Opus Review — S1 2026-05-25

**Scope:** Multi-workspace architecture (T001–T009) plus 20 follow-up findings from the
mid-session review. Reviewed the full session diff (~2017 lines) covering
`workspace_config.py`, `workspace.py`, `portfolio.py`, `generate_client_progress.py`,
`run_static_analysis.py`, the three hooks, and 45 new tests.

## Invariant Violations

1. **`scripts/tools/workspace_config.py:14` (`_yaml_load`) — silent fallback on YAML parse failure.**
   `except Exception: return {}` swallows any error and lets `active_workspace()` return
   `None`, which causes hooks to fall through to harness-root paths. If a workspace's
   `workspace.yaml` becomes malformed mid-session, ticket writes silently land in
   `docs/tickets/closed/` of the harness instead of being rejected. This is a strict
   Invariant 4 violation in the workspace-detection trust path. Fix: distinguish "file
   missing" (return {}) from "parse error" (re-raise or log+exit 2) — `yaml.YAMLError` and
   `OSError` should be handled separately. Confirmed from diff.

2. **`scripts/hooks/check_session_log.py:170-186` (`check_unstaged_code_changes`,
   workspace branch) — no `assert_workspace_boundary()` before reading repo paths.**
   The hook iterates `_all_repos(ws)` and runs `git status --porcelain` against each
   `Path(repo["path"]).expanduser().resolve()`. If `workspace.yaml` is tampered with or
   has a stale absolute path pointing outside the declared repos (or to another
   workspace's tree), the hook reads it without checking. Per Invariant 5 the boundary
   call must precede any repo file access. Fix: call
   `assert_workspace_boundary(repo_path, ws)` inside the loop before
   `subprocess.run([... "git", "status", ...], cwd=str(repo_path))`. Diff suggests this
   path is the only repo-touching code in the hook that lacks the call.

## Architectural Concerns

3. **`scripts/tools/run_static_analysis.py:879-895` — boundary check only at script
   entry, not enforced inside check functions.** `assert_workspace_boundary(primary, ws)`
   is called once before `_run_checks_for_repo`. The check functions
   (`check_test_syntax`, `check_no_utcnow`, etc., imported from `prepare_opus_context`)
   receive `scan_root` and walk it internally. If any of those functions follow a
   symlink leaving `scan_root`, or join a relative path that escapes the repo (e.g.
   reading a sibling repo via `repo_root / ".." / "other"`), Invariant 5 is violated
   silently. Diff suggests check functions only call `scan_root`-anchored `rglob`/glob
   patterns, but I cannot verify without reading `prepare_opus_context.py`. Mitigation:
   either have `_run_checks_for_repo` `os.chdir(scan_root)` + pass relative paths only,
   or assert boundary on every file open inside the check helpers.

4. **`scripts/tools/generate_client_progress.py:531-558` — no sanitisation of ticket
   Resolution text.** Despite the session summary describing it as "sanitised
   client-facing progress.md", the function passes the first sentence of the Resolution
   section through verbatim. If a developer writes internal-only notes (paths, internal
   PRs, slack handles, secret URLs, internal jargon) in `## Resolution`, those leak into
   `client/progress.md`. Either (a) add an explicit allowlist/transform pass, or (b)
   document that Resolution text is shown to clients as-is so authors know to write it
   accordingly. Currently neither happens.

5. **`scripts/tools/workspace_config.py:18-19` (`_yaml_load`) — bare `Exception` catch
   masks bugs.** Distinct from finding #1: even when keeping a fallback, catching bare
   `Exception` hides `ImportError` (yaml missing), `AttributeError`, etc., that should
   surface as errors. Replace with `(OSError, yaml.YAMLError)` and let other exceptions
   propagate.

6. **`scripts/hooks/check_ticket_acs.py:139-145` — Bash source path fallback can read
   outside declared repos.** When a Bash command references `cat foo/bar.md`, the hook
   tries `ws_dir/foo/bar.md` first and falls back to `REPO_ROOT/foo/bar.md`. If `foo`
   includes `..` traversal, the resolved `REPO_ROOT/foo/bar.md` could escape the harness
   root entirely. The `except Exception: continue` (line 145) silently absorbs the
   failure, so no abuse signal surfaces. Low likelihood, but the fallback path isn't
   bounded. Fix: `resolved.resolve()` then verify it's `relative_to(REPO_ROOT)` or
   `ws_dir`.

## Bugs & Implementation Issues

7. **`scripts/hooks/check_session_log.py:130-136` — `sessions_rel` computation is
   structurally dead in workspace mode.** In workspace context `sessions_path` is
   `workspaces/<slug>/internal/sessions.md` which is gitignored, so it will never appear
   in `all_changed`. The hook then unconditionally falls through to the content-based
   "today's date in Session Log" fallback, which is the only real check in workspace
   mode. The comment on line 132 acknowledges this — but the comparison
   `sessions_rel in all_changed or sessions_path in all_changed` (line 139) is misleading
   dead code. Either delete the path-based branch in workspace mode or document that the
   content check is the real enforcement.

8. **`scripts/tools/generate_client_progress.py:486-491` — header-line skipping logic
   is fragile.** Looking for `r"\*\*\s*\n"` after `header_match.start()` to find the
   end of the header line. If the session header has no closing `**` on the same line
   (e.g., a multi-line summary that wraps), `body_start` stays at `header_match.end()`,
   which is inside the partial header text. Add a `\n` anchor explicitly and document
   the expected header form.

9. **`scripts/tools/portfolio.py:769` — `_last_session` parses without a workspace
   boundary check.** `portfolio.py` reads `internal/sessions.md` for every workspace it
   iterates, which is fine for metadata (it's workspace-local), but the script does not
   assert that the workspace's repo paths are still valid. If `workspace.yaml` references
   a now-deleted repo, `repo_count` still shows the declared count. Minor — but the
   output should mark stale workspaces.

10. **`scripts/tools/workspace.py:1047-1050` — `repo_path.exists()` only warns, doesn't
    block.** During `cmd_create`, a non-existent repo path produces a warning but the
    workspace is still created. Then `assert_workspace_boundary` calls against that
    workspace will silently treat the bad path as "outside", potentially excluding the
    primary repo from static analysis. Either error out, or mark the repo as `disabled`
    in YAML.

11. **`scripts/hooks/regenerate_ticket_index.py:99` — `_is_closed_ticket` substring
    match is too loose.** `"/tickets/closed/" in file_path` matches any path with that
    substring, including e.g. `notes/tickets/closed/file.md` outside both
    `docs/tickets/` and `workspaces/*/internal/tickets/`. Tighten to require either
    `docs/tickets/closed/` or `/internal/tickets/closed/` (parallel to
    `_is_ticket_file`).

12. **`scripts/hooks/check_session_log.py:174-186` — workspace branch drops
    `TRACKED_PREFIXES` filter.** At harness root, `check_unstaged_code_changes`
    restricts to `TRACKED_PREFIXES` (`core/`, `infra/`, etc.). In workspace mode it
    reports every `.py` file. If a workspace declares a large repo with many unrelated
    `.py` files, this floods the hook output. Consider per-workspace `tracked_prefixes`
    in `workspace.yaml`, or scope to a sensible default like `**/src/**`.

## Test Gaps

13. **No test that `_yaml_load` raises (or exits) on malformed YAML.** All current tests
    use valid YAML. A `test_workspace_config.py` case feeding `name: [unclosed` to
    `load_workspace` would currently pass with `{}` returned, which is exactly the
    silent-fallback issue (#1). Add the failing test, then fix.

14. **No integration test for `run_static_analysis` in workspace mode end-to-end.**
    `test_workspace_extra.py::TestRunStaticAnalysisWorkspaceMode::test_workspace_mode_calls_boundary_check`
    stubs `primary_repo`, `secondary_repos`, and `assert_workspace_boundary` — so it
    proves the call site exists but not that real boundary violations are blocked.
    Add a test that creates a workspace with one repo, plants a symlink to `/etc`
    inside that repo, and verifies `run_static_analysis.main()` exits with code 2 if
    any check function tries to read through the symlink.

15. **No test for the workspace branch of `check_unstaged_code_changes`.**
    `test_hooks_workspace_scoping.py` tests path detection but not the new git-status
    iteration. A test with two workspace repos, each containing modified `.py` files,
    asserting the returned list contains `repo1/foo.py` and `repo2/bar.py`, would
    catch any future regression in the per-repo loop.

## Suggested Next Session Focus

1. **Fix the two invariant violations (#1, #2) before any other work.** Add boundary
   call in `check_unstaged_code_changes`'s workspace branch; split YAML-missing from
   YAML-malformed in `_yaml_load`. Both are 5-line changes plus tests.

2. **Decide and document `## Resolution` sanitisation policy** (#4). Either add a
   sanitisation pass to `generate_client_progress.py` or explicitly document that
   Resolution text is rendered to clients verbatim, so ticket authors know.

3. **Create the first real workspace and exercise the full hook chain.** The current
   gate item "First real workspace created and used for a live session" will surface
   any remaining path/boundary issues that synthetic tests cannot.

---


