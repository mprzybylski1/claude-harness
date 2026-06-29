# Menu Planner

Household recipe library + weekly dinner planner for two people. PWA + Supabase +
Claude-powered recipe ingestion. Personal infrastructure, not a commercial product.

This workspace is managed by the Claude harness.

## Session protocol

At session start, run `/session-start`. Context files for this workspace:

- `sessions.md` — session log
- `tickets/INDEX.md` — ticket overview
- `opus_notes.md` — Opus review history
- `SPEC.md` — full product spec (decisions, architecture, phases, pipeline design)

## Project Status

**Phase:** Phase 0 GO (S1 2026-06-11, parse PoC T001 — Sonnet 9/9; **model locked
Sonnet 4.6**). **Phases 1 & 2 shipped and deployed** (S2–S17): Supabase schema + RLS
+ magic-link auth, `POST /parse` Edge Function, recipe library + filters, weekly
dinner plan (realtime), PWA, the **offline epic** (app-shell SW + read cache + write
outbox), **auto shopping list** (rolling-window merge by `canonical_name`),
`POST /suggest` preference-driven menu suggestion, **`improve`-with-AI**,
paste-to-recipe, multi-meal days, and **multi-skin theming** (T103). Live on
Cloudflare Workers + hosted Supabase (ref `hyoapyzqfjkhvrcwszgf`). **Multi-language
sources (T092):** ingredient name split into a source-language grammatical
`display_name` (shown) + a hidden **English** `canonical_name` merge key.

**Active direction (S18 2026-06-29):** see
`~/MenuPlanner/docs/superpowers/specs/2026-06-29-handoff-actioned-roadmap.md` — the
ordering loop (canonical↔SKU keystone + Sainsbury's deep-link search), break-the-rut
suggestions, and a **gated** e-ink-cooking-device + business-validation exploration
(passion-mode default; business behind money-on-the-line gates).

## Repos

_See workspace.yaml for declared repos._

Repo path is `~/MenuPlanner` (branch `main`). Remote:
`git@github.com:mprzybylski1/MenuPlanner.git` (private). Monorepo layout:
`app/` (SvelteKit PWA — T005), `supabase/` (migrations + Edge Functions —
T002/T003), `parsing/` (Python parse prototype + 34 tests + model/cost
benchmark; **FROZEN** historical Phase-0 artifact — the `/parse` Edge Function
was originally ported from it but is now canonical and has diverged (T092
English-merge-key + display_name; T095). Don't port prompt/schema changes back here).

## Key Context for Future Sessions

### What This Is

A two-user household app:
1. Share a recipe URL from the phone → hosted pipeline parses it (JSON-LD +
   Claude) into a structured, **metric-converted**, categorised recipe.
2. Shared recipe library with filters: complexity, time, cuisine, dish type,
   meat/fish/vegetarian.
3. Weekly dinner plan both partners see (Supabase realtime).
4. Phase 2: auto shopping list from the planned week; preference-driven menu
   suggestions.

### What It Is NOT

- Not an Obsidian vault (explicitly dropped — partner usability won).
- Not a native iOS app (PWA-first; native wrapper is a Phase 3 *option* — no
  Apple Developer Program exists or is needed yet).
- Not a RAG system (index-in-prompt; corpus too small for embeddings).
- No *sensed/manual* inventory tracking (cut — see SPEC.md Decisions Locked).
  *Inferred* inventory (delivery − cooked, zero-upkeep) is a sanctioned future
  software feature (roadmap T113), not a reversal.
- **Multi-household live (T082–T084):** allowlisted onboarding (each permitted email
  gets its own isolated household) + **copy-only** recipe sharing (share link →
  recipient gets an independent fork; no shared rows, no sync). Still out: public
  open signup, social features, live collaboration. *Depth* (read-only share vs full
  multi-tenant social) is an open question — see roadmap.

### Technical Decisions (Locked S0)

| Decision | Choice |
|----------|--------|
| Platform | PWA, installable on both iPhones via Add to Home Screen |
| Backend | Supabase free tier (Postgres, RLS by household, magic-link auth, realtime, Edge Functions) |
| Frontend | SvelteKit (confirm at Phase 1 start), hosted on Cloudflare Pages |
| LLM | Claude API from Edge Functions only — keys never on phones |
| Share-sheet ingestion | iOS Shortcut → `POST /parse` (iOS PWAs can't register as share targets) |
| Unit conversion | LLM converts at parse time + deterministic verification pass; `original_text` always stored per ingredient |

### Critical Implementation Notes

- **Partner-zero-config is requirement #1.** Her surface: browse, week view,
  shopping tick-off, "what do you fancy?". If a feature needs her to configure
  anything, it's wrong.
- **Phase 0 gates everything.** Parse quality against real URLs is the only
  unknown; do not start app code before the ≥8/10 exit criterion is met.
- **The deterministic conversion check is not optional.** Every numeric unit
  conversion the LLM produces gets re-derived in code from `original_text`;
  mismatches flag `parse_meta.warnings` and surface in the UI.
- **`canonical_name` on ingredients is the keystone** for Phase 2 shopping-list
  merging — parse-time quality there pays off later.
- Supabase free tier pauses after ~1 week of zero activity — scheduled ping
  once the project exists.

## Commands

```bash
# Parse prototype tests + benchmark (Python; run from ~/MenuPlanner)
python -m pytest parsing/tests/                      # 34 conversion-checker tests
python -m parsing.run --urls parsing/urls.txt        # re-run the model/cost benchmark
```

_App (`app/`) and Supabase (`supabase/`) commands land with T005 and T002/T003._

## On-device / headless UI testing (the standard process)

Reusable harness at **`~/MenuPlanner/tools/verify/`** (standalone, own deps, not in the
app build). Use it to test UI changes on a phone — or fully headless — against the
**local** Supabase stack, with a permanent seeded test user and **no real email**.
Full detail + gotchas: `tools/verify/README.md`. Recorded in memory:
`reference_menuplanner_headless_verification`.

Prereqs: local stack up (`supabase status`), and once: `cd tools/verify && npm install
&& npx playwright install chromium`.

```bash
cd ~/MenuPlanner/tools/verify
npm run seed         # permanent test user (cookbook-verify@example.com) + recipes (idempotent)
npm run phone-dev    # serves dev on the Mac LAN IP (temp app/.env.local, auto-removed)
npm run login-link   # prints a ONE-TAP login URL → open on the phone, no OTP typing
npm run shoot        # headless: OTP login + screenshots → out/*.png (+ JSON verdict)
npm run code         # fallback: print the latest OTP from Mailpit to relay
```

- **One-tap link** = single-use token_hash to the app's own `/auth/callback` (verifies
  server-side; works from the phone where the emailed magic link can't). Re-run for a fresh one.
- **Self-verify:** `npm run shoot` writes real PNGs the assistant can read directly +
  send to the operator — no phone needed for a first pass.
- **Real/personal recipes:** drop full recipes in **gitignored** `tools/verify/seed-extra.json`
  (`seed` loads them after the built-ins). To pull one from production, use the **Supabase
  MCP** (`execute_sql` on project `hyoapyzqfjkhvrcwszgf`) — note a `/share/<token>` URL is a
  `recipe_shares.token`, *not* a recipe id (join `recipe_shares` → `recipes`).
- **Exact prod artifact:** for the real built worker, `cd app && wrangler versions upload`
  gives a no-traffic preview URL; promote with `wrangler versions deploy "<version-id>@100" --yes`.
  **Use the `Worker Version ID` printed by `versions upload`** — do NOT pick it from
  `wrangler versions list | head` (that list is OLDEST-first; `head -1` deploys a stale
  version, briefly regressing prod — happened S16).
