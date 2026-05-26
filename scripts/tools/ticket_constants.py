"""ticket_constants.py

Shared constants used by ticket index generation and consumers.

Centralising these strings prevents silent breakage when one file is updated
without the other (e.g. the *(none)* marker used in generate_ticket_index.py
and detected by surface_stale_tickets.py).
"""

# Emitted by generate_ticket_index.py in the Aging Tickets section when no
# tickets exceed the aging threshold.  Detected by surface_stale_tickets.py
# to signal a clean state (no stale tickets).
AGING_EMPTY_MARKER = "*(none)*"
