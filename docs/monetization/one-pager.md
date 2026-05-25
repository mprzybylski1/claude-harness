# Claude Code, Set Up Right — For Your Codebase

**A 5-day productized engagement that turns Claude Code from a chat window
into a disciplined engineering workflow for your team.**

---

## Who this is for

Engineering leaders at 5–50 person product teams who:

- Are already paying for Claude Code (or about to), and want more than vibe-coding
- Have shipped real software and care about review hygiene, audit trails, and not
  letting AI-generated code rot the codebase
- Don't have the time (or the in-house expertise) to design the workflow themselves

**Not for:** solo hobbyists, non-technical founders looking for "an AI to build my app",
or teams who want a Cursor demo.

---

## What you get

A working, opinionated AI-assisted development workflow grafted onto **your** repo,
with **your** stack, in **your** team's hands. Specifically:

| Deliverable | What it means in practice |
|---|---|
| **Harness installed** | Session lifecycle skills, ticket system, Opus review loop, commit-discipline + invariant-check hooks running in your repo |
| **Tailored `CLAUDE.md`** | Project context, commands, architecture, key constraints — written *with* your lead engineer, not a template you'll ignore |
| **Architecture invariants documented** | The 5–15 things Claude must never break in your codebase, enforced by hooks at every session close |
| **Stack-specific static-analysis hooks** | Configured for *your* language/framework — not generic ones you'll disable in a week |
| **90-min team training** | One live session: how to run `/session-start`, manage tickets, trigger background implementation, read Opus reviews |
| **2-week post-engagement support** | Slack/email channel for questions, hook tuning, edge cases as your team beds it in |

---

## Price & timeline

**Flat fee: $1,200 USD** — paid 50% upfront, 50% on completion.

**Timeline: 5 working days from kickoff** — typically two 90-min calls plus async setup.

No retainer, no recurring billing, no "platform fee." If the harness doesn't fit
your team after the 2-week support window, walk away — you keep everything that
was installed.

---

## How it works

1. **Day 0 — Discovery call (30 min, free)**
   Scope your repo, stack, and team size. Confirm fit. If it's not a fit, I'll tell
   you and refer you elsewhere.

2. **Day 1 — Onboarding call (90 min)**
   With your lead engineer: walk the codebase, surface invariants, fill out
   `CLAUDE.md` together, agree on which static-analysis hooks matter for your stack.

3. **Days 2–4 — Setup (async)**
   I install the harness, configure hooks, write your invariants doc, seed your
   first ticket, and run a dry-run session on a throwaway branch.

4. **Day 5 — Team training (90 min)**
   Live walkthrough with your team. They run their first real session on a real
   ticket while I watch and answer questions.

5. **Days 6–19 — Support window**
   Async Slack/email. Hook tuning, ticket workflow questions, "Claude did this
   weird thing" debugging.

---

## Why this is worth $1,200

The teams that get value from Claude Code are the ones that treat it like a
junior engineer who needs structure — not a magic genie. That structure (sessions,
tickets, invariants, post-session reviews, commit discipline) takes 40–80 hours
to design and tune correctly. I've already done that work. You get it in 5 days
for the cost of a single senior-engineer day.

If your team uses Claude Code for even 4 weeks after this engagement, the time
saved on review cycles alone pays back the fee.

---

## What this is *not*

- **Not a Claude Code license** — you bring your own Anthropic subscription
- **Not custom AI development** — I'm not writing your features, I'm setting up
  the system *your team* will use to write them
- **Not a SaaS** — this is a one-time engagement, the harness lives in your repo,
  you own it
- **Not training on prompt engineering** — this is about workflow discipline,
  not prompt tricks

---

## FAQ

**Q: We already have CI, linting, code review. Why do we need this?**
Because none of that catches *AI-specific* failure modes: invariant drift across
sessions, tickets that close with unmet acceptance criteria, half-implemented
features, untracked architectural decisions. The harness adds the layer above
your existing tooling.

**Q: Does this work with Cursor / Cody / Windsurf?**
The harness is built for Claude Code specifically (skills, hooks, session
lifecycle). Most of the discipline (tickets, invariants, review loop) is
transferable, but the automation isn't. If you're committed to another tool,
this isn't the right fit.

**Q: What languages / stacks have you done this for?**
[Fill in as you accumulate engagements. Until then: be honest — "I've built and
tested the harness on Python and TypeScript projects. Your stack is the first
production engagement, so the Day 0 call decides fit."]

**Q: What if our codebase is a mess?**
Better — that's where the discipline pays back fastest. The invariants doc
becomes the "what we wish were true but isn't yet" list, and tickets give you
a structured path to fix it.

**Q: Can you also do the ongoing work?**
Yes, but as a separate engagement (hourly contract SWE). Most clients run the
harness themselves after handoff. About 20% engage me for a monthly review
of their `opus_notes.md` at $400/mo — optional, not pushed.

---

## Next step

[Calendly link] — book a free 30-min discovery call.

Or email: martin.p2907@hotmail.com with a one-paragraph description of your
repo, team size, and stack.
