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
