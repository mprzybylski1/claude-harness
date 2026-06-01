# Opus Review — S26 2026-05-31

Scope: cleared the full S25 Opus backlog and both spin-outs — closed T142/T143/T140/T144/T145,
verified+deferred T141, opened T146. Net: `run_hook.sh` keeps its default fail-OPEN but gains
an explicit `FAIL_CLOSED` allowlist (exactly `check_cross_layer_writes`) so a missing enforcement
script stderr-warns + exit-2-blocks (T142, directly answering S25 Concern #1); the cross-layer
hook drops its private `_read_session_state`/`_HARNESS_SENTINEL` and imports
`workspace_config.read_session_state` as the single source of truth, mapping import failure to
exit 2 (T143, S25 Concern #2); `create_ticket.py` bare invocation is now session-aware —
fail-closed for workspace/undeclared, with a new explicit `--harness` bypass for programmatic
callers (T140, Inv 3 extension); `close_ticket.py` gains `--append` to preserve work-authored
Resolution content (T144) and a clearer no-placeholder error (T145); T141's join-key premise was
verified and deferred under YAGNI (S25 Concern #3 retired). One impl-review fix updated Invariant
2's verification grep for the T143 refactor. ~894 insertions / 74 deletions; static analysis
clean (33 test files compile, no `datetime.utcnow()`, 9/9 SKILL bash blocks valid). A focused,
high-discipline session — every S25 concern was retired at its root, and the T142 narrowing
(3 hooks → 1) is backed by an explicit matcher-by-matcher deadlock analysis rather than a
blanket policy. One real defect in the new `--append` path (Concern #1 below) and a recurring
section-terminator pattern (Concern #2).

## Invariant Violations

None.

Per-invariant verification against the S26 diff:
- **Inv 1 (workspace↔harness session-number separation):** Holds. No S26 change touches the
  `--sessions` routing in `create_ticket.py`/`close_ticket.py` (T140 changed only *layer
  selection*, not the session-ID lookup). The `--harness` bypass question resolves cleanly:
  `_current_session(internal=None)` reads the **harness** `sessions.md`, so a `create_ticket
  --harness` invocation stamps a **harness** `S<N>` into a **harness** ticket — no cross-layer
  number leak even if the flag is misused from a workspace session.
- **Inv 2 (session-type declaration required):** Holds, and the verification grep was correctly
  updated this session to match the refactor. First grep (`read_session_state|STATE_UNDECLARED`):
  diff confirms the hook imports `workspace_config as _wc`, re-exports `STATE_UNDECLARED`/
  `STATE_HARNESS`/`STATE_WORKSPACE` from it (lines 86-88), and calls `_wc.read_session_state(ROOT)`
  at the decision point (replacing the deleted private `_read_session_state`). Second grep
  (`_HARNESS_PROTECTED|sys\.exit`): `_HARNESS_PROTECTED` list is intact; `sys.exit(2)` now also
  guards the import-failure path (line 84), in addition to the unchanged undeclared/mismatch
  blocking paths (`main()` body below line 125 is untouched). The matcher is still `Edit|Write`
  (settings.json unchanged this session). The S25 Concern #2 silent-divergence risk is closed:
  one reader, with a test (`test_hook_has_no_private_tri_state_reader`) asserting the private copy
  and `_HARNESS_SENTINEL` are gone.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** Holds. The verification grep's two
  named tools (`raise_for_harness.py`, `close_ticket.py`) are untouched by S26 in their boundary
  exits, and `close_ticket.py`'s new `_append_resolution` adds *more* exit-2 sites (no
  Resolution header → exit 2; empty/placeholder-only section under `--append` → exit 2). T140
  extends the same principle to a new surface: `create_ticket._resolve_bare_layer` exits 2 for
  both `STATE_WORKSPACE` (refuse to create a harness ticket from a workspace session) and
  `STATE_UNDECLARED`, returning the harness layer only for an explicit `STATE_HARNESS` — a
  correct, idiomatic application of fail-closed-on-ambiguity that mirrors T136's
  `generate_ticket_index`.
- **Inv 4 (workspace isolation):** Holds. The `_workspace_internal_slug` / "may not write to
  other workspace" logic in `check_cross_layer_writes.py` is unchanged by the T143 refactor (the
  diff touches only the tri-state *reader* extraction and the import-failure guard, not the
  cross-workspace block). The run_hook.sh `FAIL_CLOSED` allowlist now makes a missing
  `check_cross_layer_writes` script fail closed, *strengthening* this invariant's enforcement
  relative to S25 (the S25 Concern #1 defense-in-depth gap).

## Fail-closed direction audit (priority-2 check)

Both new fail-closed directions are exit 2 (block), not exit 1 (non-blocking), which is the
correct and load-bearing distinction:
- `run_hook.sh`: missing FAIL_CLOSED script → `exit 2` (lines 173-178). The `case
  "$FAIL_CLOSED" in *" $name "*` match is space-padded on both the list (`" check_cross_layer_writes "`)
  and the pattern, so a hook named e.g. `check_cross` cannot substring-collide into the list.
  Confirmed correct.
- `check_cross_layer_writes.py`: import failure → `sys.exit(2)` with a recovery-pointing stderr
  message (lines 78-84). The in-code comment correctly states the rationale: Claude Code treats
  exit 2 as a block but *any other* non-zero (an uncaught `ImportError` → exit 1) as non-blocking
  → the tool proceeds → fail OPEN. The `except Exception` → exit 2 maps that correctly. Confirmed.
- T142 narrowing (3 → 1 hooks) is sound: `check_ticket_acs` matches `Edit|Write|Bash`, so
  fail-closing it would block every recovery surface (the SR-011/T138 deadlock class).
  `check_cross_layer_writes` matches `Edit|Write` only, leaving Bash (`git checkout`) as a
  recovery surface. Both fail-closed sites point the operator at that Bash recovery in stderr.

## `--harness` bypass audit (priority-2 check)

The `--harness` flag is an unconditional bypass of the session-state check (sets `internal = None`,
the harness layer). It does **not** open a separation hole in the Invariant sense: stamping is
correct (harness `S<N>` into a harness ticket, per Inv 1 above), and the flag is an explicit,
non-default override — the *bare* path fails closed, so nothing silently routes a workspace
session's ticket to harness. The residual gap is policy-vs-mechanism, not invariant: because
`create_ticket` writes via plain `open()` (not Edit/Write), the PreToolUse cross-layer hook cannot
catch a misused `--harness`, so the *only* guard against a workspace session doing harness ticket
work is "don't pass the flag." That is acceptable for a programmatic-caller escape hatch
(`promote_raised_concern.py` is the sole intended user and always creates harness tickets), but it
is an unguarded surface — see Concern #3.

## Architectural Concerns

1. **`scripts/tools/close_ticket.py` `_append_resolution` (~L146-185, per diff hunk `@@ -143`;
   exact source line not verifiable without reading the file) — its "nothing to preserve" guard
   misses the real fresh-ticket shape; `--append` on a fresh ticket leaves the
   `(Fill in on close.)` placeholder in the closed ticket.** [Low impact (audit smudge,
   opt-in), but a confirmed correctness bug with a test that masks it] The guard is
   `if not body or re.fullmatch(r"\(Fill in on close[^)]*\)", body)`. But a *fresh* ticket's
   Resolution body is not the bare placeholder — per the embedded template (context lines
   1170-1175) it is the `> **Client-visible:**` blockquote *followed by* the placeholder.
   `body = section.strip()` therefore starts with `>`, so `re.fullmatch` against the
   `(Fill in...)` pattern returns `None`, `body` is non-empty, and the guard **does not fire**.
   `--append` then preserves the blockquote+placeholder and appends the summary after it,
   producing a closed ticket that still contains `(Fill in on close.)`. The asymmetry is the
   tell: replace-mode's `strict` regex explicitly accounts for the optional client-visible block
   (`(?:> \*\*Client-visible:\*\*.*?\n(?:> .*\n)*\n)?`), but the append guard does not. **Test
   gap (priority-4):** `test_append_errors_when_only_placeholder` uses `_ticket("(Fill in on
   close.)")` — a bare placeholder with no blockquote — so it passes while never exercising the
   shape a real ticket has. The new safety-relevant path has false-confidence coverage.
   Recommendation: reuse the same optional-blockquote-aware pattern as `strict` when deciding
   whether the section is "only the placeholder", and add a test whose Resolution body is the
   full template shape (blockquote + placeholder) under `--append`.

2. **`scripts/tools/close_ticket.py` `_resolution_section` (~L146-160, per diff hunk `@@ -143`;
   exact source line not verifiable without reading the file) — its `\n##\s` terminator is the
   same fenced-code false-terminator pattern Opus flagged in S23 Concern #2.** [Low impact,
   latent] `nxt = re.search(r"\n##\s", after)` treats the first `## ` at line start as the end of
   the Resolution section. A `## ` inside a fenced code block in the Resolution body — a commit
   message snippet, a diff hunk header is `@@` not `##` so that's safe, but a markdown sample or
   a shell heredoc with `## ` would trip it — truncates the section there, so the append lands
   before the fence and any real content after it gets shoved past the (mis-detected) section
   boundary. This is mitigated because Resolution is usually the last `##` section (`nxt` is then
   `None` and the whole tail is the section), so the bug only bites when a later `##` section
   exists *and* the Resolution body contains a fenced `## `. S23 Concern #2 flagged the identical
   shape in `_extract_active_work_section` (terminating at `\n---` inside a fence); this is a
   recurring section-parsing pattern in the same codebase. Recommendation: low priority given the
   last-section mitigation, but worth a fence-aware scan or at least a code comment naming the
   assumption, so the next section-parser author doesn't copy the pattern a third time.

3. **`scripts/tools/create_ticket.py` `main()` layer-selection branch + `_resolve_bare_layer`
   (per diff hunk `@@ -159` / `@@ -101`; exact source line not verifiable without reading the
   file) — `--harness` is an unguarded mechanism bypass; only
   `promote_raised_concern.py` is the intended caller.** [Low impact, policy-vs-mechanism] Covered
   in the bypass audit above. The flag is correct for its programmatic purpose and the bare-path
   fail-closed default is the right design, but there is no mechanism stopping an interactive
   workspace session from typing `create_ticket --harness` and writing a harness ticket (the
   `open()`-based write is invisible to the Edit/Write hook). Recommendation: no code change
   required this session — the explicit-flag-only surface is an acceptable escape hatch — but if a
   future session wants belt-and-suspenders, `--harness` could additionally assert
   `read_session_state(ROOT) != STATE_WORKSPACE` (allowing harness + undeclared, since the
   programmatic caller may run before declaration) and exit 2 otherwise. Flagging so the bypass is
   a recorded decision, not an unexamined hole.

## Cross-change interaction check (priority-5)

The five tickets touched four shared files; no seams left:
- `workspace_config.py` (T143) ↔ `check_cross_layer_writes.py` (T143): the hook now imports the
  reader the comment promised in S25; `workspace_config.py`'s deferred-debt note was replaced with
  a single-source statement. The two authorities (attribution + enforcement) now share one reader —
  the S25 Concern #2 divergence risk is closed at the source, not merely documented.
- `create_ticket.py` (T140) ↔ `promote_raised_concern.py` (T140): the promoter passes `--harness`
  so it keeps working under the new fail-closed bare default. This is necessary and correct — without
  it, promotion (a harness-layer operation often run mid-session before/independent of state) would
  have started exit-2'ing. Verified the promoter is the one caller updated.
- `run_hook.sh` (T142) ↔ `check_cross_layer_writes.py` (T143): T142 makes the *missing-script* case
  of this specific hook fail closed; T143 makes the *broken-import* case fail closed. The two cover
  complementary failure modes of the same enforcer — no overlap, no gap between them.

## Suggested Next Session Focus

1. **Fix the `_append_resolution` fresh-ticket guard and its masking test (Concern #1).** ~3 LoC +
   1 test. Make the empty/placeholder-only check blockquote-aware (reuse `strict`'s optional
   client-visible pattern) and add a test whose Resolution body is the full template shape under
   `--append`. This is the only confirmed defect and it silently degrades the audit trail (closed
   tickets retaining `(Fill in on close.)`).

2. **Add a fence-aware comment or scan to `_resolution_section` (Concern #2).** ~2 LoC comment now,
   or a small fence-skip later. Cheap insurance against the third recurrence of the section-terminator
   pattern S23 already flagged once.

3. **Record the `--harness` bypass decision (Concern #3).** Either add the
   `read_session_state != STATE_WORKSPACE` assertion, or leave a one-line code comment stating that
   `--harness` is a deliberate unguarded escape hatch for programmatic callers. Lowest priority —
   it's a documentation/decision item, not a fix.

No multi-session carry-forwards: all three S25 concerns were retired this session (Concern #1 → T142,
Concern #2 → T143, Concern #3 → T141 verify-and-defer). All three S26 items are net-new from this
session's diff, and two of the three are Low impact.

---

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
