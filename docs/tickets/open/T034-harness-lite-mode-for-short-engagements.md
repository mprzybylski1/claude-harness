---
id: T034
title: Harness Lite — minimal workflow for sub-20hr freelance engagements
severity: medium
status: open
phase: process
layer: process
opened: S7 2026-05-25
closed:
---

## Problem

The full harness ceremony (`CLAUDE.md`, `architecture_invariants.md`, full
`harness.yaml` tuning, all four hooks, full `/session-start` →
`/session-close` lifecycle with Opus review) has a 60–90 minute upfront
setup cost per repo. That cost amortizes well over multi-week
engagements but is *negative ROI* on short fixed-price freelance gigs
(typical 5–40 hour scope).

Concrete failure mode: a $400 Upwork bug-fix gig with an estimated
10-hour scope. Spending 90 minutes setting up the full harness consumes
15% of the engagement budget before any client-visible work happens. The
client doesn't see the value (they paid for a fix, not a workflow), and
the margin tanks.

We need a documented "lite" mode for short engagements that keeps the
high-leverage parts (background implementation, ticket discipline as a
simple TODO list, commit-msg hook) and skips the high-ceremony parts
(invariants doc, full session-close Opus review, multi-session lifecycle
machinery).

This becomes more urgent now that the harness is being positioned for
real freelance work (see `docs/monetization/one-pager.md` and
`docs/monetization/intake-checklist.md`). Without lite mode, the
harness can only sell the high-end $1,200+ engagement; the bootcamp /
Upwork path described in `docs/monetization/` doesn't have a workflow.

## Acceptance Criteria

- [ ] **Decision criterion documented** — explicit rule for when to use
      lite vs full, expressed as an estimated-hours threshold (proposed:
      lite ≤ 20hr, full > 20hr) and a single-vs-multi-session axis.
- [ ] **Minimal subset defined** — explicit list of which components are
      *in* lite mode and which are *out*. Initial proposal to validate:
      - IN: `/implement-background`, `/implementation-review`,
            commit-msg hook, ticket files (used as a flat TODO list
            instead of a backlog), a minimal `CLAUDE.md` (commands +
            architecture only, no invariants/phase/configuration sections).
      - OUT: `architecture_invariants.md`, `/session-start`,
            `/session-close` ceremony, full Opus review, static-analysis
            hooks beyond `commit_msg_check`, `harness.yaml` tuning
            (use defaults).
- [ ] **Scaffolding tool** — `scripts/tools/init_lite.py` (or
      equivalent) that, given a target repo path and a one-line project
      description, drops the minimal set of files in <30 seconds.
- [ ] **Setup time target met** — measured wall-clock time from clean
      repo to first productive Claude session ≤ 15 minutes. Time it on a
      fresh test repo and record the result in the Resolution.
- [ ] **One sample lite-mode engagement** — actually run a small
      self-imposed gig (refactor exercise, throwaway side project, or
      first paid Upwork gig) end-to-end using lite mode. Capture
      friction in `docs/harness-improvements.md`.
- [ ] **README updated** — short section: "Harness Lite (for short
      engagements)" — when to use, how to set up, what's intentionally
      missing.
- [ ] **Upgrade path documented** — one paragraph describing how to
      promote a lite-mode repo to full mode if the engagement grows past
      the threshold (most likely: re-run the graft workflow over the top,
      keeping existing CLAUDE.md and tickets).

## Notes

This ticket is **process / design first, code second.** The first half
of the work is deciding the right minimal subset — once that's pinned
down, the scaffolding script is a 1–2 hour build.

Related but distinct from the productized service work in
`docs/monetization/`: lite mode is the underlying *workflow*; the
productized service is one possible *commercial packaging* of the full
mode. Both share the same harness substrate.

Open questions to resolve while drafting:

- Does lite mode need its own `harness.yaml`, or should it just lean
  entirely on built-in defaults?
- Should `commit-msg` validation be on or off in lite? (Lean: on — it's
  cheap and improves the audit trail at zero ceremony cost.)
- For single-session gigs, are tickets useful at all, or should lite
  mode just use a single `TODO.md` with checkboxes?
- How does lite mode interact with workspaces? Probably: lite gigs live
  in a workspace just like full ones, but the workspace.yaml has a
  `mode: lite` flag that scripts honour to skip ceremony.

## Resolution

(Fill in on close.)
