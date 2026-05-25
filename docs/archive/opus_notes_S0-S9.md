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

# Opus Review — S3 2026-05-25

**Scope:** Single-ticket session (T014) implementing `docs_path` support so workspace
docs (sessions.md, opus_notes.md, tickets/, archive/) can live inside a project repo
instead of `workspaces/<slug>/internal/`. Diff covers `workspace_config.py`,
`workspace.py`, three hooks, `portfolio.py`, `generate_client_progress.py`, a new
CLI helper, two SKILL.md docs, and two test files. ~440 lines insertions.

## Invariant Violations

1. **`scripts/hooks/check_ticket_acs.py:139-171` — Bash source resolution does NOT
   look at `docs_path`, so AC pre-lint is silently disabled for docs_path workspaces.**
   When the workspace is configured with `docs_path: ~/projects/myapp/.harness`, a
   Bash command `mv tickets/open/T001.md tickets/closed/T001.md` (run with CWD inside
   the docs_path) parses `src = "tickets/open/T001.md"`. The hook tries `ws_dir / src`
   (i.e. `workspaces/<slug>/tickets/open/T001.md` — wrong) then falls back to
   `REPO_ROOT / src` (harness root — also wrong). Neither resolves to the actual
   ticket file inside docs_path. The subsequent bounds check rejects the path as
   "outside REPO_ROOT and workspace", emits a WARNING, and continues — so unchecked
   ACs never get blocked. This is a **silent invariant-4 / fail-closed regression**
   introduced by T014: the AC pre-lint is the only mechanism preventing tickets from
   being moved to closed/ with unchecked items, and it is now a no-op for any
   workspace that uses docs_path. Fix: include `_get_closed_dir().parent.parent`
   (the docs root) and CWD in the candidate-resolution list, and add the docs root
   to the bounds-check allowlist. Confirmed by reading
   `scripts/hooks/check_ticket_acs.py:139-171` and tracing through with a docs_path
   workspace; no test in the new `TestDocsPathRouting` class covers the Bash branch.

2. **`scripts/tools/workspace.py:144-156` — docs_path validation is missing a
   "harness-root containment" check.** `is_within_workspace(docs_path, temp_ws)` only
   confirms docs_path is inside a declared repo. But nothing prevents docs_path from
   pointing INTO another workspace's directory tree if that workspace is declared as
   a repo. Example: if the primary repo is `~/projects/myapp` and the user types
   `~/projects/myapp/workspaces/some-other-ws/internal` as docs_path, the check
   passes (it's inside the declared repo) but the user has just colocated this
   workspace's docs inside another workspace's tree. Per Invariant 5, cross-workspace
   data must not be writable. Fix: after the `is_within_workspace` check, also
   verify docs_path is NOT inside `workspaces_base()` (or only allow it inside the
   primary repo's path explicitly, not just any declared repo).

## S1/S2 Carry-Forwards Status

- **S1 #3 (workspace-isolation in `run_static_analysis` helpers) — STILL OPEN.**
  Unchanged this session.
- **S1 #7 (dead `sessions_rel` path-based comparison) — STILL OPEN.** Diff at
  `check_session_log.py:263-269` keeps the comment ("workspace internal/ files are
  gitignored so this check typically falls through") but the dead comparison
  remains. Now slightly worse: with docs_path, sessions.md is NOT gitignored — it
  lives inside the project repo, so it CAN appear in `all_changed`. The dead branch
  is no longer entirely dead; it's now half-active and the relative-path computation
  via `Path(sessions_path).relative_to(project_root)` will raise ValueError when
  sessions_path is outside `project_root` (which is the harness root, not the docs_path
  root). The try/except catches it and falls back to `SESSIONS_MD = "docs/sessions.md"`
  for the comparison — which then NEVER matches in docs_path mode because the actual
  changed path will be relative to the project repo, not the harness. So with
  docs_path, the path-based check is dead and the content check fires every time,
  reading sessions.md from an absolute path. Functionally OK, but the relative-path
  logic should be removed or rewritten for docs_path. **NEW carry-forward: same
  bug, expanded scope.**
- **S1 #8 (header-line regex fragility in `generate_client_progress.py`) — STILL OPEN.**
- **S1 #9 (portfolio stale-repo marking) — STILL OPEN.**
- **S1 #10 (workspace.py warns-but-creates on missing repo) — STILL OPEN.**
- **S1 #11 (`_is_closed_ticket` loose substring match in `regenerate_ticket_index.py`)
  — STILL OPEN.** The new `_is_ticket_file` (line 137-144) now broadly matches any
  path with `/tickets/` and falls through to `_detect_workspace_from_path`, which
  iterates ALL workspaces' YAMLs. The loose substring at line 106 is unchanged.
- **S1 #12 (`TRACKED_PREFIXES` filter missing in workspace branch) — STILL OPEN.**
- **S1 #14 (no E2E test for `run_static_analysis` workspace mode) — STILL OPEN.**
- **S1 #15 (no test for per-repo git-status iteration) — STILL OPEN.**
- **S2 #15 (Resolution audit of closed tickets before client_progress runs)
  — STILL OPEN.**
- **S2 #17 (`active_workspace_dir()` called twice per Bash command) — STILL OPEN.**
- **S2 #18 (silent OSError swallow in AC pre-lint) — STILL OPEN.**
- **S2 #19 (no test for `ImportError` propagation in `_yaml_load`) — STILL OPEN.**
- **S2 #20 (no test for ws_dir branch of bounds check) — STILL OPEN.**
- **S2 #21 (no regression test for boundary check ordering) — STILL OPEN.**

## Architectural Concerns

3. **`scripts/hooks/regenerate_ticket_index.py:55-68` — slow path performs N YAML
   loads per hook invocation.** Every Edit/Write whose path contains `/tickets/` and
   isn't matched by the fast path iterates ALL non-archived workspaces and loads
   each `workspace.yaml`. The hook fires on every Edit/Write, so a single session
   that edits many tickets does O(edits × workspaces) YAML loads. On a system with
   10 workspaces this adds up. Mitigation: cache the per-workspace docs_path → ws_dir
   mapping at hook-script load (sys.modules cache), or pre-filter by checking
   whether `file_path` even starts with any candidate prefix. Combined with the
   fact that `_is_ticket_file` (line 137-144) now sends ANY `/tickets/`-containing
   path through `_detect_workspace_from_path`, this is paid even on false-positive
   edits to `/some/dir/tickets/random.md`.

4. **`scripts/tools/workspace_config.py:39-48` — `internal_dir` blindly resolves
   `docs_path` without verifying it exists.** `Path(docs_path).expanduser().resolve()`
   succeeds even if the directory has been deleted (Python's `Path.resolve()` does
   not require existence on default settings). Downstream readers then silently
   treat the missing directory as "no tickets", which can fail-open: a workspace
   whose docs_path was deleted shows 0 open tickets in `portfolio.py`, an empty
   sessions log in `extract_session_brief.py`, and would create a fresh sessions.md
   on first write. Fix: add `if not docs_path_resolved.is_dir(): print(...);
   sys.exit(2)` at the top of `internal_dir` or in `active_internal_dir`, with a
   recovery hint ("workspace.yaml points to a missing docs_path; restore or update
   the path"). At minimum, hooks that read from it should error out loudly rather
   than silently produce empty results.

5. **`scripts/tools/workspace.py:158-161` — scaffolding writes into a directory
   that may already contain user data.** `_scaffold` and `_write_initial_files` use
   `mkdir(parents=True, exist_ok=True)` and `write_text` without an overwrite check.
   If the user types a docs_path that already contains a `sessions.md` (e.g. they're
   migrating an existing workspace), it gets overwritten with the empty initial
   template. No prompt, no backup. Fix: detect existing `sessions.md` /
   `tickets/INDEX.md` / `opus_notes.md` in docs_path and either refuse to scaffold
   or prompt the user (`Files already exist at <path>. Overwrite? [y/N]`).

## Bugs & Implementation Issues

6. **`scripts/hooks/check_session_log.py:263-269` — `sessions_rel` calculation can
   raise ValueError when docs_path is configured, hidden by the try/except.** In
   docs_path mode `sessions_path` resolves to e.g.
   `/home/user/projects/myapp/.harness/sessions.md`, and `project_root` is the
   harness root. `Path(sessions_path).relative_to(project_root)` raises ValueError.
   The except sets `sessions_rel = SESSIONS_MD = "docs/sessions.md"`. The subsequent
   comparison `sessions_rel in all_changed or sessions_path in all_changed` then
   compares "docs/sessions.md" against `all_changed`, which contains git-relative
   paths from the harness repo only (since `git diff main...HEAD` was run with
   `cwd=project_root`). Even if the workspace's sessions.md was modified, `all_changed`
   only contains harness-repo files — workspace repo changes are never tracked here.
   The path-based check is structurally dead in docs_path mode. The content check at
   line 272 saves it, but the error message at line 282-289 prints
   `"docs/sessions.md has no Session Log entry"` which is misleading — it should
   print the actual workspace sessions.md path. Fix: in workspace mode, skip the
   path-based comparison entirely and use sessions_path directly in the error message.

7. **`scripts/tools/workspace.py:160-161` — `_scaffold(ws_dir, docs_dir)` only
   creates `tickets/open`, `tickets/closed`, `archive` in `docs_dir`, but T012's
   docs say opus_review_context.md also lives in `<INTERNAL>`.** The scaffold
   creates the tickets/ subtree but not the `opus_review_context.md` file. That's
   fine for the file itself (generated on demand), but means a fresh docs_path
   workspace has no `opus_review_context.md` until session-close runs. If
   `prepare_opus_context.py --output <INTERNAL>/opus_review_context.md` is run
   before session-close completes once, it must create the parent directory. Check
   `prepare_opus_context.py` does so — minor risk only.

8. **`scripts/hooks/regenerate_ticket_index.py:104-106` — `_is_closed_ticket` is
   the carry-forward S1 #11 substring match, unchanged.** Worth re-flagging here
   because T014's expanded `_is_ticket_file` makes it more likely the loose match
   fires on docs_path-routed files. The check is used by `check_closed_attribution`
   (line 109-134), which warns about closed: field mismatches. A loose match would
   trigger spurious warnings on files outside the actual ticket tree, but won't
   block anything — low severity.

9. **`scripts/tools/workspace.py:144-156` — `is_within_workspace` is called BEFORE
   `ws_dir.mkdir(parents=True)`, but `_repo_roots(temp_ws)` iterates
   `Path(r["path"]).expanduser().resolve()` for repos that may not exist on disk.**
   `Path.resolve()` with default settings handles non-existent paths fine (returns
   the lexically resolved path), so this works. However, combined with S1 #10 (repo
   path existence is only a warning), a user can create a workspace where the
   "primary repo" path doesn't exist, then any docs_path the user provides will
   pass `is_within_workspace` if the lexical resolution makes it look like a child.
   Compound risk with #4 above.

## Test Gaps

10. **No test for the AC pre-lint Bash branch in docs_path mode (Invariant
    Violation #1 above).** The new `TestDocsPathRouting` class in
    `tests/test_hooks_workspace_scoping.py` covers `_resolve_paths`, `_get_closed_dir`,
    and `_detect_workspace_from_path`, but does NOT cover `check_ticket_acs._bash_ticket_sources`
    in docs_path context. A test that creates a docs_path workspace, runs
    `hook.main()` with a Bash command moving a ticket to docs_path's `closed/`, and
    asserts that unchecked ACs trigger `sys.exit(2)` would have caught the violation
    in #1.

11. **No test that the new slow-path workspace detection performance is bounded.**
    With many workspaces, the O(N) YAML loads in `_detect_workspace_from_path`
    become noticeable. A simple test that creates 20 fake docs_path workspaces and
    asserts the hook completes under, say, 200ms would catch any future regression
    where this gets even slower.

12. **`test_resolve_paths_uses_docs_path` and `test_get_closed_dir_uses_docs_path`
    create the workspace.yaml but never plant a tampered docs_path (e.g. pointing
    outside the declared repos).** The boundary-violation case in `cmd_create`
    (`is_within_workspace` check) is exercised only by code inspection. A test that
    drives `cmd_create` interactively (or extracts the validation into a testable
    function) and asserts exit(1) on out-of-bounds docs_path would close that AC.

## Suggested Next Session Focus

1. **Fix Invariant Violation #1 (AC pre-lint silently disabled in docs_path mode)
   before any real client workspace runs.** This is a fail-closed regression and
   is the single highest-priority item. Add docs_path awareness to
   `check_ticket_acs._bash_ticket_sources` candidate-resolution and bounds-check,
   plus the test in #10.

2. **Fix Invariant Violation #2 (docs_path can land inside another workspace's
   tree) by tightening `cmd_create`'s validation.** Reject docs_path inside
   `workspaces_base()` explicitly.

3. **Then attack the carry-forward backlog by topic:** group `_is_closed_ticket`,
   `TRACKED_PREFIXES` filter, dead `sessions_rel` branch (now extended by S3 #6),
   and the "stale closed-ticket Resolution audit" into a single docs/hook cleanup
   session. Each is small but the backlog of 14 open carry-forwards is getting
   unwieldy and undermines the Phase 1 gate.

---

# Opus Review — S5

Scope: workspace-awareness flags across `scripts/tools/`, dead trading-app code
removal from `prepare_opus_context.py`, new `/workflow-review` skill, and a fresh
`scrabble-score` workspace scaffold. ~1225 insertions / 269 deletions.

## Invariant Violations

None new. The S3 #6 carry-forward (dead `sessions_rel` path-based comparison in
`check_session_log.py:262-271`) and S3 #4 (`internal_dir` no-existence-guard)
remain — both addressable in a future cleanup pass but no regression from S5.

## Concrete bugs

1. **`scripts/tools/extract_opus_key_sections.py:24` — `OPUS_NOTES` is a
   relative path, breaks the harness-root default.** The module uses
   `OPUS_NOTES = Path("docs/opus_notes.md")` (relative), unlike every other
   tool in this batch and unlike `extract_carry_forwards.py:18` which uses
   `Path(__file__).resolve().parents[2] / "docs" / "opus_notes.md"` (absolute).
   When invoked from any CWD other than the harness root (e.g. inside a
   workspace where the SKILL is meant to fall back to harness defaults),
   `main()` will try to read `./docs/opus_notes.md` from the wrong directory
   and either fail or read the wrong file. Fix: replace line 24 with
   `OPUS_NOTES = Path(__file__).resolve().parents[2] / "docs" / "opus_notes.md"`
   and update line 77 to reference `path` instead of `OPUS_NOTES` (otherwise
   the error message also prints the wrong path when `--opus` is provided).

2. **`scripts/tools/rotate_opus_notes.py:50` — no existence guard on `notes`.**
   `content = notes.read_text()` is called unconditionally. If a user passes
   `--opus /nonexistent/path` the script crashes with `FileNotFoundError`
   instead of the clean error message that `archive_session_log.py:103-105`
   provides for the same scenario. Add `if not notes.exists(): print(
   f"ERROR: {notes} not found", file=sys.stderr); sys.exit(1)` before the
   `read_text()` call. Same inconsistency cost as S3 found in
   `extract_opus_key_sections.py` — consistency matters when SKILLs hand
   user-supplied paths to these scripts.

3. **`scripts/tools/classify_session.py` — `--repo` flag swaps git CWD but
   not the config that decides classification.** `CODE_PREFIXES` (line 34)
   and `_SESSION_CLOSE_PREFIX` (resolved through `_hc.session_close_prefix`)
   are loaded from the harness's own `harness.yaml`. With `--repo
   /home/user/projects/myapp`, git ops correctly run in the workspace repo,
   but the classifier looks for `src/`, `lib/`, `tests/` (harness values)
   in workspace repos that may use entirely different prefixes. Worse,
   `_get_last_session_close_sha` searches the workspace repo's git log for
   "docs: S\d+ session close" — workspace projects almost never have this
   commit pattern, so `sha = ""` triggers the conservative "code" fallback
   at line 113-115, which means workspace sessions are always classified
   "code" regardless of what changed. Fix: either accept `--code-paths`
   and `--session-prefix` flags, or read these from a workspace-specific
   config (e.g. workspace.yaml's `classify_config` block). Otherwise the
   `--repo` flag is decorative.

4. **`scripts/tools/prepare_opus_context.py:265 — `_is_python_project` gate
   is too coarse, leading to misleading PASS results.** When `--repo PATH`
   points at a Python project that has `pyproject.toml` but no `tests/`
   directory, `check_test_syntax` returns `PASS  0 test files compile
   cleanly` and `check_bash_blocks` returns `SKIP  check_skill_bash_blocks.py
   not found`. The user sees "PASS" for tests but in fact zero coverage was
   verified — a fail-open style positive. Tighten: in `check_test_syntax`,
   return `SKIP` (not PASS) when no test files are found. Same for
   `check_utcnow` when none of the searched directories exist.

5. **`scripts/tools/prepare_opus_context.py:393-395 — architecture
   invariants and ticket template always come from harness ROOT, even when
   `--repo` targets a workspace.** Lines 393 (`inv_path = ROOT / "docs" /
   "architecture_invariants.md"`) and 398 (`template_path = ROOT / "docs"
   / "tickets" / "TEMPLATE.md"`) ignore the workspace context. For workspace
   sessions, Opus is handed the harness's invariants and template, not the
   workspace's. Invariants are project-specific by definition — sending the
   wrong set silently degrades the review. Fix: when `--repo` is provided,
   look in `<repo>/docs/architecture_invariants.md` and `<repo>/docs/tickets/
   TEMPLATE.md` first, fall back to harness defaults only if missing. Or
   add explicit `--invariants` / `--template` flags.

6. **`docs/system_state.md` regression — current uncommitted file shows
   `T000` as an open ticket.** The Open Tickets table reads
   `| T000 | Short description (keep under 60 chars) | 2 | 3 | 4 | process |
   backend | frontend | fullstack | infra | process | 5 sessions |`. T000 is
   the TEMPLATE.md sentinel ID; current `docs/tickets/INDEX.md` correctly
   shows only T026. Root cause: at some point during S5 the
   `generate_ticket_index.py` script saw TEMPLATE.md as a ticket and
   `update_system_state.py:_extract_open_tickets` (line 53-70) pulled the
   resulting row by simple `line.startswith("| T")` matching. Two fixes
   needed: (a) `generate_ticket_index.py:load_tickets` (line 100-102) should
   skip any file with `id == "T000"` or filename `TEMPLATE.md`, and (b)
   `update_system_state.py` should re-run before commit so a stale
   `system_state.md` doesn't ship to the archive. The current uncommitted
   diff will be embedded in tomorrow's review context unless cleaned.

## Test gaps

7. **No tests for `classify_session.py` at all** (`grep classify_session
   tests/` returns empty), including the new `--repo` flag added in T022.
   Combined with finding #3, this means the workspace classification path
   has zero coverage — a regression that flips every workspace session to
   "docs" (skipping full Opus review) would go undetected. Add a class
   along the lines of the existing `TestArchiveSessionLogFlags` pattern in
   `tests/test_workspace_path_flags.py`.

8. **`tests/test_workspace_gitignore.py` has no test for the
   `repo_root == ROOT.resolve()` skip branch** (`workspace.py:57`). Easy to
   add: create a workspace whose docs_path lands inside the harness repo,
   call `_add_opus_context_to_gitignore`, assert no write happened. Without
   this test, a future refactor that removes the guard would re-add a
   redundant gitignore line in the harness's own `.gitignore` (or worse,
   point at a workspace path the harness doesn't actually own).

## SKILL drift / consistency

9. **`.claude/skills/session-close/SKILL.md:121` — bare `classify_session.py`
   call, no `--repo` for workspace sessions.** The README workspace-awareness
   matrix says "session-close SKILL should pass `--repo` for workspace
   sessions" (scripts/tools/README.md:31), but the SKILL itself doesn't.
   Lines 124-126 are advisory ("verify manually") instead of prescriptive.
   Either bake the `--repo` invocation into the SKILL when in workspace
   context, or drop the README claim. Today the SKILL drives behavior, so
   the README is technically wrong.

10. **`scripts/tools/harness_config.py:76` — stale docstring.** Lists
    `'eval_exec', 'sql_mutations'` as example check names, but both were
    deleted by T021. Update to mention the current set: `test_syntax`,
    `utcnow`, `bash_blocks` (which `harness.yaml:23` already documents
    correctly).

11. **`harness.yaml:11-14` — `code_paths` does not include `scripts/`.**
    The harness's own production code lives in `scripts/tools/` and
    `scripts/hooks/`, but the configured `code_paths` only contains
    `src/`, `lib/`, `tests/`. A session that touches only `scripts/tools/`
    (no test changes) would be classified as "docs" and skip full Opus
    review. This session is rescued only because `tests/` were also
    modified. Add `"scripts/"` to the list.

12. **`scripts/tools/archive_session_log.py:111-112` — docstring/behavior
    mismatch.** Docstring lines 16-17 promise the script prints
    "Session log has N entries (threshold M). No action needed." when
    `count <= threshold`. The code silently returns 0 with no output.
    Either restore the print (helpful for CLI visibility) or update the
    docstring to match the actual silent-success behavior.

13. **`scripts/tools/prepare_opus_context.py:389` — `--opus PATH` silently
    skipped if path does not exist.** No warning on typo'd path; the user
    thinks `opus_notes.md` was embedded in context but it was not. Add a
    `print(f"WARNING: --opus {opus_path} not found, skipping", file=
    sys.stderr)` when the path was provided but does not exist (distinct
    from the omit-by-default case where `opus_path is None`).

## Carry-forwards from S1–S4 (status check)

- S1 #3 (workspace-isolation in `run_static_analysis` helpers) — STILL OPEN.
- S1 #7 / S3 #6 / S4 #1 (dead `sessions_rel` path-based comparison) —
  STILL OPEN. No change this session; S5 did not touch
  `scripts/hooks/check_session_log.py`.
- S1 #8 (header-line regex fragility) — STILL OPEN.
- S1 #9 (portfolio stale-repo marking) — STILL OPEN.
- S1 #10 (workspace.py warns-but-creates on missing repo) — STILL OPEN.
- S1 #11 (`_is_closed_ticket` loose substring match) — STILL OPEN.
- S1 #12 (`TRACKED_PREFIXES` filter missing in workspace branch) — STILL OPEN.
- S1 #14 (no E2E test for `run_static_analysis` workspace mode) — STILL OPEN.
- S1 #15 (no test for per-repo git-status iteration) — STILL OPEN.
- S2 #15 (closed-ticket Resolution audit for client_progress safety) — STILL OPEN.
- S2 #17 (`active_workspace_dir()` called twice per Bash command) — STILL OPEN.
- S2 #18 (silent OSError swallow in AC pre-lint) — STILL OPEN.
- S2 #19 (no test for `ImportError` propagation in `_yaml_load`) — STILL OPEN.
- S2 #20 (no test for ws_dir branch of bounds check) — STILL OPEN.
- S2 #21 (no regression test for boundary check ordering) — STILL OPEN.
- S3 #3 (N YAML loads per hook in `regenerate_ticket_index.py` slow path) — STILL OPEN.
- S3 #4 (`internal_dir` blindly resolves `docs_path` without `is_dir` check) —
  PARTIALLY closed by T018 (which added the check in `active_internal_dir`
  for `docs_path` mode). `internal_dir` itself remains unchecked for callers
  bypassing `active_internal_dir`.
- S3 #11 (perf test for `_detect_workspace_from_path`) — STILL OPEN.
- S4 #3 (standard-workspace Bash branch in `check_ticket_acs` has no test) —
  STILL OPEN.

The backlog now stands at ~18 open carry-forwards. Several are individually
small (test gaps, minor refactors); collectively they undermine the Phase 1
gate. Suggest one full cleanup-pass session before any client workspace goes
live.

## Suggested Next Session Focus

1. **Fix findings #3 and #11 (and add the test in #7) together** — they're
   the same bug from two angles: workspace sessions get the wrong
   classification config. Without this, `--repo` is a misleading API
   surface. Estimated 1-ticket session.

2. **Clean `docs/system_state.md` and add the T000 filter in
   `generate_ticket_index.py:load_tickets` (finding #6).** Otherwise the
   stale T000 row will keep regenerating. Also a 1-ticket session;
   sequence it before the first real workspace is created so the dashboard
   is correct.

3. **Take a single dedicated session for the carry-forward backlog** — at
   18 open items, a focused pass attacking S1 #3 + S1 #11 + S1 #12 + S3 #3
   + S3 #6 (related to workspace-scoped path handling) is much more
   efficient than piecemeal fixes across many sessions. The shared
   infrastructure (workspace-aware `regenerate_ticket_index`, removal of
   dead path comparisons) means a single context window can carry the
   whole cleanup.

---

# Opus Review — S6 2026-05-25

Scope: closed T026 (telemetry hook + analyzer), T027 (classify_session `--repo`
config), T028 (prepare_opus_context invariants/template per-repo), T029
(`scripts/` in code_paths), T030 (batch consistency fixes). ~1061 insertions /
32 deletions. New PostToolUse hook wired in `.claude/settings.json`, new
`analyze_tool_log.py`, and 18 new telemetry tests.

## Invariant Violations

None new. S3 #6 / S4 #1 (dead `sessions_rel` path-based comparison) and the
broader carry-forward backlog from S5 remain unchanged this session.

## Concrete Bugs

1. **`scripts/hooks/log_tool_usage.py:48-53` — session tag in the JSONL log is
   wrong because the fast-path reads a bare integer and returns it as the
   session ID.** `current_session.persist_session(n)` writes `str(n)` (e.g.
   `"6"`) to `.git/CLAUDE_SESSION_ID`; the hook reads it via
   `claude_id.read_text().strip()` and returns `"6"` unchanged. The slow path
   (line 117) correctly returns `f"S{int(entries[-1]) + 1}"` (e.g. `"S6"`).
   Result: when the cache file exists (the common case once
   `current_session.py` has been run at session-start), every record gets
   `"session": "6"` instead of `"session": "S6"`. The analyzer's
   `--session S6` filter (`analyze_tool_log.py:48`,
   `rec.get("session") != session_filter`) then returns zero records, and
   `workflow-review`'s Step 1b call to `analyze_tool_log.py --session
   S[CURRENT]` silently produces an empty report. Fix: prepend `"S"` in
   `_current_session()` when the cached value is numeric, or change
   `persist_session` to write `f"S{n}"`. Neither is covered by the 18 new
   telemetry tests — every test in `tests/test_telemetry.py` either constructs
   JSONL fixtures directly or runs the hook in isolation without populating
   `.git/CLAUDE_SESSION_ID`, so the bug is invisible to CI.

2. **`scripts/tools/harness_config.py:514-517` — `load_for_repo` silently falls
   back to harness config when the workspace `harness.yaml` exists but is
   malformed (YAMLError, IOError, etc.).** The `except Exception` block prints
   a WARNING to stderr but still returns `load()` — the harness root config.
   This is a fail-open: a workspace with a typo in its `harness.yaml` (e.g.
   wrong indentation in `code_paths`) silently gets the harness's
   classification config, producing wrong "code"/"docs" verdicts. Fix-closed
   behavior: `sys.exit(2)` on parse failure of an existing file, so the user
   sees the error before classification runs on the wrong rules. The current
   warning is easy to miss in a long session-close output stream.

3. **`scripts/hooks/log_tool_usage.py:89` — `_SESSION_CACHE` is declared but
   never read or written.** Dead code introduced this session. Either remove
   it or use it (presumably it was meant to cache the resolved session ID to
   avoid the slow-path re-read on every tool call; if so, that's a separate
   feature). At minimum, delete the unused module-level constant so it doesn't
   mislead the next reader.

4. **`scripts/hooks/log_tool_usage.py:134-142` — `_extract_exit` always returns
   0 for non-Bash tools because only `tool_response["exit_code"]` is checked.**
   Edit/Write/Read/NotebookEdit hook responses never include `exit_code`, so
   the `exit` field in the JSONL is uniformly 0 for those tools — making the
   field meaningless except as a Bash-vs-non-Bash signal. `analyze_tool_log.py`
   doesn't currently use `exit` in any of its sections, so this is latent
   noise rather than a downstream miscalculation, but the field name implies
   data that isn't actually being captured. Either drop the field, document
   "Bash only" in the docstring, or add Edit/Write success detection (the
   `tool_response` payload typically has `success` or error keys for those).

5. **`scripts/hooks/log_tool_usage.py:124-131` — Bash `command` is truncated to
   120 chars and logged verbatim with no secret scrubbing.** Commands like
   `psql -p hunter2 ...` or `curl -H 'Authorization: Bearer SECRET' ...` land
   in `.git/session_tool_log.jsonl` in plaintext. The log is local to `.git/`
   so confidentiality risk is bounded, but if a user ever shares the file
   (e.g. uploading for a workflow-review consultation), credentials leak. At
   minimum, document the risk in the hook docstring; ideally, scrub common
   secret patterns (`-p \S+`, `Bearer \S+`, `password=\S+`) before logging.

## Test Gaps

6. **No test exercises `_current_session()` in `log_tool_usage.py`.** The
   integration between `persist_session` (writes `"6"`) and `_current_session`
   (returns it verbatim) — Bug #1 above — is the highest-leverage missing
   test. A single test that writes `"6"` to a temp `.git/CLAUDE_SESSION_ID`,
   invokes the hook, and asserts the log line has `"session": "S6"` would
   catch the bug immediately.

7. **No test for `load_for_repo` malformed-YAML fail-closed behavior** (Bug #2).
   The new tests cover the happy path and the missing-file fallback but not
   the corrupt-YAML case. A test that writes invalid YAML and asserts the
   intended behavior (currently: silent fallback with WARNING; should-be:
   `sys.exit(2)`) would lock in either decision.

8. **No test that the PostToolUse hook self-gates correctly (exits 0 silently)
   when `workflow_telemetry` is unset or False.** The hook is wired in
   `.claude/settings.json` unconditionally, so every tool call spawns
   `log_tool_usage.py`. If the early-exit gate ever regresses (e.g. someone
   inverts a boolean), the hook would start writing logs on every harness
   install with no opt-in. Easy guard: a test that runs the hook with
   `workflow_telemetry: false` and asserts no log file is created.

## Architectural Concerns

9. **PostToolUse hook fires on every tool call regardless of telemetry-enabled
   state**, spawning a Python subprocess that does an import + YAML load
   before exiting. On a session with hundreds of tool calls, this adds
   measurable overhead even when telemetry is off. Two cheap mitigations:
   (a) check for a sentinel file (`.git/workflow_telemetry_on`) before any
   Python import, exiting in <10ms; (b) gate the hook in `.claude/settings.json`
   itself with a matcher that's only added when the feature is enabled (via
   a setup script). The current architecture pays the subprocess cost
   universally for an opt-in feature.

10. **`analyze_tool_log.py` `_retry_sequences` (line 317-333) interleaves
    sessions when computing "same tool ≤30s" pairs.** If session S5 ends at
    timestamp T and session S6 starts at T+10s with the same tool, the pair
    is flagged as a "retry" even though they're in different sessions. Easy
    fix: split records by `session` first, then compute retries per-session,
    then concatenate. Without this, multi-session aggregation reports are
    polluted with false-positive retries at session boundaries.

11. **`scripts/tools/prepare_opus_context.py` repo-local invariants/template
    lookup is correct but doesn't surface which set was used in the output
    context.** When `--repo` is provided and the repo has its own
    `architecture_invariants.md`, that file is embedded; if not, the harness's
    is embedded silently. Opus reviewing the context can't tell which it got
    without re-reading the diff. Add a header line like `Source:
    <repo>/docs/architecture_invariants.md` or `Source: harness fallback` to
    the section so the review is explicit about which constraints apply.

## SKILL / Consistency

12. **`scripts/tools/README.md` `analyze_tool_log.py` row** (line 47) lists it
    in the "Workspace-compatible scripts" table but the script reads only
    `.git/session_tool_log.jsonl` from the harness root — it has no workspace
    awareness at all. Strictly speaking it's harness-root-only because the
    hook writes to harness `.git/`. If the intent is per-workspace telemetry,
    the hook needs `--repo`-style scoping too. If single-harness telemetry is
    the design, the README row should say so explicitly to avoid confusion
    when a workspace user runs `analyze_tool_log.py` expecting workspace data.

## Carry-forwards from S1–S5

No carry-forward was addressed this session (S6 was a pure-ticket-closure
session for T026–T030, all newly opened in S5). The backlog of ~18 carry-forwards
remains unchanged from the S5 review. The Phase 1 gate dependency ("create
first real workspace and use it") is still blocking — and worth doing before
or in parallel with the carry-forward cleanup, since live use is the only way
to validate the workspace-aware paths against real workloads.

## Suggested Next Session Focus

1. **Fix Bug #1 (session ID format mismatch in telemetry hook).** This makes
   the entire T026 deliverable inert for the headline use-case
   (`workflow-review` calling `--session S<N>`). One-line fix in
   `_current_session()` plus one integration test (Test Gap #6). Without it,
   T026 is shipped but functionally broken.

2. **Fix Bug #2 (load_for_repo fail-open on malformed YAML)** with a test.
   Small change but it closes a fail-closed invariant gap before the first
   real workspace lands. Bundle with Bug #1 as a single "telemetry hardening"
   ticket.

3. **Then the carry-forward backlog session.** S5's recommendation #3 still
   stands and is now more urgent — the backlog grew by zero this session
   (good) but hasn't shrunk in three sessions (bad). Block out one full
   session for S1 #3 + S1 #7 / S3 #6 + S1 #11 + S3 #3 as a coherent
   workspace-scoped-paths cleanup, before any client workspace goes live.

---


