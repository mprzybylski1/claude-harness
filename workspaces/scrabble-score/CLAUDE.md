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
