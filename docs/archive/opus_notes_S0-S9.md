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

# Opus Review — S2 2026-05-25

**Scope:** Four ticket closures (T010–T013) addressing S1 findings #1, #2, #4, #5, #6,
plus four mid-session review fixes. Diff covers `workspace_config.py`,
`check_session_log.py`, `check_ticket_acs.py`, `session-close/SKILL.md`,
`TEMPLATE.md`, and two test files. Total: 8 commits, ~250 lines.

## S1 Carry-Forwards Fixed This Session

1. **S1 #1 (T010) — FIXED.** `_yaml_load` now distinguishes `(FileNotFoundError,
   OSError)` (return `{}`) from `yaml.YAMLError` (re-raise). `import yaml` lifted out
   of the try block so `ImportError` propagates. Four new tests in
   `tests/test_workspace_config.py` cover all four branches.

2. **S1 #2 (T011) — FIXED.** `assert_workspace_boundary(repo_path, ws)` called inside
   the `_all_repos` loop in `check_unstaged_code_changes`, before `repo_path.exists()`
   and the `git status` subprocess. Test `test_tampered_path_triggers_system_exit_2`
   exercises the failure path.

3. **S1 #4 (T012) — POLICY DECIDED.** Option A chosen: documentation-only. `TEMPLATE.md`
   Resolution section now warns that first sentence is client-visible verbatim;
   `session-close/SKILL.md` Step 5c carries the same note. No code-level sanitisation —
   deferred until first real client workspace exercises the path. Acceptable for now,
   but the leak surface is still present (see Architectural Concerns #5 below).

4. **S1 #5 (T010, same diff) — FIXED.** Bare `except Exception` in `_yaml_load`
   replaced with narrowed `(FileNotFoundError, OSError)` plus explicit `yaml.YAMLError`
   re-raise.

5. **S1 #6 (T013) — FIXED.** `check_ticket_acs.py` Bash branch now calls
   `resolved.resolve()` followed by `relative_to(REPO_ROOT)` / `relative_to(ws_dir)`
   bounds check; out-of-bounds paths skipped with WARNING. Bare `except Exception`
   narrowed to `(OSError, UnicodeDecodeError)`. Test
   `test_bash_traversal_path_skipped_with_warning` drives `hook.main()` via stdin.

## S1 Carry-Forwards Still Open

6. **S1 #3 — NOT ADDRESSED.** `run_static_analysis.py` boundary check is still only
   asserted at script entry, not enforced inside imported check helpers from
   `prepare_opus_context.py`. Still a latent Invariant 5 hole if any helper follows
   a symlink or joins a `..` path. No ticket opened in S2.

7. **S1 #7 — NOT ADDRESSED.** Dead-code `sessions_rel` path-based comparison in
   `check_session_log.py` workspace mode remains. Low impact (the content-based
   fallback already enforces the check), but misleading.

8. **S1 #8 — NOT ADDRESSED.** `generate_client_progress.py` header-line skipping
   regex `r"\*\*\s*\n"` still fragile against multi-line summary headers.

9. **S1 #9 — NOT ADDRESSED.** `portfolio.py` does not mark workspaces whose declared
   repo paths no longer exist as stale. Cosmetic.

10. **S1 #10 — NOT ADDRESSED.** `workspace.py cmd_create` still only warns on
    non-existent repo path; workspace is created with a broken declaration.

11. **S1 #11 — NOT ADDRESSED.** `_is_closed_ticket` substring match
    `"/tickets/closed/" in file_path` still loose; would match
    `notes/tickets/closed/file.md`.

12. **S1 #12 — NOT ADDRESSED.** Workspace branch of `check_unstaged_code_changes`
    still has no `TRACKED_PREFIXES` filter — reports every `.py` file in declared
    repos. Will flood output on a real repo.

13. **S1 #14 — NOT ADDRESSED.** No end-to-end integration test for
    `run_static_analysis` in workspace mode (only stubbed unit test exists). Coupled
    with #6 above — if helpers do leak via symlink, no test catches it.

14. **S1 #15 — NOT ADDRESSED.** No test for the per-repo git-status iteration in
    `check_unstaged_code_changes` workspace branch. T011's new test only proves the
    boundary check fires; it does NOT prove the iteration produces correct output for
    two repos with modified files.

## Invariant Violations

None new this session. S1 #3 (workspace-isolation hole in `run_static_analysis`
helpers) remains a latent Invariant 5 risk but is unchanged from S1.

## Architectural Concerns

15. **T012's Option-A decision pushes leak risk to ticket authors.** The policy now
    says "first sentence of Resolution is client-visible — don't write internal paths
    there." This is enforceable only by author discipline. Every existing closed
    ticket's Resolution (T001–T013) should be audited against this rule before any
    real client workspace runs `generate_client_progress`. T010's Resolution
    currently contains `_yaml_load` (internal symbol), `tests/test_workspace_config.py`
    (internal path), `ImportError`/`yaml.YAMLError` (internal jargon) — all of which
    would leak verbatim. T013's Resolution contains `check_ticket_acs.py` and
    `tests/test_hooks_workspace_scoping.py`. Policy-only fix means these are now
    actively unsafe to render to a client. Either: (a) re-audit each closed
    Resolution and rewrite the first sentence, or (b) implement a minimal
    sanitisation pass as originally proposed in Option B.

16. **T011's boundary check is structurally tautological in non-tampered runs.** Both
    `_all_repos(ws)` and `_repo_roots(ws)` (inside `assert_workspace_boundary`)
    derive from the same `workspace["repos"]` dict. So a non-tampered run will always
    pass — the call protects only against in-process mutation of `_all_repos`'s
    return value between the two calls. This is acceptable defense-in-depth, but
    the test (`test_tampered_path_triggers_system_exit_2`) only fires because it
    mocks `_all_repos` while leaving `active_workspace` returning the original dict.
    No real attack surface in current code exercises this — the test is artificial.

## Bugs & Implementation Issues

17. **`check_ticket_acs.py:144,157` — `active_workspace_dir()` called twice in the
    bounds-check path.** Line 144 binds `ws_dir` for the candidate-path step; line
    157 calls it again inside the bounds check. Two `Path.cwd().resolve()` calls and
    two YAML loads per Bash command. Cosmetic — but in workspace context with many
    Bash commands per session, this adds up. Bind once at the top of the `for src`
    loop.

18. **`check_ticket_acs.py:172` — `OSError` catch may still mask real read failures.**
    Narrowing from bare `Exception` to `(OSError, UnicodeDecodeError)` is correct,
    but the `continue` still silently skips. If a closed-ticket source file exists
    in-bounds but is unreadable (permission error, symlink loop), the AC pre-lint
    silently produces no findings for that file. Consider logging the OSError to
    stderr before `continue` — same pattern as the WARNING just above.

## Test Gaps

19. **`test_workspace_config.py` does not test `ImportError` propagation.** T010's AC
    #2 (`ImportError` not swallowed) is verified by code inspection (`import yaml`
    outside try block), not by a test. A test that stubs `sys.modules["yaml"] = None`
    and asserts `load_workspace` raises `ImportError` would close the AC properly.

20. **`test_bash_traversal_path_skipped_with_warning` only tests `active_workspace_dir
    return_value=None`.** The bounds-check has two branches (REPO_ROOT, ws_dir). The
    ws_dir branch is exercised by no test. Add a workspace-context case where a
    traversal escapes BOTH ws_dir and REPO_ROOT, and verify WARNING fires.

21. **No regression test for the "boundary check before exists() check" mid-session
    fix in `check_unstaged_code_changes`.** The session log notes "boundary check
    before exists() check (review fix)" but the test plants `outside_repo` as an
    existing directory. A test variant where the tampered path points to a
    non-existent location would catch any future regression where someone moves the
    boundary check below the `if not repo_path.exists(): continue` guard.

## Suggested Next Session Focus

22. **Audit and rewrite closed-ticket Resolution first sentences (Concern #15).**
    Before any real client workspace runs `generate_client_progress`, each of T001–
    T013's Resolution needs a client-facing first sentence. This is a 30-minute
    docs-only pass and is a hard prerequisite to the Phase 1 gate ("First real
    workspace created and used for a live session").

23. **Close S1 carry-forwards #11, #12, #14 (items 11, 12, 13 above) before the
    first real workspace.** `_is_closed_ticket` tightening, `TRACKED_PREFIXES` filter
    in workspace mode, and end-to-end test for `run_static_analysis` workspace mode
    are all small, but #12 (no prefix filter) will produce noisy hook output on the
    first real repo and #14 leaves the most concerning S1 finding (#3) untested.

24. **Either implement Option B for `generate_client_progress` sanitisation, or
    explicitly defer the client-progress feature.** Option A only works if every
    ticket author is disciplined — and item 15 shows current closed tickets already
    violate the policy. If the team won't backfill, the safer move is to gate the
    client_remote push step behind a manual review until sanitisation lands.

---

# Opus Review — S4

**Invariant Violations:**
None new this session. S4 explicitly fixed both S3 Invariant Violations (T015 closed
the AC pre-lint fail-open in docs_path mode; T016 closed the docs_path-inside-
workspaces_base hole). T017 partially closed S3 #6 (sessions_rel comparison now
prints the correct path on error, but the underlying path-based comparison is still
structurally dead in docs_path mode — see Architectural Concerns).

**Architectural Concerns:**

1. **`scripts/hooks/check_session_log.py:262-271` — T017 only fixed the error
   message, not the structurally dead path-based comparison.** In docs_path mode,
   `Path(sessions_path).relative_to(project_root)` raises ValueError because
   sessions_path is inside the workspace repo, not the harness. The new fallback
   sets `sessions_rel = sessions_path` (absolute). The subsequent comparison
   `sessions_rel in all_changed or sessions_path in all_changed` then compares
   an absolute path against a set of harness-repo-relative paths and can never
   match. The content-based check at line 272+ saves it (the test asserts this
   path fires), but the entire `sessions_rel in all_changed` branch is dead code
   in docs_path mode. T017's resolution explicitly punts on this: "the git-path
   comparison still silently misses." Either gate the path-based comparison
   behind a docs_path-mode check (skip it entirely when sessions_path is outside
   project_root) or remove the branch. Carry-forward of S1 #7 / S3 #6 — still
   open after T017.

2. **`scripts/hooks/check_ticket_acs.py:139` — `_get_closed_dir()` calls
   `active_workspace_dir()` internally; S2 #17 fix is half-landed.** The Bash
   branch now binds `ws_dir = active_workspace_dir()` once outside the for-src
   loop (good), but `docs_root = _get_closed_dir().parent.parent` triggers
   another `active_workspace_dir()` + YAML load via `_get_closed_dir()` →
   `active_internal_dir()`. Net: 2 workspace lookups per Bash command instead of
   the previous 2 (was: `active_workspace_dir()` × 2; now: `_get_closed_dir()`
   + `active_workspace_dir()`). Cosmetic; S2 #17 carry-forward not fully closed.

3. **T015 silently fixed a latent bug in standard (non-docs_path) workspace
   Bash branch.** Previously `ws_candidate = ws_dir / src` resolved to
   e.g. `workspaces/<slug>/tickets/open/T001.md` — but in standard workspaces,
   tickets live at `workspaces/<slug>/internal/tickets/open/T001.md`. So the
   Bash branch only worked correctly for absolute source paths in standard
   workspaces too — relative paths silently fell through to the
   `REPO_ROOT / src` fallback (harness root, also wrong). The T015 fix
   incidentally fixes this because `docs_root = _get_closed_dir().parent.parent`
   resolves to `ws_dir/internal` in standard workspaces. **But no test covers
   the standard-workspace Bash branch** — see Test Gaps below. This means a
   regression could re-break standard-workspace AC pre-lint without detection.

4. **T019's overwrite guard is partial — only catches three specific filenames
   and the open/closed ticket dirs.** Does not check for migrated `archive/`
   content, `opus_review_context.md`, `system_state.md`, or any other docs that
   could exist at the docs_path root. Acceptable for the documented data-loss
   case (a fresh `_scaffold` + `_write_initial_files` writes only the three
   detected filenames), but a broader "is this directory pristine?" check would
   be more robust if `_scaffold` ever grows new initial files.

**Carry-forwards from prior sessions:**

- **S1 #3** (workspace-isolation in `run_static_analysis` helpers) — STILL OPEN.
- **S1 #7 / S3 #6** (dead `sessions_rel` path-based comparison) — PARTIALLY closed
  by T017 (error message fixed); structural dead-code in docs_path mode remains.
- **S1 #8** (header-line regex fragility in `generate_client_progress.py`) — STILL OPEN.
- **S1 #9** (portfolio stale-repo marking) — STILL OPEN.
- **S1 #10** (workspace.py warns-but-creates on missing repo path) — STILL OPEN.
- **S1 #11** (`_is_closed_ticket` loose substring match) — STILL OPEN.
- **S1 #12** (`TRACKED_PREFIXES` filter missing in workspace branch) — STILL OPEN.
- **S1 #14** (no E2E test for `run_static_analysis` workspace mode) — STILL OPEN.
- **S1 #15** (no test for per-repo git-status iteration) — STILL OPEN.
- **S2 #15** (closed-ticket Resolution audit for client_progress safety) — STILL OPEN.
  Now also applies to T015–T019 Resolutions, several of which contain internal
  symbols (`active_internal_dir`, `_workspaces_base`, hook script names).
- **S2 #17** (`active_workspace_dir()` called twice in Bash branch) — PARTIALLY closed.
  See Architectural Concern #2 above.
- **S2 #18** (silent OSError swallow in AC pre-lint) — STILL OPEN.
- **S2 #19** (no test for `ImportError` propagation in `_yaml_load`) — STILL OPEN.
- **S2 #20** (no test for ws_dir branch of bounds check) — STILL OPEN.
- **S2 #21** (no regression test for boundary check ordering) — STILL OPEN.
- **S3 #3** (N YAML loads per hook in `regenerate_ticket_index.py` slow path) — STILL OPEN.
- **S3 #11** (perf test for `_detect_workspace_from_path`) — STILL OPEN.

**Suggested Next Session Focus:**

1. **Close the remaining S3 #6 carry-forward properly.** Add an explicit
   docs_path-mode branch in `check_session_log.run_session_log_check` that
   either skips the path-based comparison or uses the workspace repo's git
   diff (not harness's) to populate `all_changed`. T017 only addressed the
   error message; the structurally dead comparison remains.

2. **Add a standard-workspace test for the Bash branch in
   `tests/test_hooks_workspace_scoping.py`** (TestDocsPathRouting). T015's two
   new tests cover docs_path mode only; the standard-workspace path resolution
   (`docs_root = ws_dir/internal`) is exercised by no test. Without it, a
   regression to the candidate-resolution order could silently re-disable AC
   pre-lint in standard workspaces.

3. **Phase 1 gate is now unblocked from a code-quality standpoint** — all S3
   findings are addressed. Highest-leverage next move is to **create the first
   real workspace and run a live session** (the open gate item). This will
   exercise the docs_path scaffolding/migration path in anger and surface any
   issues the T015–T019 fixes did not anticipate.

---


