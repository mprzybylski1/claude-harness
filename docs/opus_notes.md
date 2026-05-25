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
