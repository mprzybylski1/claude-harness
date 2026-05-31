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
# Fail-open by default: if the named hook script is missing, exit 0. A resolution
# accident must never hard-deadlock the session. A hook's own deliberate `exit 2`
# (a real block) still propagates: `exec python3` replaces this process, so the
# python exit code is returned directly to Claude Code.
#
# Fail-CLOSED exception (T142): a few hooks enforce a confidentiality/safety
# invariant where a *silent* skip is itself a harm. For those, a missing script
# means stderr-warn + exit 2 (block the tool) rather than exit 0. The list is
# deliberately minimal — a hook qualifies only if BOTH hold:
#   (1) silent-skip is a confidentiality/safety harm, AND
#   (2) failing closed still leaves a recovery surface.
# `check_cross_layer_writes` is the sole member: it enforces Invariants 2 & 4
# (session-type declaration + workspace isolation — Inv 4 calls cross-workspace
# leakage a confidentiality violation), and its matcher is Edit|Write only, so a
# fail-closed block leaves Bash (`git checkout`) as a recovery surface. The
# process-discipline hooks are intentionally NOT here: `check_ticket_acs` matches
# Edit|Write|Bash, so fail-closing it would block every recovery surface — an
# unrecoverable deadlock (the SR-011 class T138 fixed). Default fail-OPEN avoids
# that; a future confidentiality enforcer must be added to this list deliberately.
set -u

# Space-delimited; matched with surrounding spaces so names can't substring-collide.
FAIL_CLOSED=" check_cross_layer_writes "

name="${1:-}"
if [ -z "$name" ]; then
    echo "run_hook.sh: missing hook name (fail-open, exit 0)" >&2
    exit 0
fi

here="$(cd "$(dirname "$0")" && pwd)"
script="$here/$name.py"

if [ ! -f "$script" ]; then
    case "$FAIL_CLOSED" in
        *" $name "*)
            echo "run_hook.sh: enforcement hook '$name' not found at $script —" \
                 "failing closed (exit 2). Restore the script via Bash" \
                 "(\`git checkout\`) to recover." >&2
            exit 2
            ;;
        *)
            exit 0
            ;;
    esac
fi
exec python3 "$script"
