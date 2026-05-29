# Scrabble Score

This workspace is managed by the Claude harness.

## Session protocol

At session start, run `/session-start`. Context files for this workspace:

- `sessions.md` — session log
- `tickets/INDEX.md` — ticket overview
- `opus_notes.md` — Opus review history

## Repos

_See workspace.yaml for declared repos._

## Commands

All commands assume `cwd = ~/Documents/Projects/ScrabbleScore`.

### Run tests (simulator)

The Swift 6 `main actor-isolated conformance of 'Position' to 'Hashable'` warnings
produce ~25 identical lines per `xcodebuild test` run and bury the test summary.
The `grep -E` filter below keeps only the test verdict.

```bash
xcodebuild -project ScrabbleScore.xcodeproj -scheme ScrabbleScore \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' test 2>&1 \
  | grep -E "Test Suite|Test case|Executed|error:|BUILD (SUCCEEDED|FAILED)"
```

iPhone 16 Pro is **not** installed as a simulator on this machine — do not use it
as a destination. List currently-installed simulators with:

```bash
xcrun simctl list devices available | grep -E "iPhone|iPad"
```

#### Stale incremental builds

If `xcodebuild test` reports `"no member"` / `"cannot find"` for a symbol that
is clearly present in source, the incremental build cache is stale — this
happens after edits to `@MainActor`-isolated types, `@Model` types, or any
test-target signature change. `xcodebuild clean` followed by a re-run resolves
it; do this on the first occurrence rather than re-debugging the source:

```bash
xcodebuild -project ScrabbleScore.xcodeproj -scheme ScrabbleScore \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' clean test 2>&1 \
  | grep -E "Test Suite|Test case|Executed|error:|BUILD (SUCCEEDED|FAILED)"
```

### Build & deploy to physical iPhone

Marcin's iPhone udid is pinned below for convenience. If a different device gets
paired in future, fetch the current id with
`xcodebuild -showdestinations -scheme ScrabbleScore` (run from the project root).

```bash
xcodebuild -project ScrabbleScore.xcodeproj -scheme ScrabbleScore \
  -destination 'id=00008140-000270A8143B801C' build
```

The build step is sufficient for code-signing + bundling; launch via Xcode's
Run button to actually install and start the app on the device.

## Cross-repo ticket closes

When a workspace ticket's deliverable lives in the **harness repo** (e.g. an
edit to this `workspaces/scrabble-score/CLAUDE.md`, or to a shared script),
expect **two commits in two repos**:

1. Commit the deliverable in the harness repo first
   (`docs(T###): <description>` or `fix(T###): <description>`)
2. Then run `close_ticket.py T###` in the scrabble repo for the archive move
   (`fix(T###): <title>` — auto-suggested message references the harness
   commit SHA for traceability)

`close_ticket.py --files` only stages files in the workspace repo. There is
no `--harness-files` flag today — track via SR if this becomes painful at
scale.

Example: S9 / T018 — workspace CLAUDE.md edit committed to harness as
`5f36dbc`, archive move committed to scrabble as `3c24ca5`.

The same pattern applies when a workspace ticket-close also **raises a new
SR** in `workspaces/<slug>/raised/`. The SR file lives in the harness repo,
so it needs its own commit there before `close_ticket.py` runs in the
workspace repo — `close_ticket.py --files` will not stage it. Without this,
the SR sits dangling and untracked until the next harness-root session.

Example: S11 / T019 — SR-008 committed to harness as `0392ea6`, ticket
archive move + code/test changes committed to scrabble as `35e6a89`.
