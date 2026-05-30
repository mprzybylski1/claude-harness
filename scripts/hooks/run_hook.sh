#!/usr/bin/env bash
# Dispatch a harness hook by name — cwd-independently and fail-open. (T138 / SR-011)
#
# settings.json invokes this as:
#   bash -c 'H="$CLAUDE_PROJECT_DIR/scripts/hooks/run_hook.sh"; \
#            [ -f "$H" ] && exec bash "$H" <name> || exit 0'
#
# Root resolution: the caller locates this wrapper via $CLAUDE_PROJECT_DIR, which
# Claude Code sets in every hook process and keeps FIXED for the session — it does
# not drift when a Bash command does `cd`. This wrapper then re-derives the hooks
# directory from its OWN location ($0), so the python hook path never depends on
# cwd or `git rev-parse` (the SR-011 deadlock: cwd drifting into a workspace repo
# made `git rev-parse --show-toplevel` resolve to a repo with no harness hooks →
# `python3: can't open file` → exit 2 → PreToolUse fail-closed-blocked every tool).
#
# Fail-open: if the named hook script is missing, exit 0. A resolution accident
# must never hard-deadlock the session. A hook's own deliberate `exit 2` (a real
# block) still propagates: `exec python3` replaces this process, so the python
# exit code is returned directly to Claude Code.
set -u

name="${1:-}"
if [ -z "$name" ]; then
    echo "run_hook.sh: missing hook name (fail-open, exit 0)" >&2
    exit 0
fi

here="$(cd "$(dirname "$0")" && pwd)"
script="$here/$name.py"

[ -f "$script" ] || exit 0
exec python3 "$script"
