# Upwork Profile Copy — Draft v1

Ready-to-paste copy for setting up the Upwork profile. Two specialty
profiles: a **primary** niche (Claude Code / AI dev workflow) and a
**fallback** niche (Python automation) for slow weeks. Plus a cover-letter
template, rate ladder, and the first 5 saved searches to set up on Day 1.

---

## Profile title (50 chars max)

**Pick one — A/B these in the first 30 days:**

- `AI-Assisted Dev Workflows for Engineering Teams` (49)
- `Claude Code Setup & Python Automation Engineer` (47)
- `AI Dev Workflow Engineer — Claude Code & Python` (48)

Recommended start: **option 1.** Most specific, lowest competition, clearly
signals the niche to algorithmic search. Switch to option 2 if response
rate after 20 bids is under 10%.

---

## Hourly rate ladder

Public rate is a *signal*, not the cap. Set it deliberately.

| Phase | Bids 1–3 | Bids 4–10 | After Top Rated |
|---|---|---|---|
| Public rate | $45/hr | $65/hr | $95/hr |
| Floor for fixed-price | $35/hr effective | $55/hr effective | $80/hr effective |
| Strategy | Win JSS at any reasonable price | Filter; raise on every win | Cherry-pick only |

**Do not go below $35/hr effective on any gig, ever.** Below that you're
buying reviews at a loss and signalling "cheap labour" to the algorithm,
which puts you in front of the wrong clients permanently.

---

## Profile overview (paste into Upwork's "Overview" field)

> I help engineering teams get real, durable value from AI-assisted
> development tools — not the demo-day kind, the kind that survives
> three months of production code.
>
> Most teams plug in Claude Code, Cursor, or Copilot and get a productivity
> bump for two weeks. Then the codebase starts to drift: half-finished
> features, untracked architectural decisions, AI-generated tests that
> pass but assert the wrong thing, invariants that quietly stop holding.
> I fix the workflow layer above the tool, so the productivity gains
> compound instead of decay.
>
> **What I do:**
>
> - Set up Claude Code (or equivalent) properly on your repo: session
>   discipline, ticket workflows, automated post-session reviews,
>   commit-message validation, invariant-check hooks. The same system I
>   built and use on my own production work.
> - Build production Python tooling: CLI tools, automation scripts,
>   internal-developer-platform plumbing, CI/CD glue, hook-based
>   workflow enforcement.
> - Migrate legacy projects to AI-assisted workflows without losing the
>   institutional knowledge buried in the existing code.
>
> **Background:** I built the open-source Claude Harness — a
> project-agnostic session management system for Claude Code with
> structured sessions, automated post-session reviews, a ticket system,
> and hooks that enforce commit discipline and invariant checks.
> Everything I deliver runs on top of that same substrate, so you get
> the audit trail and process discipline as a side effect.
>
> **What I don't do:** chatbots, "build my app with AI," prompt-engineering
> consulting in the abstract, or low-bid generic dev work. If you're
> shopping on price, I'm not your hire.
>
> If you're an engineering leader who wants AI velocity *without* the
> codebase rot — message me with two sentences about your stack and the
> outcome you want.

(Character count: ~1,650 / 5,000 max. Leave room to add a portfolio
reference once you have one.)

---

## Skill tags (max 15)

Add in this order — Upwork weights the first 5 heaviest in search:

1. Claude
2. AI Development
3. Python
4. Workflow Automation
5. DevOps
6. Git
7. CI/CD
8. Bash
9. CLI Application
10. Code Review
11. Software Architecture
12. Static Analysis
13. Pre-commit Hooks
14. Technical Writing
15. Open Source

---

## Specialty profiles

Upwork allows up to 2 specialty profiles. Use both — they appear in
different searches.

### Specialty 1 (primary) — "AI Development Workflow"

- **Title:** Claude Code workflow setup + AI dev hygiene
- **Description:** Short version of the main overview, narrowed to
  Claude Code / AI tooling setup. Lead with the Claude Harness.
- **Skills:** Claude, AI Development, Workflow Automation, Code Review,
  Pre-commit Hooks

### Specialty 2 (fallback) — "Python Automation & Tooling"

- **Title:** Python CLI tools, automation, and dev-process tooling
- **Description:** Lean into the harness's Python tooling work — hooks,
  static-analysis runners, ticket-index generators, CLI scripts. Pitch
  to teams that need internal dev tooling, not customer-facing apps.
- **Skills:** Python, CLI Application, Workflow Automation, Bash,
  Static Analysis

The fallback exists because the primary niche will have slow weeks. The
fallback should net 2–3 bids/week from a different client pool.

---

## Portfolio items (you have no client work yet — here's how to fill it)

Three portfolio items, in priority order:

1. **The Claude Harness itself.** Public GitHub repo, link directly.
   Caption: *"Open-source workflow system for Claude Code. Structured
   sessions, ticket discipline, post-session reviews, commit-message
   and invariant-check hooks. Same substrate I deliver client work
   on."*
2. **A 90-second Loom walkthrough of the harness in action.** Record
   yourself running `/session-start`, opening a ticket, doing a small
   implementation, running `/session-close`, showing the Opus review
   output. Captions over the relevant moments.
3. **One worked case study — even a self-imposed one.** Pick a small
   open-source project, graft the harness onto a fork, deliver one
   meaningful fix using the lite workflow, write up a 300-word
   "before/after" with screenshots. This stands in for a client
   testimonial until you have a real one.

**Do not** put generic GitHub repos, university projects, or
"sample tutorials" in the portfolio. Clients filter those out. The
above three signal craft and process discipline — your actual edge.

---

## Cover letter template (for bid submissions)

Three paragraphs, never longer. ~120 words. Tweak the bracketed parts
per gig — never paste verbatim.

```
Hi [first name if visible, else "there"],

[One sentence demonstrating you read the job post — reference the
specific stack, problem, or constraint they mentioned. NOT "I am
excited about your project."]

[One paragraph on the concrete approach you'd take in the first 4
hours of this engagement — what you'd look at, what you'd ship first,
what you'd want to confirm. Show you've thought about THEIR problem,
not yours. If you can pre-empt one likely objection ("you mentioned
the existing tests are flaky — I'd check X before touching Y"), do it.]

[One sentence on relevant signal — the Claude Harness, prior Python
tooling work, or — once you have it — a specific past gig. Link
included.]

Happy to jump on a 15-min call to sanity-check fit before either of
us commits.

— Martin
```

**Anti-patterns to avoid:**

- "I have X years of experience in Y" — clients don't care, the algorithm
  doesn't reward it.
- "I will deliver high-quality work" — assumed; saying it is a tell that
  you can't.
- Linking your résumé instead of the harness. The harness *is* the
  résumé.
- Submitting more than 10 lines. Long covers signal junior.

---

## Saved searches (set up Day 1, check daily)

Upwork lets you save filtered searches and get email alerts. Set these
five, in order of priority:

1. **`Claude Code` OR `Claude API`** — Hourly + Fixed, $40+ budget,
   any duration. Tiny pool, highest signal.
2. **`AI workflow` OR `LLM workflow` OR `Cursor`** — Hourly + Fixed,
   $40+ budget, Intermediate or Expert level.
3. **`Python` + `automation` + `CLI`** — Hourly only, $40+, Expert level.
   The fallback niche.
4. **`pre-commit` OR `git hooks` OR `static analysis`** — any type,
   $30+. Small but very targeted pool; expect 0–2 hits/week.
5. **`developer experience` OR `internal tools` + `Python`** — Hourly,
   $50+, Intermediate or Expert. Adjacent niche; some of the best gigs
   come from here.

Discipline rule: open the saved-search emails *once* per day, at a fixed
time. Spend max 20 minutes triaging. Bid on at most 2 per session. The
constant Upwork notification loop will eat your week if you let it.

---

## Bid budget & tracking

- **Connects budget:** $30–40/week max. At 12–18 Connects per bid (mid
  range), that's 8–12 bids/week. Don't exceed it — if you can't win at
  10 bids/week, the problem is positioning, not volume.
- **Track every bid** in a spreadsheet (or, ideally, a Python script
  that drops them into a CSV): date, gig title, gig budget, your
  proposed rate, response received? (Y/N), outcome (won / lost / no
  response). Review weekly. After 30 bids you should know your response
  rate and conversion rate to the nearest 5%.

---

## Exit criterion (write this down somewhere durable)

> **I move to direct LinkedIn outreach for the productized harness
> service when I hit 10 completed Upwork gigs OR 90 days from first
> bid, whichever comes first — regardless of how the Upwork pipeline
> is going at that point.**

This is the rule that prevents the platform from becoming a permanent
substitute for the harder direct-sales work. Date it. Commit to it.
