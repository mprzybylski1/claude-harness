# Architecture Invariants

These are hard constraints that never change without an explicit decision. Opus checks
these every session. If an invariant is violated, it is treated as a critical blocker —
fix before the next session starts.

---

## Invariant 1 — [Name]

**Rule:** [State the rule precisely. E.g. "No eval() or exec() calls in src/"]

**Why:** [Why this matters. E.g. "Arbitrary code execution in user-supplied strategies is a security and reproducibility risk."]

**Verification:** [How to check. E.g. `grep -r 'eval\|exec' src/` must return empty.]

---

## Invariant 2 — [Name]

**Rule:** [State the rule.]

**Why:** [Why this matters.]

**Verification:** [How to check.]

---

## Invariant 3 — Append-only audit log (if applicable)

**Rule:** Application code may only INSERT into the audit log — never UPDATE or DELETE.

**Why:** Audit records must be tamper-evident. Allowing mutation breaks the audit trail.

**Verification:** `grep -r 'UPDATE\|DELETE' src/audit*.py` must return empty outside of migration scripts.

---

## Invariant 4 — Fail-closed on exceptions (if applicable)

**Rule:** Any exception in a safety-critical path must cause the operation to be rejected
or halted — never silently continue with a default value.

**Why:** Silent defaults mask real failures and allow unsafe state to propagate.

**Verification:** Review exception handling in `src/core/` — no bare `except: pass` or
exception-catch-with-fallback patterns.

---

*Add project-specific invariants above. Remove placeholder sections that don't apply.*
*Keep invariants tightly scoped — each should be checkable by a specific grep or test.*
