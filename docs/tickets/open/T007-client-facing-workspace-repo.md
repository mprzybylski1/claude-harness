---
id: T007
title: Client-facing workspace repo and progress.md generation
severity: medium
status: open
phase: 2
layer: fullstack
opened: S002 2026-05-25
closed:
---

## Problem
Clients have no visibility into work in progress. Session notes and Opus findings are
internal and too raw to share. A client-facing layer — clean progress summaries and ticket
status — pushed to a private git remote the client can access, is a differentiator that
builds trust and reduces check-in overhead.

## Acceptance Criteria
- [ ] `workspace.yaml` supports optional `client_remote` field (git remote URL for client-facing repo)
- [ ] `workspaces/<slug>/client/` directory structure: `progress.md` (generated), `tickets/` (curated view)
- [ ] At session-close, harness generates `client/progress.md` from the session's work: date, tickets closed, summary of what was done (1–3 sentences per ticket), what's next
- [ ] `client/tickets/` contains a filtered view of open and recently closed tickets (no internal notes, no Opus references)
- [ ] If `client_remote` is set in workspace.yaml, harness auto-pushes `client/` to that remote at session-close
- [ ] If `client_remote` is not set, `client/` is generated locally but not pushed (no error)
- [ ] `internal/` is never pushed to `client_remote` under any circumstances
- [ ] Progress summary generation is a separate lightweight pass — not the Opus deep review

## Notes
Depends on T001, T004 (session-close is where generation happens).

The progress summary does not need to be Opus-quality. A structured template filled from
session data is sufficient: date, tickets closed, narrative summary, next session focus.

Client remote setup is intentionally manual (user runs `workspace.py create` and provides
the URL). No automatic repo creation.

Related: T001, T004. See `docs/harness-improvements.md` — this is a generalizable feature.
