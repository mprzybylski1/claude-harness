# App Portfolio

Lightweight portfolio layer that tracks all app ideas and projects across workspaces.

## What This Is

A pipeline for evaluating, speccing, and tracking iOS app ideas. Each app that passes the stress test gets its own workspace under `workspaces/`. This directory holds:

- **portfolio.md** — master tracker (status, sector, monetization, metrics)
- **templates/spec.md** — standardized spec template for new ideas
- **rejected/** — ideas that failed the stress test (with rationale)

## Process

### 1. Ideation

Identify a gap in a specific sector. Quick evaluation:
- Is the pain real and recurring?
- Is there a dominant native iOS app already?
- Can a solo dev build an MVP in 2-4 weeks?

### 2. Stress Test

Before committing to a spec, run two analyses:
- **Competitor analysis** — who exists, what they charge, what users complain about
- **"Why doesn't it already exist?"** — identify structural barriers (retention, unit economics, distribution, data moats, AI substitution risk)

If structural barriers are fatal → save to `rejected/` with rationale.

### 3. Spec

Use `templates/spec.md` to write a full product spec covering:
- Problem, target user, competitive landscape
- Feature scope (MVP vs. future), technical architecture, data model
- Build plan (week-by-week), monetization, App Store strategy
- Success metrics and open questions

### 4. Workspace Creation

Once specced, create a workspace under `workspaces/<app-name>/` with:
- `workspace.yaml` — workspace config
- `CLAUDE.md` — app-specific handoff instructions and build commands
- `SPEC.md` — the product spec (from step 3)
- `sessions.md` — session log
- `tickets/INDEX.md` — ticket index for implementation

### 5. Development Handoff

The SPEC.md + CLAUDE.md in the workspace should be sufficient for a dev session to start coding on day 1. Key requirements for handoff readiness:
- Technical decisions locked (stack, min iOS, architecture)
- Data model defined with code
- Week-by-week build plan with daily deliverables
- Build/test commands documented in CLAUDE.md

### 6. Post-Launch Tracking

After release, update `portfolio.md` metrics:
- Days to MVP, days to App Store live, days to first paid user
- Monthly downloads, revenue, App Store rating, CAC

## Evaluation Criteria

When comparing ideas, weight these factors:

| Factor | Weight | Why |
|--------|--------|-----|
| Ongoing engagement (daily/weekly use) | High | Retention drives ratings, ASO ranking, and word-of-mouth |
| No dominant incumbent | High | Easier to capture market share |
| AI substitution resistance | High | ChatGPT can answer static-knowledge problems for free |
| Data moat (grows with use) | Medium | User-generated data is defensible; static databases aren't |
| One-time purchase viable | Medium | Subscription fatigue is real; one-time exploits it |
| Viral/shareable hook | Medium | Reduces CAC; Reddit/TikTok-friendly content |
| Solo-dev buildable (2-4 weeks) | Medium | Speed to market matters more than feature depth |
| Willingness to pay | Medium | Target users with disposable income |

## Existing Apps

| App | Workspace | Status |
|-----|-----------|--------|
| SubTracker | [workspaces/sub-tracker](../workspaces/sub-tracker/) | Spec complete — ready for development |
| Retention App | [workspaces/retention-app](../workspaces/retention-app/) | Parked — build after SubTracker ships |
