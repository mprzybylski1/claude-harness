---
id: T031
title: extract_opus_key_sections.py — header-level mismatch + misleading error path
severity: high
status: closed
phase: 2
layer: infra
opened: S7 2026-05-25
closed: S7 2026-05-25
---

## Problem

`scripts/tools/extract_opus_key_sections.py` (closed in T020 as workspace-aware via
`--opus PATH`) is functionally broken for the only use case T020 was opened to fix:
session-start in a workspace. Surfaced live during scrabble-score S2 — the
session-start skill received an exit-1 error and the Opus review subsections were
not shown in the briefing.

Two distinct bugs in one tool:

**Bug A — header-level regex assumes level-1 only.** Line 73:

```python
review_pattern = re.compile(r"^# Opus Review", re.MULTILINE)
```

Harness-root `docs/opus_notes.md` uses `# Opus Review — S<N>` (level 1).
Workspace `opus_notes.md` (written by `/session-close`) uses
`## Opus Review — S<N>` (level 2), because the workspace file has a
file-level `# Opus Notes — <Project>` title at the top.

So when `--opus` points to a workspace file, the regex matches zero
boundaries → "no '# Opus Review' sections found" error → session-start
skill reports a gap.

**Bug B — error message hardcodes the harness-root constant.** Line 77:

```python
print(f"ERROR: no '# Opus Review' sections found in {OPUS_NOTES}", file=sys.stderr)
```

Should print `path` (the actual file being read), not the hardcoded
`OPUS_NOTES` constant. This made the bug A failure mode look like
"the `--opus` flag is being ignored and the script is reading the
harness-root file instead" — which is what S2 reported back to the user
and what the user-facing summary at session-start said. The flag IS being
honored; the error message just claims the wrong path.

**Bug C — `add_help=False` disables `--help`.** Line 117:

```python
_parser = argparse.ArgumentParser(add_help=False)
```

Combined with `parse_known_args()`, unknown flags and typos are swallowed
silently. `python ... --help` runs the tool against the default path
instead of printing help.

## Acceptance Criteria

- [x] **Bug A:** regex changed to match either heading level — e.g.
      `re.compile(r"^#{1,2} Opus Review", re.MULTILINE)`. Verified against
      both the harness-root and a workspace `opus_notes.md`.
- [x] **Bug B:** error message at line 77 (and any sibling error path) uses
      `path` rather than `OPUS_NOTES`.
- [x] **Bug C:** `add_help=False` removed, OR a `--help` action added
      explicitly. `--help` exits 0 with usage text.
- [x] Test in `tests/` (extend `test_workspace_path_flags.py` or a new file):
      passing `--opus` to a workspace-format file (level-2 headers) extracts
      the sections successfully.
- [x] Existing tests still pass.

## Notes

Severity HIGH because this regressed T020's claimed deliverable for the
first real workspace session. The session-start skill is the most-critical
flow in the harness — the briefing failure here forced a documented "gap"
note and means the user did not see prior-session Opus findings during
S2's briefing.

The header-level divergence between harness-root and workspace
`opus_notes.md` is not the bug — that's a stylistic side-effect of the
workspace file having a parent `# Opus Notes — <Project>` title. The
extractor should accept either.

## Resolution

Bug A: `review_pattern` changed to `r"^#{1,2} Opus Review"`. After finding the
latest boundary, `sub_prefix` is derived from whether the boundary line starts
with `## ` (workspace) or `# ` (harness-root), then used as `^{sub_prefix} (.+)$`
to match subsections at the correct level.

Bug B: error message now prints `path` (the resolved file being read) instead of
the hardcoded `OPUS_NOTES` constant.

Bug C: `add_help=False` removed; `parse_known_args` replaced with `parse_args`.

Test: `TestExtractOpusKeySectionsWorkspaceFormat` added to
`tests/test_workspace_path_flags.py` — three cases covering level-2 header
parsing, correct error path in stderr, and `--help` exit 0.
