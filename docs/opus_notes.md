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
