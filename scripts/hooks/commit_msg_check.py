#!/usr/bin/env python3
"""
commit-msg hook: enforce conventional commit format.

Valid format: <type>[(T###)]: <description>
Valid types: feat, fix, docs, research, refactor, test, chore

Install:
    cp scripts/hooks/commit_msg_check.py .git/hooks/commit-msg
    chmod +x .git/hooks/commit-msg

Or use the wrapper at .git/hooks/commit-msg which calls this script directly.
"""
import re
import sys

TYPES = "feat|fix|docs|research|refactor|test|chore"
PATTERN = re.compile(rf'^(?:{TYPES})(?:\(T\d+\))?:\s+\S')
BYPASS_PREFIXES = ("Merge ", "Revert ", "Initial commit", "fixup!", "squash!")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(0)  # no message file provided (e.g. --amend with no edit)

    msg_file = sys.argv[1]
    try:
        msg = open(msg_file).read()
    except OSError:
        sys.exit(0)

    # Find first non-comment, non-empty line
    first = next(
        (line for line in msg.splitlines() if line.strip() and not line.startswith("#")),
        "",
    )

    if any(first.startswith(p) for p in BYPASS_PREFIXES):
        sys.exit(0)

    if not PATTERN.match(first):
        print(
            f"COMMIT REJECTED — bad message format: {first!r}\n"
            f"Expected: <type>[(T###)]: <description>\n"
            f"Valid types: feat, fix, docs, research, refactor, test, chore\n"
            f"Examples:\n"
            f"  feat(T123): add bootstrap CI kill gate\n"
            f"  fix: correct crontab TZ directive\n"
            f"  docs: S159 session close — workflow hooks implemented\n"
            f"Use --no-verify to bypass (for WIP commits only).",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
