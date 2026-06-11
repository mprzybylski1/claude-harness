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

**Phase:** Planning — spec written S0 (2026-06-11). Next: Phase 0 (parse-quality
proof against 10 real recipe URLs) before any app code.

## Repos

_See workspace.yaml for declared repos._

Repo path is `~/MenuPlanner` (initialized S0, branch `main`, README + .gitignore
only). Remote: `git@github.com:mprzybylski1/MenuPlanner.git` (private). Planned
layout: monorepo with `app/` (SvelteKit PWA) and `supabase/` (migrations + Edge
Functions).

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
- No inventory tracking (cut, not deferred — see SPEC.md Decisions Locked).
- Single household — no multi-tenant, social, or sharing features.

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

_None yet — repo not created. Update this section when `~/MenuPlanner` exists
(dev server, supabase CLI, test runner)._
