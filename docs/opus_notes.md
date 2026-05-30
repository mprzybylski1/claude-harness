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
