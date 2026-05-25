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
