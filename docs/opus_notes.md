# Opus Review — S23 2026-05-28

Scope: closed T127–T134 (8 tickets) — full Opus S22 backlog plus T132–T134 opened and closed in-session. Net: new `session_lookup.py` consolidator (T128) absorbs 5 callers; `raise_for_harness._current_session` now fail-closes on missing workspace `sessions.md` (T132); `architecture_invariants.md` finally rewritten with grep-anchored rules and renumbered (Invariant 5 → 4) with name-anchor replacement everywhere live code references the old number (T131); `_extract_proposed_change_acs` carries SR bullets into ticket ACs (T127); `list_raised_concerns.py` buckets unparseable SRs into a dedicated section (T130); Stop hook gains `run_active_work_check` to catch the session-close prepend regression (T134, opened from the workflow-review that found S22→S23 produced an orphan in the Active Work section); session-close skill rewritten to specify REPLACE semantics for Active Work (T133). ~480 LoC production + ~310 LoC tests; 455 passing (+15 net). Strong follow-through — every S22 suggested item landed plus two self-found tickets. A small set of brittleness edges remain in T134's check and T127's section detection.

## Invariant Violations

None.

Checking the new Inv 1–4 against the diff:
- **Inv 1 (workspace↔harness session-number separation):** verification grep #1 (`current_session.py|--sessions` in scripts/tools/*.py) holds — `session_lookup.call_current_session` routes `--sessions PATH` when `sessions_md is not None`, and all four named callers (`raise_for_harness.py`, `surface_workspace_concerns.py`, `create_ticket.py`, `close_ticket.py`) construct the workspace path via `resolve_workspace_sessions_md` or the `internal` argument. Verification grep #2 (`sessions_md is None` in both `raise_for_harness.py` and `surface_workspace_concerns.py`) holds — `raise_for_harness._current_session` exits 2, `surface_workspace_concerns._current_session` returns None. The two semantics are intentionally divergent (tracked-field vs commit-message) and documented in the new Inv 3 verification.
- **Inv 2 (session-type declaration required):** no S23 change touches `_STATE_FILE`, `_HARNESS_PROTECTED`, or `STATE_UNDECLARED` (T131 follow-up renamed Invariant 5 references in this file, but did not alter enforcement). Tests in `tests/test_check_cross_layer_writes.py` were touched only for the name-anchor rename.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** verification grep `sys.exit(2)` in `raise_for_harness.py` + `close_ticket.py` holds — T132 added one in `raise_for_harness._current_session`, T125 from S22 left one in `close_ticket._check_cross_repo_files`. Verification test `tests/test_raise_for_harness.py::TestSessionIdSource::test_refuses_to_fall_back_when_internal_sessions_md_missing` is named in the diff stat (test_raise_for_harness.py: +34 lines, inverted broken-fallback test per the session log).
- **Inv 4 (workspace isolation):** verification grep `_workspace_internal_slug|may not write to other workspace` in `scripts/hooks/check_cross_layer_writes.py` holds — diff only changes the user-visible error string from "Invariant 5 (workspace isolation)" to "the Workspace Isolation invariant".

**Opus S22 Concern #2 retired.** Implementer is correct: `_slug_valid` rejects `__harness__`. The S21/S22 Opus reviews both flagged this as low-confidence (S21: "Diff suggests; low confidence — namespace hygiene"; S22 just carried it forward without re-verifying). Diff confirms the implementer reinvestigated and the regex `^[a-z0-9][a-z0-9-]*$` excludes leading underscore. Removed from carry-forwards.

The placeholder-invariants carry-forward (S18–S22, 5 reviews) is also retired — T131 replaced placeholders with concrete grep-anchored rules and the per-invariant verification commands are reproducible.

## Architectural Concerns

1. **`scripts/hooks/check_session_log.py:155` — `active_work.count("Tickets closed:")` is a substring search with two foreseeable false-positive vectors.** [Medium impact] (a) Narrative content inside Active Work that names the literal phrase — e.g. "Tickets closed: line was duplicated by the bug T134 fixes" — would inflate the count and block session-close. The implementer hit this exact failure mode in S23 per the prompt. (b) A future session author who writes prose like "Tickets closed in earlier sessions:" would also trip the check. Tighter shape: anchor at line start with a regex `re.compile(r"^Tickets closed:", re.MULTILINE)` so only the canonical reporting line counts, not narrative substrings. As-is, the check punishes any session that talks about itself at the meta level — including this Opus review section if it appeared inside Active Work. Fix: replace `.count(...)` with `len(re.findall(r"^Tickets closed:", active_work, re.MULTILINE))`.

2. **`scripts/hooks/check_session_log.py:124-131` — `_extract_active_work_section` terminates at the first `\n---` found in the body.** [Medium impact, latent] The section terminator search picks whichever comes first between `\n## ` and `\n---`. If a session author writes a thematic break (`---`) inside their Active Work narrative (e.g. between "Files changed" and "Tests"), the function silently truncates and the integrity check operates on a partial section — drift after the truncation point goes undetected. Also: if Active Work ever contains a fenced code block whose body contains `---` (YAML frontmatter sample, hook config snippet, the embedded ticket template), the section ends mid-fence. The Stop hook then fails open for everything past the cut. Fix: scan for `\n## ` only (the next H2 is the canonical terminator since `## Session Log` always follows); the `---` arm exists because of the current docs/sessions.md layout where `---` precedes `## Session Log`, but H2 is the more reliable anchor and `## Session Log` will always be there in a well-formed file.

3. **`scripts/tools/promote_raised_concern.py:115` — `## Proposed change` matched only by exact lowercased equality.** [Low impact, brittleness] `stripped.lower() == "## proposed change"` will fail for any reasonable variant: `## Proposed change:`, `## Proposed Changes` (plural), `## Proposed change (urgent)`, trailing whitespace beyond `.strip()`'s trim. When the match fails, `_extract_proposed_change_acs` silently returns `[]` and `create_ticket.py` falls back to the default `- [ ] (fill in)` placeholder — same as if the SR had no Proposed change section. Two failure modes converge into one observable behavior, so the operator can't tell from outside which case they're in. Loosen to `stripped.lower().rstrip(":").startswith("## proposed change")` or emit a debug log when the section is found but yields zero items.

4. **`scripts/tools/session_lookup.py:35-37` — bare `except Exception` for YAML parse errors with a comment "yaml.YAMLError and unexpected parse errors".** [Low impact] The `import yaml` is inside the try block (line 29), so an `ImportError` on `yaml` import would fall through `except ImportError` correctly, but a `KeyError`/`AttributeError` inside `cfg.get("docs_path")` would also be swallowed by the bare-Exception arm with a misleading "could not parse" message. Tighten to `except yaml.YAMLError` and let unexpected errors crash visibly. The risk surface is small (we already validated `cfg` is from `yaml.safe_load`), but defensive bare-Exception in shared infra is the kind of thing that hides a real bug for sessions.

5. **`scripts/tools/list_raised_concerns.py:67` — `sorted(raised_dir.glob("*.md"))` introduces a deterministic order, but `_severity_key` `sort` was already applied per-workspace.** [Cosmetic, low impact] The new `sorted()` call at glob time is good (filename-deterministic) but the in-workspace `items.sort(key=_severity_key)` is INSIDE the for-loop on line 80, so it re-sorts after every item is appended. That's O(N² log N) for a per-workspace list — fine at current scale (single-digit SRs per workspace) but a code-smell pattern. Move `items.sort` outside the loop. Diff confirms this is pre-existing (the `items.sort` line wasn't changed in T130), so it's not a new defect, but T130 modified surrounding logic without fixing it.

6. **`scripts/tools/raise_for_harness.py:79` — the fail-closed error message names `workspaces/<slug>/internal/sessions.md` as the lookup target even when `workspace.yaml` declares a `docs_path` override.** [Low impact] When `resolve_workspace_sessions_md` returns None because the `docs_path`-overridden path is missing, the error message in `_current_session` interpolates the *default* `ROOT / workspaces / slug / internal / sessions.md`, not the actual override target the user configured. Operator chases the wrong path. Either thread the resolved-but-missing path through, or have `resolve_workspace_sessions_md` return a sentinel-or-pair distinguishing "no yaml override, default missing" from "yaml override declared, override missing". Diff confirms only the slug is passed into `_current_session`, so the error path doesn't know which target failed.

## Suggested Next Session Focus

1. **Tighten the T134 substring check (Concern #1) and the section terminator (Concern #2).** ~10 LoC + 2 tests. These are coupled: both are brittleness in the same new hook check that the implementer already hit a false positive on. Use `re.MULTILINE` anchored matches for "Tickets closed:" and prefer `## ` over `---` as the section terminator. The hook is the last line of defense against the prepend regression — when it false-positives, operators will be tempted to bypass it; when it false-negatives, the regression that motivated T134 returns silently.

2. **Loosen `_extract_proposed_change_acs` section matcher (Concern #3).** ~3 LoC + 1 test. Variants of "## Proposed Change" / trailing colon / pluralization should all match. The current strict match makes the new T127 capability silently no-op on most real SRs that don't use the exact-case canonical heading.

3. **Lock the docs_path-aware error message in `raise_for_harness._current_session` (Concern #6).** ~5 LoC. If we're going to fail closed and tell the user which file to create, name the actual file. Currently misleads when `docs_path` is in play. Low priority but easy.

No multi-session carry-forwards remain after S23. Both the placeholder-invariants and the `__harness__` slug carry-forwards retired this session — first time in 6 reviews the carry-forward list is empty.

---

# Static Analysis — S24 2026-05-30

Docs-only session (SR triage + analysis). No code changed; full Opus review skipped per protocol.

```
PASS  30 test files compile cleanly (no SyntaxError)
PASS  no datetime.utcnow() in production code
PASS  9/9 bash blocks in SKILL.md files syntax-valid
All 3 checks PASS.
```

No new findings. S23 Opus carry-forwards remain as the Suggested Next Session Focus above.

---

# Opus Review — S25 2026-05-31

Scope: closed T135/T136/T137/T138/T139 — the full scrabble-score SR-008/009/010/011
workspace-blind-tooling sweep. Net: telemetry attribution rewritten from per-file-path
(T057) to active-session via `workspace_config.read_session_state` + a new
`claude_session_uuid` live join key (T137); `analyze_tool_log` gains a `(workspace,
session)` pair filter with gated auto-detect (T137); `create_ticket._next_id` scoped
per-layer (T135); `generate_ticket_index` fail-closes on bare workspace/undeclared
invocation (T136); new `run_hook.sh` wrapper resolves hook paths cwd-independently via
`$CLAUDE_PROJECT_DIR` + `$0` (T138); `raise_for_harness --session` bypasses the
last-logged+1 off-by-one during close (T139). ~1556 insertions / 547 deletions across
32 files; 477 tests pass (+22 net). Clean, well-documented sweep — every SR in the
batch landed, and the implementer left honest in-code notes on the residual skew and
the duplicated tri-state reader. Two spin-outs (T140/T141) correctly deferred.

## Invariant Violations

None.

Per-invariant verification against the S25 diff:
- **Inv 1 (workspace↔harness session-number separation):** grep #1 holds —
  `close_ticket.py:221` and `create_ticket.py:117` both route `--sessions
  <internal>/sessions.md`; `session_lookup.py:42-46` is the single consolidator that
  appends `--sessions PATH` only when given a workspace path. T135's `_next_id(internal)`
  rework keeps the per-layer counter (its docstring explicitly cites the
  `current_session.py --sessions` per-layer model). No harness `S<N>` is written into
  workspace state and vice versa in the diff.
- **Inv 2 (session-type declaration required):** grep #2 holds — the
  `check_cross_layer_writes` matcher is still registered on `Edit|Write`
  (settings.json:34), now dispatched through `run_hook.sh`. The hook body is unchanged:
  `_STATE_FILE`, `_HARNESS_PROTECTED`, `STATE_UNDECLARED` all present, `sys.exit(2)` at
  line 96 on the mismatch/undeclared path. The new T136 `workspace_config.read_session_state`
  reads the SAME `.claude/.active_workspace` tri-state (see Concern #2). Enforcement logic
  untouched — but its *invocation wrapper* changed; see Concern #1.
- **Inv 3 (fail-closed on workspace-boundary ambiguity):** grep #3 holds —
  `raise_for_harness.py:194` exits 2 on a malformed `--session` value (T139's new flag
  validates `S\d+` before stamping the tracked `raised:` field, so the explicit-value
  path can't smuggle garbage in), plus the pre-existing exits at 83/88. `close_ticket.py`
  retains its cross-repo guards (12 `sys.exit(2)` sites). T136's `generate_ticket_index`
  bare-invocation path also fail-closes (`sys.exit(2)`) for workspace/undeclared sessions
  rather than overwriting the harness INDEX — a new, correct application of this invariant.
- **Inv 4 (workspace isolation):** grep #4 holds — `check_cross_layer_writes.py:155`
  still blocks workspace-A→workspace-B `internal/` writes via `_workspace_internal_slug`.
  No diff change to the isolation logic; same wrapper caveat as Inv 2 (Concern #1).

Test suite: `477 passed` (ran with `--ignore=tests/test_workflow_orchestrator.py` per
the prompt).

## Architectural Concerns

1. **T138 inverted the enforcement hook's failure mode from fail-closed to fail-open
   — `scripts/hooks/run_hook.sh:31` + `.claude/settings.json:34`.** [Medium impact,
   defense-in-depth gap] T138 correctly fixed the SR-011 deadlock (cwd drifting into a
   workspace repo made `git rev-parse --show-toplevel` resolve to a repo with no harness
   hooks → `python3: can't open file` → exit 2 → every tool blocked). The fix —
   `$CLAUDE_PROJECT_DIR` to locate the wrapper, `$0`-relative to locate the script — is
   sound, and a *deliberate* `exit 2` still propagates correctly (`exec python3` replaces
   the process, so the python exit code is returned verbatim; I verified this). But the
   *script-not-found* path now changes behavior asymmetrically by hook type. Pre-T138, a
   missing/unresolvable hook script produced a non-zero exit → the write was **blocked**.
   Post-T138, `[ -f "$script" ] || exit 0` (and the settings.json `|| exit 0`) means a
   missing script → **silent exit 0** → write proceeds. For `log_tool_usage` and
   `regenerate_ticket_index` this fail-open is correct (best-effort telemetry/index must
   never block a tool). But the SAME blanket fail-open is applied to
   `check_cross_layer_writes` — the *enforcer* of Invariant 2 and Invariant 4. If that
   one script ever fails to resolve (rename, partial checkout, perms, a future refactor
   that moves it), workspace isolation silently vanishes instead of blocking. In normal
   operation the `$0`-relative resolution makes the script always present, so this is a
   defense-in-depth gap rather than an active hole — but the harness's own threat model
   (Inv 4: "cross-workspace data leakage is a confidentiality violation") is exactly the
   case where you want loud failure. Recommendation: differentiate enforcement hooks from
   best-effort hooks. The enforcement hooks (`check_cross_layer_writes`, and arguably
   `check_ticket_acs`/`check_fix_commit_has_code`) should fail closed — or at minimum emit
   a visible stderr warning AND exit 2 — when their script can't be resolved; only the
   telemetry/index hooks should silently `exit 0`. A small allowlist of fail-open hook
   names in `run_hook.sh`, defaulting to fail-closed, would express the policy in one place.

2. **Two parallel copies of the `.active_workspace` tri-state reader now exist, and one
   of them is the Inv 2/4 enforcer.** [Low-Medium impact, tracked debt] T136 added
   `workspace_config.read_session_state()` (workspace_config.py:147-163), which the
   implementer's own comment (lines 131-132) notes "Mirrors the tri-state read in
   `scripts/hooks/check_cross_layer_writes.py`; a future pass could have the hook import
   these instead of keeping its own copy." The hook's copy is at
   check_cross_layer_writes.py:34-57. They agree today (same sentinel `__harness__`, same
   `.strip()`, same empty→undeclared rule), but they are the attribution authority (which
   layer a telemetry record / index / SR is stamped with) and the enforcement authority
   (which writes get blocked). If they ever drift — a future fourth state, different
   whitespace handling, a sentinel rename done in one file — the tool that *attributes* and
   the hook that *blocks* would disagree about what layer the session is, and the
   disagreement would be silent. The implementer flagged this honestly as deferred debt,
   so this is tracked, not a missed defect. Recommendation: have the hook import
   `workspace_config.read_session_state` (the hook already manipulates `sys.path` for ROOT;
   the import is cheap and fail-open-able), collapsing to a single source of truth. T136's
   note already anticipates this — promote it to a ticket so it doesn't rot.

3. **`claude_session_uuid` join key rests on an unverified Claude Code internal
   assumption — `log_tool_usage.py:266`.** [Low impact] The new field stores
   `os.environ.get("CLAUDE_CODE_SESSION_ID", "")` on the documented premise that this value
   "IS the native JSONL transcript filename" (line 23). If that premise is wrong (env var
   unset in the hook subshell — note CLAUDE.md records `$CLAUDE_PROJECT_DIR` was *empty* in
   a hook subshell as of S3, later found present on 2.1.158; env availability in hooks has
   bitten this harness before — or the filename≠UUID), the field is silently dead weight: it
   degrades to `""` and the deferred T141 join finds nothing. Low risk because it fails
   gracefully and the join is explicitly deferred. Recommendation: before building T141,
   empirically verify the env var is populated in the `log_tool_usage` subshell AND that a
   live `.git/session_tool_log.jsonl` record's uuid matches an actual transcript filename
   on disk. One `/verify`-style check, not a code change. If it's empty in practice, drop
   the field rather than carry a dead join key.

Note (acknowledged, not a concern): the `_session_from_sessions_md` last-logged+1
off-by-one (log_tool_usage.py docstring) is pre-existing (path-based stamping had it too),
documented in-code, and explicitly deferred — the `claude_session_uuid` field is the
intended future reconciliation key (T141). Correctly out of scope for T137.

## Suggested Next Session Focus

1. **Differentiate enforcement vs. best-effort hooks in `run_hook.sh` (Concern #1).**
   ~8 LoC + 2 tests (script-present → runs; enforcement-script-missing → exit 2 + stderr;
   best-effort-script-missing → exit 0). This is the only Medium finding and it sits
   directly on the Inv 2/4 trust boundary that T138 touched. The existing
   `tests/test_hook_command_resolution.py` is the natural home for the cases.

2. **Collapse the duplicated tri-state reader (Concern #2).** Promote workspace_config.py's
   line 131-132 note to a ticket and have `check_cross_layer_writes.py` import
   `read_session_state`. ~10 LoC net negative. Single source of truth for the
   attribute-vs-block layer decision; closes the silent-divergence risk before a fourth
   state or a rename introduces it.

3. **Verify the `claude_session_uuid` premise before investing in T141 (Concern #3).**
   A read-only `/verify`: confirm `CLAUDE_CODE_SESSION_ID` is populated in the hook subshell
   and that a logged uuid maps to a real transcript filename. Cheap insurance against
   building the T141 join on a `""` field.

No multi-session carry-forwards remain (S23's three items were the carry-forward and S24
was docs-only). All three S25 items are net-new from this session's diff.
