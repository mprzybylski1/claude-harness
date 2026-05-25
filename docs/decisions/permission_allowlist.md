# Permission Allowlist — `.claude/settings.json`

Origin: scrabble-score workspace S2 2026-05-25, via `/fewer-permission-prompts`.

## What's allowlisted, why, and source data

Patterns added to `permissions.allow` in `.claude/settings.json`:

| Pattern | Count (last 50 transcripts) | Why safe to allow |
|---|---:|---|
| `Bash(git add *)` | 18 | Stages files; doesn't mutate working tree, history, or remotes. |
| `Bash(xcodebuild *)` | 19 | iOS build + test driver. Local artefact production only. |
| `Bash(xcrun devicectl *)` | 3 | Lists / installs / launches on locally-paired iOS devices. |
| `Bash(python scripts/tools/generate_ticket_index.py *)` | 16 | Reads tickets, rewrites INDEX.md. Idempotent. |
| `Bash(python scripts/tools/extract_opus_key_sections.py *)` | 9 | Read-only — prints sections from opus_notes.md. |
| `Bash(python scripts/tools/extract_session_brief.py *)` | 5 | Read-only — prints session brief from sessions.md. |
| `Bash(python scripts/tools/surface_stale_tickets.py *)` | 7 | Read-only — surfaces aging tickets. |
| `Bash(python scripts/tools/repo_hygiene.py *)` | 5 | Read-only — repo hygiene checks. |
| `Bash(python scripts/tools/workspace.py *)` | 6 | Read-only — workspace list/show. |
| `Bash(python scripts/tools/workspace_internal_path.py *)` | 5 | Read-only — resolves workspace docs root. |
| `Bash(python scripts/tools/current_session.py *)` | 6 | Read-only — prints session ID. |

Counts reflect a scan of `~/.claude/projects/*/*.jsonl` (10 transcripts, 826 tool
uses total) at the time of analysis.

## What was deliberately not allowlisted

**Already auto-allowed by Claude Code** — no entry needed. Adding one is harmless
but noise:
- `ls` (42), `grep` (32), `git status` (15), `git log` (11), `git diff` (11),
  `wc` (4), `head` (4), `find` (3), `cat` (3), `sed` (2), `git remote` (2),
  `git show` (1).

**Mutating — kept asking on purpose** (review-then-approve discipline):
- `rm` (5), `mv` (3), `git commit` (5), `git mv` (1), `git push` (1),
  `git reset` (1), `git checkout` (1).

**Arbitrary code execution — never allowlist as wildcard:**
- `Bash(python *)`, `Bash(python3 *)`, `Bash(bash *)`, `Bash(sh *)`,
  `Bash(npx *)`, `Bash(bunx *)`, `Bash(uvx *)`, etc.
- The skill enumerates this category. Specific scripts (e.g.
  `Bash(python scripts/tools/foo.py *)`) are safe; the interpreter itself is not.

## Where this lives

`/.claude/settings.json` at harness root (project-scope). Reasons over the
alternatives:

- **Not `~/.claude/settings.json`** — these patterns reference paths
  (`scripts/tools/*.py`) that only exist in this repo. User-scope would be
  noise in unrelated projects.
- **Not `.claude/settings.local.json`** — that file is for personal overrides
  and is gitignored; this allowlist should be shared with anyone working on
  the harness so the harness's own tooling doesn't prompt them either.
- **Not the workspace's `.claude/`** — same scripts are used from any
  workspace; centralising at harness root means new workspaces inherit the
  allowlist via settings.json discovery (which walks up from cwd).

## Caveat — `cd <path> && python ...` prefix

Most harness-tool invocations follow the form:
```
cd /Users/mprzybylski/PycharmProjects/claude-harness && python scripts/tools/foo.py ...
```

Whether Claude Code's pattern matcher decomposes shell composition (i.e.
checks each `&&`-separated segment against patterns) determines whether
`Bash(python scripts/tools/foo.py *)` actually silences these calls.

If prompts persist for the harness scripts after this allowlist is in place,
either:
1. Invoke from the harness cwd directly without `cd && `, or
2. Widen to a substring-style pattern: `Bash(*python scripts/tools/foo.py*)`.

Try as-is first; only widen if needed.

## Updating

When you notice the same prompt several times across sessions, re-run
`/fewer-permission-prompts` — it will scan transcripts again and propose
additions on top of what's already here.

Never widen a pattern to grant arbitrary code execution. Specific scripts
only.
