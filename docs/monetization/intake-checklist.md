# Intake & Delivery Checklist — "Claude Code Setup" Engagement

Internal playbook. One file per client engagement; copy this template, fill it in,
keep it as the source of truth for that engagement.

---

## Client meta

- **Client:** _____
- **Contact:** _____ (role: _____)
- **Repo language/stack:** _____
- **Team size:** _____ (of which active Claude Code users: _____)
- **Engagement start:** _____
- **Engagement end (Day 5):** _____
- **Support window ends:** _____
- **Invoice sent (50% upfront):** [ ] / amount: _____
- **Invoice sent (50% on completion):** [ ] / amount: _____

---

## Day 0 — Discovery call (30 min, free)

**Goal:** decide fit. Walk away if it's not.

Qualification questions:

- [ ] Are you already using Claude Code, or evaluating?
- [ ] How big is the repo (LOC, services, monorepo or single)?
- [ ] What's your current AI-assisted dev workflow? ("None" is fine; "we ban it" is a red flag)
- [ ] Who on your team will own the harness after handoff? *(If no one — disqualify.)*
- [ ] What does "Claude Code working well for us" look like in 90 days?
- [ ] Any compliance constraints? (SOC2, HIPAA, GDPR, sovereign cloud)
- [ ] Hard no's: technologies, frameworks, workflows that are off-limits

Fit signals (need at least 3):

- [ ] Lead engineer is bought in, not just the CTO
- [ ] Repo is in git, hosted somewhere (GitHub/GitLab/Bitbucket)
- [ ] Has existing test suite (any state — even broken)
- [ ] Has at least one clear architectural concern they want enforced
- [ ] Team can commit to 90-min training within the 5-day window

Disqualify if:

- [ ] Asking for "build my app with AI"
- [ ] No technical owner identified
- [ ] Stack is something exotic with no Python tooling story (harness uses Python hooks)
- [ ] Wants this to "replace" code review or QA

**Decision:** _____ (proceed / decline / refer to: _____)

---

## Day 1 — Onboarding call (90 min, billable)

**Pre-call prep (you, ~30 min):**

- [ ] Skim repo: README, top-level structure, primary languages
- [ ] Note obvious invariant candidates (e.g., "all DB writes go through `db/` package")
- [ ] Draft 3–5 candidate static-analysis checks for their stack
- [ ] Prepare blank `CLAUDE.md` and `architecture_invariants.md` for shared editing

**On the call (with lead engineer):**

- [ ] Walk the repo top-down — get the 5-minute architecture tour
- [ ] Fill `CLAUDE.md` together:
  - [ ] Commands (run/test/build/deploy)
  - [ ] Architecture (1–3 paragraphs)
  - [ ] Key constraints & honest limitations
  - [ ] Phase roadmap (where are they now, what's next)
  - [ ] Configuration (env vars, secrets, config files)
- [ ] Draft `architecture_invariants.md`:
  - [ ] 5–15 things Claude must never break, written as testable assertions
  - [ ] Each invariant: how is it currently enforced? (test, lint, manual, nothing)
- [ ] Confirm static-analysis checks to enable in `harness.yaml`
- [ ] Confirm `code_paths` and `tickets_dir`
- [ ] Identify first real ticket they want to ship using the harness

**Post-call (you, same day):**

- [ ] Send recap email: what was agreed, what's next, what you need from them
- [ ] Ask for: repo access (read+write to a setup branch), any auth tokens needed

---

## Days 2–4 — Setup (async, billable)

Per-client setup checklist (~6–8 hours):

- [ ] Create branch `claude-harness-setup` in their repo
- [ ] Copy harness scaffolding (skills, scripts, hooks, doc templates) per README graft workflow
- [ ] Customize `.claude/settings.json` — merge with any existing hooks they have
- [ ] Install `commit-msg` hook
- [ ] Configure `harness.yaml`:
  - [ ] `session_close_prefix`
  - [ ] `code_paths` (from Day 1)
  - [ ] `tickets_dir`
  - [ ] `static_analysis_checks` (from Day 1)
- [ ] Commit `CLAUDE.md` (draft from Day 1, polished)
- [ ] Commit `docs/architecture_invariants.md` (draft from Day 1, polished)
- [ ] Seed `docs/sessions.md` with S001 stub
- [ ] Seed `docs/opus_notes.md` empty
- [ ] Seed `docs/system_state.md` empty
- [ ] Create first real ticket in `docs/tickets/open/` (the one identified Day 1)
- [ ] Run a dry-run session on throwaway branch — confirm hooks fire, INDEX regenerates,
      commit-msg validates, session-close skill runs end-to-end
- [ ] Push setup branch, open PR with checklist of what was installed
- [ ] Send client a "ready for Day 5" email with the PR link

Red flags during setup (escalate to client before continuing):

- [ ] Their existing `.claude/settings.json` has hooks that conflict
- [ ] Pre-commit framework already installed (husky/pre-commit/lefthook) — need merge strategy
- [ ] Python 3.10+ not available in their dev environment
- [ ] Monorepo with multiple project roots — needs harness-per-subdir decision

---

## Day 5 — Team training (90 min, billable)

**Agenda:**

- [ ] 10 min — Why the harness exists (problem → solution framing)
- [ ] 15 min — Live walkthrough: `/session-start`, what it reads, what it surfaces
- [ ] 15 min — Ticket lifecycle: open → ACs → implement → close, hooks in between
- [ ] 10 min — `/implement-background` demo on a small ticket
- [ ] 10 min — `/session-close` demo + Opus review walkthrough
- [ ] 20 min — Their lead engineer runs a real session on a real ticket, you watch
- [ ] 10 min — Q&A, gotchas, "what if X"

**Post-training:**

- [ ] Send final invoice (50%)
- [ ] Send written handoff: list of files installed, where to look when X breaks,
      the 3 most common gotchas you've seen
- [ ] Confirm Slack/email support channel for the 2-week window
- [ ] Calendar reminder: support window end date

---

## Days 6–19 — Support window

Track every support interaction here (so you know what to fix in the harness):

| Date | Question / Issue | Resolution | Time spent | Harness improvement? |
|------|------------------|------------|------------|----------------------|
|      |                  |            |            |                      |

---

## Day 20 — Wrap

- [ ] Send wrap-up email: what they should do next, the 2 patterns you saw work
      best for their team
- [ ] Ask for written testimonial (1–2 sentences, name + title + company)
- [ ] Ask for referral (one engineering leader they know who might benefit)
- [ ] Soft-pitch the $400/mo monthly-review add-on (only if they're getting value)
- [ ] Log the engagement in your own pipeline tracker
- [ ] Update harness based on the support-window improvements column above

---

## Definition of done (engagement complete when all true)

- [ ] Harness installed and merged to client's main branch
- [ ] `CLAUDE.md` and `architecture_invariants.md` exist and are non-empty
- [ ] At least one ticket has been opened, worked, and closed by the client's team
      using the harness
- [ ] At least one `/session-close` has been run successfully by the client
- [ ] Final invoice paid
- [ ] Testimonial requested
