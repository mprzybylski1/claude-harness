# Architecture Invariants

These are hard constraints that never change without an explicit decision. Opus checks
these every session. If an invariant is violated, it is treated as a critical blocker —
fix before the next session starts.

Every invariant below is checkable by a specific grep or test command.

---

## Invariant 1 — Workspace↔harness session-number separation

**Rule:** A workspace's `S<N>` session ID must never appear in harness-layer state, and
a harness `S<N>` must never appear in workspace-layer state. Each layer maintains an
independent session counter; mixing them destroys the audit trail.

Workspace-layer state (must not contain harness `S<N>`):
- `workspaces/*/internal/sessions.md` (or the `docs_path` override)
- `workspaces/*/internal/opus_notes.md`
- `workspaces/*/internal/tickets/`
- `workspaces/*/raised/*.md` `raised:` frontmatter field
- Git commit messages produced for any workspace-scoped commit

Harness-layer state (must not contain workspace `S<N>`):
- `docs/sessions.md`
- `docs/opus_notes.md`
- `docs/tickets/`
- `docs/archive/`

**Why:** Each session counter is local to its layer (locked S5 2026-05-27). Mixed
numbering makes audit references ambiguous ("which S22?") and obscures who did what,
when. Past incidents: SR-001 was stamped with harness session # before T116; T132
removed a residual silent fallback in `raise_for_harness._current_session`.

**Verification:**
1. `current_session.py` accepts an explicit `--sessions PATH` flag. Every caller that
   writes workspace state must pass the workspace `internal/sessions.md`:
   ```
   grep -nE "current_session\.py|--sessions" scripts/tools/*.py
   ```
   Confirm `raise_for_harness.py`, `surface_workspace_concerns.py`, `create_ticket.py`,
   and `close_ticket.py` route the `--sessions` argument when targeting workspace paths.
2. Workspace-scoped helpers fail-closed when sessions.md is missing rather than fall
   back to harness-global lookup:
   ```
   grep -nE "sessions_md is None" scripts/tools/raise_for_harness.py \
       scripts/tools/surface_workspace_concerns.py
   ```
   Both must show an explicit None-branch that warns and either omits the session ID
   (commit-message use) or exits 2 (tracked-field use). T128 will consolidate the two
   helpers — semantics must remain fail-closed at each call site.

---

## Invariant 2 — Session-type declaration required for protected writes

**Rule:** Every `Edit`/`Write` tool call targeting a harness-protected path or any
`workspaces/*/internal/` path requires `.claude/.active_workspace` to declare the
session type before the write. Missing or empty state file blocks the write
(fail-closed).

Protected paths:
- `docs/tickets/`, `docs/sessions.md`, `docs/opus_notes.md`, `docs/architecture_invariants.md`
- `workspaces/*/internal/` (for any workspace)

State file values:
- `__harness__` → harness-root session (may write to `docs/`, blocked from `workspaces/*/internal/`)
- `<slug>` → workspace session (may write to its own `internal/`, blocked from `docs/` and other workspaces' `internal/`)
- empty / missing → undeclared; all protected writes blocked

`workspaces/*/raised/` is the boundary slot and is always allowed regardless of state.

**Why:** Without explicit session-type declaration, a workspace session can silently
leak writes into harness docs (or vice versa). State file forces an at-most-once
decision per session, made by `/session-start` and verified by the hook on every
write.

**Verification:**
1. The hook is registered as a `PreToolUse` matcher on `Edit|Write` in
   `.claude/settings.json`:
   ```
   grep -A2 "check_cross_layer_writes" .claude/settings.json
   ```
2. The hook reads the state file and enforces the protected-paths list:
   ```
   grep -nE "_STATE_FILE|_HARNESS_PROTECTED|STATE_UNDECLARED" \
       scripts/hooks/check_cross_layer_writes.py
   ```
   Must show: state file path resolution, the protected-paths list above, and
   `sys.exit` (non-zero) on the undeclared / mismatched-slug paths.
3. Hook tests cover the four state × target combinations:
   ```
   grep -nE "def test_" tests/test_check_cross_layer_writes.py
   ```

---

## Invariant 3 — Fail-closed on workspace-boundary ambiguity

**Rule:** Any tool that resolves workspace context, scopes file reads/writes by
workspace, or stamps session/audit fields must reject (exit non-zero) when the
boundary cannot be uniquely identified. Never silently default to a "best guess",
the harness layer, or a different workspace.

Concrete cases this covers:
- Missing workspace `internal/sessions.md` → reject writing a session ID into a
  workspace SR (`raise_for_harness.py`, T132).
- `close_ticket.py --files` paths spanning multiple git repos → reject before
  staging (T125).
- Workspace-scoped diff/context tools targeting a path outside the workspace's
  declared repos → reject via `workspace_config.assert_workspace_boundary`
  (Invariant 5 below).

**Why:** Silent defaults caused workspace SRs to ship with harness session numbers
(pre-T116) and risked cross-repo staged commits (pre-T125). The cost of a wrong
default value is always higher than the cost of an explicit error, because the
wrong value persists in audit trails and downstream parsers.

**Verification:**
```
grep -nE "sys\.exit\(2\)" \
    scripts/tools/raise_for_harness.py \
    scripts/tools/surface_workspace_concerns.py \
    scripts/tools/close_ticket.py \
    scripts/tools/prepare_opus_context.py
```
Each tool listed must have at least one fail-closed `sys.exit(2)` covering the
workspace-boundary ambiguity case for that tool. Tests must cover the rejection
path, not only the happy path.

---

## Invariant 4 — Workspace isolation

**Rule:** Scripts that access repo content must only read paths declared in the
active workspace's `workspace.yaml` repos list. No script may read from a repo
belonging to a different workspace.

**Why:** The harness manages multiple client and personal projects simultaneously.
Client code must never appear in another workspace's Opus review context, session
log, or static analysis output. Cross-workspace data leakage is a confidentiality
violation.

**Verification:**
1. `workspace_config.assert_workspace_boundary(path, workspace)` must be called
   before any file read targeting a workspace repo path. The function exits with
   code 2 if the path falls outside all declared repos.
2. The cross-layer write hook (Invariant 2) also blocks workspace-A sessions from
   writing into workspace-B `internal/` directories:
   ```
   grep -nE "_workspace_internal_slug|may not write to other workspace" \
       scripts/hooks/check_cross_layer_writes.py
   ```
3. Boundary tests:
   ```
   grep -nE "def test_.*boundary|def test_.*workspace_isolation" tests/
   ```

---

*Invariants are intentionally narrow and grep-anchored. If a new rule cannot be
checked by a concrete command, it is policy, not invariant — put it in `CLAUDE.md`
or the relevant skill instead.*
