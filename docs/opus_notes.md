# Opus Review — S29 2026-06-01

Scope: T150/T151/T152 — portability and scaffolding tooling, plus doc/spec edits. T150 adds a
shared `is_machine_specific_path` detector + `portable_path` collapser in `workspace_config.py`,
wires WARNINGs into `workspace.py cmd_create` (interactive) and a new `check_workspace_paths()`
finding in `repo_hygiene.py`, and rewrites the two existing workspace.yaml entries to `~/...` form.
T151 makes `_write_initial_files` scaffold a real `S0` sessions.md entry and a generator-format
INDEX.md. T152 adds `check_docs_path_gitignored.py` (advisory, always exit 0) and a session-start
step that surfaces a gitignored docs_path. No enforcement surface was touched: no change to
`check_cross_layer_writes.py`, `.claude/settings.json`, the `--sessions` session-ID routing in
`create_ticket.py`/`close_ticket.py`, or `assert_workspace_boundary`. 731 insertions / 42 deletions;
all 36 new tests pass; static analysis clean except the pre-existing, non-S29 bash-block-2
placeholder snippet (`--session S<N>` in CLAUDE.md commit example — illustrative, not executable).

## Invariant Violations

None.

Per-invariant verification against the S29 diff:
- **Inv 1 (workspace↔harness session-number separation):** Holds. The only session-numbered writes
  this session are the T151 scaffold (`workspace.py` L183-207): an `S0` Active-Work line + `S0`
  Session-Log entry in the **workspace** `sessions.md`, and `Generated S0` in the **workspace**
  INDEX.md. `S0` is a workspace number written into workspace-layer state — no harness `S<N>` leak,
  and no harness state is written by any S29 change. The `--sessions` routing flagged in the
  invariant's verification (`create_ticket.py`/`close_ticket.py`) is untouched.
- **Inv 2 (session-type declaration required):** Holds. The hook (`check_cross_layer_writes.py`) and
  its `Edit|Write` matcher in `settings.json` are unchanged. The only related touch is doc-only and
  it carries a minor precision regression worth recording (Concern 1): the **staged** session-start
  SKILL.md edit (context L692-697) rewrites the fail-closed description from "fails closed if the
  state file is missing **or empty**" to "fails closed if this file is **missing**." The hook still
  blocks on empty (`STATE_UNDECLARED` covers empty per the invariant), so this is a doc weakening of
  the *described* enforcement surface, not the actual one.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** Holds. `check_workspace_paths()`
  (`repo_hygiene.py` L120-147) reads only workspace.yaml config *strings* and emits `WARN` findings;
  it makes no boundary decision and stamps no audit field. `check_docs_path_gitignored.py` is
  advisory-by-design (exit 0 always, per its docstring). Neither is a fail-closed surface, and the
  two named write-path tools in the invariant are untouched.
- **Inv 4 (workspace isolation):** Holds. `check_workspace_paths()` iterates
  `list_active_workspaces()` config only — no repo *content* is read, so no cross-workspace content
  can leak. `check_docs_path_gitignored.py` reads only the target workspace's own `workspace.yaml`
  and runs `git check-ignore` against that workspace's own docs_path. The cross-workspace block in
  `check_cross_layer_writes.py` is untouched.

## Architectural Concerns

1. **Staged session-start SKILL.md edit drops "or empty" from the fail-closed description**
   (context L692-697). [Low impact, doc-only] The new wording says the hook "fails closed if this
   file is **missing**"; the original said "missing **or empty**." The actual hook still blocks the
   empty case (Invariant 2 maps empty → `STATE_UNDECLARED` → blocked), so this is a precision
   regression in the *prose*, not a behavior change. It's the same class of issue the invariants doc
   warns about: the doc that an operator reads to understand enforcement now under-describes it.
   Recommendation: restore "missing or empty" (or "missing/empty/undeclared"). ~1 word.

2. **`is_machine_specific_path` covers only four POSIX prefixes + Windows drives**
   (`workspace_config.py` L270-282; tests L613-635). [Low impact, likely by-design] The detector
   flags `/Users/`, `/home/`, `/mnt/`, `/Volumes/`, and `[A-Za-z]:[\\/]`, but not other absolute
   prefixes that are equally non-portable across machines/users (`/opt/...`, `/srv/...`, `/data/...`,
   bare `/Projects/...`). The parametrized test only asserts the covered prefixes, so coverage *looks*
   exhaustive but isn't — a path under `/opt/work/repo` silently passes the portability check and
   gets stored verbatim. Given the WARN is advisory and the realistic case is home-rooted paths,
   severity is genuinely low; flagging so the prefix list is a recorded decision, not an unexamined
   gap. Optional: warn on any leading `/` that isn't already `~`-collapsible, or document the
   intentional scope in a comment.

3. **`check_docs_path_gitignored` has no test for the not-a-git-repo case** (`check_gitignored`
   L86-96; tests in `test_check_docs_path_gitignored.py`). [Low impact, test gap not bug] When
   `docs_path.parent` is not inside a git repo, `git check-ignore` exits 128; the code treats every
   non-zero return as "not ignored" → returns None (silent). That is the correct fail-silent
   behavior for an advisory check, but all five tests either build a real repo or skip the git path
   (`test_silent_when_no_docs_path`, `test_silent_when_docs_path_does_not_exist` both return before
   the subprocess). No test pins the 128/not-a-repo branch, so a future refactor that mis-handles
   non-zero-but-not-1 returncodes wouldn't be caught. Add one test: existing docs_path whose parent
   is not a git repo → asserts None.

4. **Scaffold↔generator format coupling is now load-bearing and only guarded by one byte-for-byte
   test** (`workspace.py` L196-207 vs `generate_ticket_index.py render_index`). [Low impact, noted as
   healthy] The T151 hand-written INDEX.md scaffold must match `render_index([], 0, today)` exactly,
   and `test_index_matches_generator_output` (L104-121) asserts this byte-for-byte — verified passing,
   and `SEVERITY_ORDER = [critical, high, medium, low, unknown]` confirms the section list matches.
   This is good (the drift risk is caught), but the coupling is implicit: a change to `render_index`'s
   header text or section order will break the scaffold and the failure surfaces only in this one
   test, in a different file. No action needed; recorded so the next `render_index` editor knows the
   scaffold mirror exists.

## Suggested Next Session Focus

1. **Restore "or empty" in the session-start SKILL.md fail-closed description (Concern 1).** ~1 word;
   the edit is still staged/uncommitted, so it can be fixed before it lands. Keeps the operator-facing
   doc honest about Invariant 2's actual enforcement (empty state file is blocked).

2. **Add the not-a-git-repo test for `check_docs_path_gitignored` (Concern 3).** ~1 test; pins the
   fail-silent branch that the current five tests skip.

3. **Decide the `is_machine_specific_path` prefix scope (Concern 2).** Either broaden beyond the four
   POSIX prefixes or add a comment stating the home-rooted scope is intentional. Lowest priority — the
   check is advisory and the realistic miss is narrow.

Carry-forward status: the one S26 item with teeth — Concern #1, the `_append_resolution` fresh-ticket
guard that could leave `(Fill in on close.)` in closed tickets — is **resolved**. Verified directly:
`close_ticket.py` L193-199 now uses the blockquote-aware "nothing to preserve" pattern
(`> \*\*Client-visible:\*\*.*?\n(?:> .*\n)*` + the placeholder), matching `strict`'s shape as S26
recommended. S26 Concerns #2 (`_resolution_section` fence-terminator) and #3 (`--harness` bypass) are
out of S29's diff and remain as previously dispositioned (low/latent and recorded-decision
respectively); no S29 change touched their surfaces.

---

# Opus Review — S30 2026-06-15

## Invariant Violations

None.

Per-invariant verification against the S30 diff:
- **Inv 1 (workspace↔harness session-number separation):** Holds. The session-numbered
  surfaces this session are read-only or correctly layer-scoped. `check_session_continuity.py`
  *reads* `opened: S<N>` stamps but writes nothing; its defaults point at harness paths and it
  takes `--sessions/--tickets-dir/--archive-dir` overrides for workspace use (diff L236-238,
  SKILL.md L640-644), so it never mixes layers. `telemetry_coverage.py` joins on
  `claude_session_uuid` (a transcript filename), not on `S<N>` — no session-number write. The
  `--sessions` routing the invariant names (`create_ticket.py`/`close_ticket.py`) is untouched
  by S30.
- **Inv 2 (session-type declaration required):** Holds. No S30 change touches
  `check_cross_layer_writes.py` or the `Edit|Write` matcher in `settings.json`. Static analysis
  confirms 45 test files compile and bash blocks pass; the hook's enforcement surface is
  unchanged.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** Holds, and was *amended this session*
  for the multi-repo `--files` case — the amendment and the code agree. `close_ticket.py` now
  commits each git root separately in a loop (diff L411-442) and keeps the no-repo reject (the
  deleted `_check_cross_repo_files` is replaced by `_stage_extra_files` exit-2 on a not-in-a-repo
  path, per the comment at L394-396). The invariant doc (L119-132) was rewritten to permit
  multi-repo via per-root commits while retaining "no silent, no single-index spanning repos" —
  the two teeth are preserved. The deleted `_refuse_multi_root_commit` previously *blocked*
  multi-root; its removal is the intended behavior change, not a regression. Verify: `grep -n
  "sys.exit(2)" scripts/tools/close_ticket.py` and `grep -nE "for git_root in roots"
  scripts/tools/close_ticket.py`.
- **Inv 4 (workspace isolation):** Holds. No S30 change reads workspace repo *content*;
  `check_session_continuity.py` and `telemetry_coverage.py` read only ticket/transcript metadata
  in explicitly-passed dirs. The cross-workspace block in `check_cross_layer_writes.py` is
  untouched.

## Architectural Concerns

1. **`scripts/tools/telemetry_coverage.py` `main()` — `ratio = (captured / native) if native
   else 1.0` reports 100% coverage (and PASSES `--min-coverage`) when the transcript has zero
   tool_use blocks.** [Med] Diff L609: when `native == 0` the ratio is hardcoded to `1.0`, so an
   empty, truncated, or wrong transcript — exactly the failure this smoke check exists to catch —
   prints "coverage 100%" and, under `--min-coverage 0.9`, returns 0 (pass). This is fail-open in
   a tool whose entire purpose is to surface under-capture. A genuinely empty native count is not
   "perfect coverage"; it is "no ground truth to compare against." Fix: when `native == 0`, do not
   claim 1.0 — print an explicit "no native tool_use blocks found; cannot compute coverage" and,
   if `--min-coverage` is set, treat it as a non-pass (return 1) or a distinct exit, rather than
   silently satisfying the threshold. Confirmed from the diff. Verify: `grep -n "else 1.0"
   scripts/tools/telemetry_coverage.py`.

2. **`scripts/tools/telemetry_coverage.py` `_resolve_transcript` — `--uuid` without `--transcript`
   silently falls back to nothing-found when the per-project file is absent, but the same `--uuid`
   is still used as the telemetry join key elsewhere only if a transcript resolves.** [Low]
   Diff L577-579: if `--uuid` is given but `proj_dir/<uuid>.jsonl` does not exist, `_resolve_transcript`
   returns `None`, `main` prints "no transcript found" and returns 0 (advisory). That is acceptable
   fail-silent for an advisory tool, but it means `--uuid X` against a missing project dir produces
   the same "0, looks fine" output as a healthy run with no work — the operator can't distinguish
   "nothing to check" from "I asked for a specific session and it wasn't there." Low severity
   because it is opt-in and advisory; worth a one-line stderr note distinguishing "requested uuid
   not found" from "no transcripts at all." Confirmed from the diff.

3. **`scripts/tools/check_session_continuity.py` `_scan` — ticket-ID fallback `p.name.split("-")[0]`
   assumes a `T###-...` filename when the `id:` frontmatter is absent.** [Low] Diff L227-228: if a
   ticket file has no `^id:\s*(T\d+)` line, the displayed ID is derived from the filename stem
   before the first `-`. For the standard `T165-slug.md` naming this is correct, but a malformed or
   renamed file would print a wrong/empty ID in the collision warning. The collision *detection*
   (the `opened: S<N>` match) is unaffected — only the cosmetic ID label in the warning. The tool
   is advisory (always exit 0), so this is purely a display nit, recorded so the fallback is a known
   decision. Confirmed from the diff.

## Suggested Next Session Focus

1. **Fix the `native == 0 → 1.0` fail-open in `telemetry_coverage.py main()` (Concern 1).** ~3 LoC.
   This is the only finding with teeth: a smoke check that reports 100% on an empty transcript and
   passes `--min-coverage` defeats its own purpose. Make zero-native an explicit "cannot compute,"
   not a pass.

2. **Distinguish "uuid not found" from "no transcripts" in `_resolve_transcript` (Concern 2).**
   ~2 LoC stderr. Optional; keeps the advisory output honest when a specific session is requested.

3. **Carry-forward (S29):** S29's four concerns all target files untouched by S30
   (`workspace.py`, `workspace_config.py`, `repo_hygiene.py`, `check_docs_path_gitignored.py`,
   session-start SKILL.md fail-closed prose). Status: **all still open** — not regressed, not
   resolved, simply not in scope this session. Most actionable remaining item is S29 Concern 1
   (restore "or empty" in the SKILL.md fail-closed description); the S30 SKILL.md edit added step
   10 but did not touch that line, so the prose under-description persists if the S29 edit landed.
   The S26 carry-forwards (#1 resolved at S29; #2/#3 dispositioned) saw no S30 change to their
   surfaces and need no further action.
