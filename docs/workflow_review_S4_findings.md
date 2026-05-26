# Workflow Review Findings — scrabble-score S4 (harness S15)

Date: 2026-05-26
Source: `/workflow-review` run during scrabble-score session S4. Per SKILL rule, harness-side findings cannot be ticketed from a workspace session — this file is the handoff. Open tickets for these at next harness-root session opportunity, then delete this file.

---

## 1. `generate_ticket_index.py --tickets-dir` scans the passed dir directly, not `open/`

**Severity:** medium-high (causes broken INDEX every session-close in workspaces)

**Observed S4:** `--tickets-dir <ws>/.harness/tickets` (which is what `session-close` SKILL implies) picked up `TEMPLATE.md` as a phantom `T000` row and omitted real ticket `T008`. Workaround: pass `<ws>/.harness/tickets/open` instead. Both `session-start` and `session-close` SKILLs document the broken form.

**Fix options:**
- Script-side: if the passed directory contains an `open/` subdir, scan that instead.
- SKILL-side: update both SKILL.md files to pass `tickets/open/`.

Script fix is cheaper and prevents future SKILL drift.

---

## 2. `close_ticket.py` clobbers harness `docs/tickets/INDEX.md` from workspace context

**Severity:** high (silent corruption of a tracked file; happens every workspace ticket close)

**Observed S4:** `close_ticket.py T009 --workspace scrabble-score` and `close_ticket.py T010 --workspace scrabble-score` each rewrote `<harness>/docs/tickets/INDEX.md` with workspace-session-number values (e.g. "Generated S4", "T073 age = -11 sessions"). Both times I had to `git restore docs/tickets/INDEX.md` before committing.

**Root cause hypothesis:** `close_ticket.py` invokes `generate_ticket_index.py` post-close, defaulting to harness-root paths instead of the workspace's INDEX. Same workspace-blind class as T072/T073.

**Fix:** thread `--workspace` (or auto-detect from the ticket file's path) through to the inner `generate_ticket_index.py` call so it writes to the workspace INDEX, not harness root.

---

## 3. `rotate_opus_notes.py` regex mismatch — never rotates

**Severity:** medium (opus_notes.md grows unbounded; will become a token-cost issue in 10+ sessions)

**Observed S4:** Workspace `opus_notes.md` has two `## Opus Review — S1/S2` sections (h2). Script reported "0 section(s) — no rotation needed." Likely scans for `# Opus Review` (h1).

**Fix:** update the regex to match `^## Opus Review` (h2). Verify against existing files for both harness-root and workspace forms.

---

## 4. `classify_session.py --repo <ws>` returns "docs" for code-changing sessions

**Severity:** low-medium (caused no harm this session because I overrode, but flow-critical for stricter SKILL-following)

**Observed S4:** Three commits to `<ws>/ScrabbleScore/view/GameView.swift` landed before session-close. `classify_session.py --repo <ws>` returned `docs`. Likely cause: script checks `git diff` at invocation time (dirty state only), not commits since last session-close boundary.

**Fix:** classify based on commits since the last `docs:` session-close commit on master (or whatever the boundary marker is), not the current dirty diff.

---

## 5. Background Opus agent denied filesystem access to workspace repo

**Severity:** medium (forces synchronous review on every workspace session-close)

**Observed S4:** Spawned the post-session Opus review with `run_in_background: true` per SKILL. Agent reported `Read` and `Bash` denied for `/Users/mprzybylski/Documents/Projects/ScrabbleScore/`. Foreground retry (same prompt, same paths) succeeded.

**Hypothesis:** Background agents inherit a more restrictive permission set than the main session, and the workspace repo path isn't in the implicit allow-list (only the harness repo is).

**Fix options:**
- Add the workspace repo to the background-agent permission allow-list (read from `workspace.yaml`).
- OR: change `session-close` SKILL to use foreground review for workspace sessions until the permission gap is closed.

---

## Suggested ticket batching at harness-root session

- One ticket per finding (5 total) — they're independent and individually scoped.
- OR: bundle 1 + 2 into a single "fix workspace path-handling in ticket-index pipeline" ticket since they share root cause.

Either way, items 2 and 5 are the highest-value: 2 is silent corruption; 5 doubles session-close latency.
