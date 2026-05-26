---
id: T085
title: close_ticket.py --path-only flag to resolve ticket ID to file path
severity: low
status: closed
phase: process
layer: process
opened: S17 2026-05-26
closed: S17 2026-05-26
---

## Problem

When working on a ticket, the model must run `find docs/tickets/open -name "T0XX*"`
(or `ls | grep`) to resolve a ticket ID to its filename before reading it. This ran
3–4 times in S17.

`close_ticket.py` already contains exactly this lookup logic (`_find_ticket()`).
It's not exposed as a standalone query — the tool always proceeds to close the ticket.

## Acceptance Criteria

- [x] `close_ticket.py T079 --path-only` prints the absolute path of the ticket file
      and exits 0. No other output, no side effects.
- [x] Returns exit 1 with the existing "ticket not found" error message if the ID is
      not in any open/ directory.
- [x] When multiple matches exist (ambiguous workspace), exits 1 with the existing
      "use --workspace to disambiguate" error.
- [x] `--path-only` is mutually exclusive with `--resolution` / `--resolution-file`
      (argparse error if combined).
- [x] At least one test covers the happy path (ID → path printed) and one covers the
      not-found case.

## Notes

S17 workflow-review finding #4. `--path-only` is preferred over a separate
`ticket_path.py` script to keep the surface area small.

## Resolution

Added --path-only flag to close_ticket.py: made --resolution group required=False, added --path-only argument, short-circuits in main() to print the ticket path and exit 0 with no side effects. Errors if combined with --resolution. 5 tests in tests/test_close_ticket_path_only.py.

Closed S17 2026-05-26.
