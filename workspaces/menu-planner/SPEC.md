# Menu Planner — Product Spec

> Household recipe library + weekly dinner planner for two people. PWA-first,
> Supabase backend, LLM-powered recipe ingestion. Native iOS wrapper is a
> possible later upgrade, not a commitment.

---

## One-Line Pitch

"Share a recipe link from your phone and it appears — parsed, metric, categorised —
in a shared library you plan the week's dinners from."

---

## Problem Statement

Recipes live scattered across browser tabs, screenshots, and "I'll remember that
site." Weekly meal planning happens ad hoc, the same six dishes recur, and the
shopping list is reconstructed from memory in the supermarket. Existing recipe
apps either lock data into their own cloud, do a poor job of parsing arbitrary
sites, keep imperial units, or are built for food bloggers rather than a
two-person household.

---

## Users & Design Principles

Two users: Martin and his partner. This is household infrastructure, not a
product for the App Store.

1. **Partner-zero-config is requirement #1.** Her surface: browse recipes, see
   the week, tick off shopping items, answer "what do you fancy this week?".
   One-time magic-link login, never sees settings, never does admin.
2. **Low friction beats features.** Anything that requires sustained manual
   upkeep (see: inventory, cut below) is presumed dead on arrival.
3. **The pipeline does the tedious work.** Unit conversion, categorisation, and
   ingredient structuring happen at import time, automatically — never as a
   manual chore.

---

## Decisions Locked (S0, 2026-06-11)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Platform | **PWA** (installable web app), not native iOS | No Apple Developer Program ($99/yr) needed, no 90-day TestFlight expiry chore, instant updates, partner setup = "open link → Add to Home Screen". Native wrapper possible later; backend carries over unchanged. |
| Backend | **Supabase** (hosted free tier) | Postgres + magic-link auth + row-level security + realtime out of the box. Zero ops. Chosen over PocketBase (self-hosted = permanent "is my server okay?" tax) and Firebase (lock-in, NoSQL). |
| Obsidian | **Dropped** | Original idea; abandoned in favour of an app the partner can actually use. No vault, no sync plugins. |
| Recipe parsing | **Hosted, server-side** — Supabase Edge Function calling the Claude API | Keys stay off phones; phones stay thin. |
| RAG | **Not building it.** Index-in-prompt instead | Household corpus will be a few hundred recipes for years — the whole index (titles, tags, times, history) fits in one Claude prompt. Embeddings/vector search only earn their keep past ~1,000 recipes. Revisit then. |
| Inventory + restock notifications | **Cut, not deferred** | Manual inventory tracking requires updating stock after every shop and every meal; nobody sustains it. Shopping list gives 80% of the value with zero upkeep. Revisit only if shopping-list use sticks for 2+ months. |
| Planning scope | **Dinner-first** | Week view plans dinners. Data model has a meal-slot field so lunch/other can come later, but the UI doesn't pay for them yet. |

---

## Feature Scope

### Phase 0 — Proof of Pipeline (de-risk before building anything)

The only real unknown is parse quality. Before any app code:

| # | Deliverable | Notes |
|---|-------------|-------|
| 1 | Parse 10 recipe URLs from sites actually used by the household | Collect real URLs first |
| 2 | JSON-LD extraction + Claude normalisation prototype (script is fine) | Measure: fields extracted, conversion correctness, classification sanity |
| 3 | Go/no-go + model choice (Haiku vs Sonnet) based on results | Cost per parse measured |

**Exit criteria:** ≥8/10 real-world URLs parse into complete, correctly
converted recipes.

### Phase 1 — MVP

| # | Feature | Priority | Notes |
|---|---------|----------|-------|
| 1 | Supabase project: schema, RLS by household, magic-link auth | P0 | Both phones logged in |
| 2 | `POST /parse` Edge Function (URL → structured recipe) | P0 | The keystone — see Pipeline section |
| 3 | "Add Recipe" iOS Shortcut (share sheet → POST url) | P0 | iOS PWAs can't join the share sheet; Shortcut is functionally identical |
| 4 | Recipe library: list, detail view, filter by complexity / time / cuisine / dish type / protein | P0 | The categories are the user's stated taxonomy |
| 5 | Weekly dinner plan: assign recipes to days, next-week view | P0 | Shared — partner's phone updates via realtime |
| 6 | PWA installability (manifest, icons, Add to Home Screen flow) | P0 | Partner onboarding must be one link |
| 7 | Manual recipe entry/edit | P1 | For family recipes with no URL |
| 8 | Original-units toggle on recipe view | P1 | Conversion errors always recoverable |

### Phase 2 — The Payoff Features

| # | Feature | Priority | Notes |
|---|---------|----------|-------|
| 9 | Auto shopping list from the planned week | P0 | Merge same canonical ingredients across recipes; pantry-staples exclusion list; shared tick-off |
| 10 | "What do you fancy this week?" → suggested menu | P1 | Preference prompt → `POST /suggest` → Claude over recipe index → proposed week, user accepts/swaps |
| 11 | Web push notifications (iOS 16.4+) | P2 | e.g. "no plan for next week yet" Sunday nudge |
| 12 | Cooked-it tracking (mark plan entry cooked; last-cooked on recipes) | P1 | Feeds Phase 3 suggestions |

### Phase 3 — Earned Features

- Proactive weekly menu suggestions using cooking history (rotation, seasonality,
  "haven't had fish in a while").
- Smarter search if the bank grows (full-text first; embeddings only past ~1k recipes).
- **Native iOS wrapper** — only if the PWA proves itself and widgets/native feel
  are missed. Requires Apple Developer Program ($99/yr). Backend unchanged.

### Cut List (decided, not backlog)

- Inventory tracking + restock notifications (see Decisions Locked).
- Public/multi-household support, sharing recipes with friends, social anything.
- Meal types beyond dinner in the UI (model supports them; UI doesn't).

---

## Technical Architecture

### Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | SvelteKit PWA | Small bundle, fast on mobile; final framework call confirmed at Phase 1 start |
| Hosting (frontend) | Cloudflare Pages | Free, instant deploys |
| Backend | Supabase free tier | Postgres, auth, RLS, realtime, Edge Functions |
| Auth | Supabase magic links | No passwords; one household, two users |
| LLM | Claude API (model per Phase 0 benchmark; start Haiku, escalate to Sonnet if quality demands) | Parsing, conversion, classification, menu suggestion |
| Recipe extraction | schema.org/Recipe JSON-LD first; readability-extracted text fallback | The vast majority of recipe sites embed JSON-LD |
| Push | Web Push (iOS 16.4+ home-screen PWAs) | Phase 2 |

```
iPhone (Martin)        iPhone (partner)
  PWA + "Add Recipe"     PWA
  iOS Shortcut             │
        │                  │
        ▼                  ▼
  ┌──────────────────────────────────┐
  │ Supabase (one household)         │
  │  Postgres + RLS + realtime       │
  │  Edge Fn: POST /parse            │
  │  Edge Fn: POST /suggest          │──→ Claude API
  └──────────────────────────────────┘
```

### Data Model (Postgres, RLS scoped by household_id throughout)

```sql
households(id, name, created_at)
profiles(id REFERENCES auth.users, household_id, display_name)

recipes(
  id, household_id, title, source_url, image_url, servings,
  prep_minutes, cook_minutes, total_minutes,
  complexity        -- enum: easy | medium | involved
  cuisine           -- text: italian, thai, polish, ...
  dish_type         -- enum: main | soup | salad | side | dessert | bake | breakfast | other
  protein           -- enum: meat | fish | vegetarian | vegan
  instructions      -- jsonb: ordered steps
  notes, rating, times_cooked, last_cooked_at,
  parse_meta        -- jsonb: parser version, model used, raw JSON-LD, warnings
  created_by, created_at
)

recipe_ingredients(
  id, recipe_id, position, group_name,
  canonical_name,        -- "chicken thigh", normalised for merging
  quantity NUMERIC, unit TEXT,
  original_text TEXT,    -- "6 oz boneless chicken thighs" — always preserved
  note TEXT
)

week_plans(id, household_id, week_start DATE, UNIQUE(household_id, week_start))
plan_entries(id, week_plan_id, day DATE, slot DEFAULT 'dinner', recipe_id, note, cooked BOOL)

shopping_lists(id, household_id, week_plan_id, created_at)
shopping_items(id, list_id, canonical_name, quantity, unit, checked BOOL,
               source_recipe_ids UUID[], manually_added BOOL)

pantry_staples(household_id, canonical_name)   -- excluded from shopping lists
```

`recipe_ingredients.canonical_name` is the quiet keystone: structured at parse
time by the LLM, it makes shopping-list merging ("2 onions" + "1 onion" → "3
onions") nearly free in Phase 2.

### Ingestion Pipeline (`POST /parse`)

```
{url} or {url, html}            ← Shortcut can send page content if the
        │                          server-side fetch is bot-blocked
        ▼
fetch page (UA, timeout)
        ▼
extract schema.org/Recipe JSON-LD ──absent──→ readability text extraction
        ▼
ONE Claude call (structured output schema):
  • normalise title, servings, times, steps
  • convert all units to metric (rules below)
  • classify: complexity, cuisine, dish_type, protein
  • structure ingredients: canonical_name + quantity + unit + original_text
        ▼
deterministic verification pass:
  code re-derives every numeric conversion from original_text;
  mismatches → warning flags in parse_meta, original shown in UI
        ▼
insert recipe + ingredients; realtime delivers to both phones
```

Response: `{recipe, confidence, warnings[]}`. Low confidence → recipe saved
with a "check me" badge rather than rejected.

### Unit Conversion Rules

Originals always stored (`original_text`) and viewable; conversions are
display-canonical.

| From | To | Rounding |
|------|----|----------|
| °F / gas mark | °C | nearest 10 °C (400°F → 200°C) |
| oz | g | nearest 5 g (6 oz → 170 g) |
| lb | g / kg | nearest 25 g; ≥1 kg shown as kg |
| cups/tbsp/tsp (solids) | g | per-ingredient density table (flour 120 g/cup, sugar 200 g/cup, butter 225 g/cup, …); amounts ≤4 tbsp stay as spoons |
| fl oz / cups (liquids) | ml | nearest 25 ml (1 cup → 250 ml) |
| inches | cm | nearest 0.5 cm |
| sticks of butter | g | 1 stick → 115 g |

Sanity rules: never round to zero; quantities <5 g keep 1 g precision; spoon
measures are already metric-friendly and stay as-is.

### Menu Suggestion (`POST /suggest`, Phase 2)

No RAG. The request carries a compact index of the whole library (id, title,
tags, total_minutes, last_cooked_at) plus the user's free-text preferences
("something light, one fish dish, nothing over 30 min on weekdays") and recent
plan history. Claude returns a proposed week as recipe ids + reasoning. User
accepts or swaps individual days. Revisit with embeddings only if the corpus
passes ~1,000 recipes.

---

## Costs

| Item | Cost |
|------|------|
| Supabase free tier | £0 (500 MB DB; 2-user scale is nowhere near limits) |
| Cloudflare Pages | £0 |
| Claude API | ~£0.01–0.05 per recipe parse; suggestions pennies/week |
| Domain (optional) | ~£10/yr |
| Apple Developer Program | £0 — **not needed** unless/until Phase 3 native wrapper |

Known fine print: Supabase free-tier projects pause after ~1 week of zero
activity. Weekly household use prevents this; a scheduled ping (cron) is the
belt-and-braces fix.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Recipe sites bot-block server-side fetches | Import fails on some sites | Shortcut falls back to sending page HTML from the phone; manual paste as last resort; Phase 0 measures real-world hit rate |
| LLM mangles a quantity during conversion | Wrong amounts in a cooked dish | Deterministic verification pass on every numeric conversion; originals stored and one tap away |
| PWA feels second-rate, partner stops using it | Project fails its #1 requirement | Phase 3 native wrapper is the escape hatch; backend unaffected. Keep the PWA fast and boring. |
| iOS PWA limitations shift (Apple policy) | Install/push flows break | Monitored; native wrapper path always available |
| Supabase free-tier pause | App "down" at the supermarket | Weekly use + scheduled ping; data is plain Postgres, exportable anytime |
| Magic-link emails rate-limited (Supabase built-in SMTP is limited) | Login friction | Sessions are long-lived (login is rare); custom SMTP only if it ever bites |

---

## Success Criteria (personal-app scale)

- Phase 0: ≥8/10 real recipe URLs parse correctly (fields, conversions, categories).
- Partner installs and uses the app with zero coaching beyond "open this link."
- 8 consecutive weeks with a planned menu actually cooked from.
- Shopping list used in the supermarket (not reconstructed from memory) for a month.
- ≥50 recipes in the bank within 3 months of MVP.

---

## Open Questions

- [ ] **App name.** "Menu Planner" is a working title. Decide before the domain purchase, not before code.
- [x] **Recipe source languages.** RESOLVED (Phase 0, S1): **English-only.** The household cooks from English sites; no non-English sources. Polish dropped.
- [x] **Frontend framework** — RESOLVED (Phase 1 start, S1): **SvelteKit** (small bundle, fast on mobile, hosted on Cloudflare Pages).
- [x] **Claude model for parsing** — RESOLVED (Phase 0, S1): **Sonnet 4.6** (`claude-sonnet-4-6`). 9/9 clean vs Haiku 8/9 (Haiku doubled a ¼-cup flour). Cost negligible at household volume (~3p/parse). Haiku stays a fallback if volume ever changes the maths.
- [x] **Serving scaling** — RESOLVED (Phase 1 start, S1): **store as-published, scale at display time.** Keeps `original_text` honest; the recipe's own servings count drives display-time scaling.
