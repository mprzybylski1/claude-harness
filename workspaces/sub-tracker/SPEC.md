# SubTracker — Product Spec

> Privacy-first iOS subscription tracker. No bank account required. No subscription to track subscriptions.

---

## One-Line Pitch

"The subscription tracker that doesn't need your bank account — and doesn't charge you a subscription."

---

## Problem Statement

The average consumer has ~8 active subscriptions costing ~$219/month but estimates spending only ~$86/month (a 2.5x perception gap). 41% report subscription fatigue. Existing solutions force a trade-off:

- **Bank-linked apps** (Rocket Money, Copilot) auto-discover subscriptions but require full financial history access via Plaid, charge $6-15/month, and suffer frequent disconnects.
- **Privacy-first apps** (Bobby, Subtrack) keep data on-device but can't discover forgotten subscriptions, have unreliable notifications, and are often abandoned by their developers.

Nobody solves both: automatic discovery AND full privacy.

---

## Target User

- 25-40 year old professional
- Has 5-15 active subscriptions
- Privacy-conscious (uncomfortable linking bank accounts to third-party apps)
- Experiencing subscription fatigue
- Willing to pay a one-time fee for a tool that saves them money
- Likely frequents r/personalfinance, r/financialindependence, r/frugal

---

## Competitive Landscape

### Direct Competitors

| App | Model | Rating | Reviews | Weakness to Exploit |
|-----|-------|--------|---------|---------------------|
| Rocket Money | $6-12/mo freemium | 4.5★ | ~356K | Requires bank link; subscription irony; hard to cancel their own app |
| Bobby | One-time $1.99-2.99 | 4.7★ | ~7.9K | Notifications broken; long gaps between updates; no iCloud sync |
| Copilot Money | $13/mo or $95/yr | 4.8★ | ~5.7K | Massively overpriced for sub-tracking only; requires Plaid |
| Subtrack Pro | One-time $7.99 | 4.5★ | ~188 | Tiny user base; crash reports; limited features |
| ReSubs | Freemium | — | — | Unclear privacy model for email scanning |

### Our Differentiators

1. **No bank link required** — privacy as a feature, not a limitation
2. **One-time purchase** — exploits subscription fatigue sentiment
3. **Reliable notifications** — where Bobby fails, we succeed
4. **iCloud sync** — zero-cost data portability that Bobby lacks
5. **On-device email scanning (V1.1)** — bridges the discovery gap without Plaid
6. **Actively maintained** — regular updates signal trust

---

## Monetization

### Pricing: $7.99 one-time unlock (non-consumable IAP)

**Free tier:**
- Up to 5 subscriptions
- Basic renewal reminders (day-of only)
- No widgets

**Paid unlock ($7.99):**
- Unlimited subscriptions
- All reminder options (7/3/1/0 days before)
- Home screen widgets
- Custom categories
- CSV export
- Trial countdown with escalating alerts

**Revenue math:**
- Apple takes 15% (Small Business Program) → net $6.79/sale
- Breakeven on $10/day App Store Search Ads ≈ ~45 downloads/month
- Target: 500 paid users in first 3 months = ~$3,395 net revenue

---

## Feature Scope

### MVP (Ship by Week 2)

| # | Feature | Priority | Notes |
|---|---------|----------|-------|
| 1 | Add subscription from 200+ pre-loaded service catalog | P0 | JSON catalog with icons, default prices, categories |
| 2 | Custom subscription entry | P0 | For services not in catalog |
| 3 | Monthly/yearly burn rate dashboard | P0 | The "shock number" — core value prop |
| 4 | Renewal reminders (configurable: 7/3/1/0 days) | P0 | Must be rock-solid — Bobby's #1 failure |
| 5 | Free trial countdown with escalating alerts | P0 | Underserved pain point |
| 6 | iCloud sync via CloudKit | P0 | Solves Bobby's data-loss problem; zero backend cost |
| 7 | Home screen widgets (spend + next renewal) | P0 | High retention driver |
| 8 | One-time IAP paywall (StoreKit 2) | P0 | Non-consumable; no server validation needed |
| 9 | Category grouping (defaults + custom) | P1 | Entertainment, Productivity, Health, etc. |
| 10 | Subscription archive (soft delete) | P1 | Keep history without cluttering active view |

### V1.1 (Week 3-4)

| # | Feature | Priority | Notes |
|---|---------|----------|-------|
| 11 | Bank statement import (PDF/CSV) | P1 | On-device parsing via Vision (PDF OCR) or CSV; surfaces recurring charges as suggestions; no bank link needed |
| 12 | On-device email receipt scanning | P1 | Regex + NaturalLanguage.framework; surfaces suggestions |
| 13 | Screen Time usage correlation | P2 | "Used 2x this month — $7/use"; needs DeviceActivity entitlement research |
| 14 | Price increase detection + history | P1 | Flag deltas on user-confirmed edits |
| 15 | Family sharing (shared iCloud container) | P2 | "Who pays for what" household view |
| 16 | Cancellation flow guides | P2 | Step-by-step for hard-to-cancel services |

### V1.2+ (Post-Launch Backlog)

- Notification summary digest (weekly "you're spending $X this week")
- Spending trends over time (Charts framework)
- App Store subscription auto-import (StoreKit Transaction API for Apple subs only)
- Shortcuts/Siri integration ("How much am I spending on subscriptions?")
- Apple Watch complication (next renewal countdown)

---

## Technical Architecture

### Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| UI | SwiftUI | Modern, less boilerplate, widget support |
| Data | SwiftData (Core Data) | Native persistence + CloudKit sync for free |
| Sync | CloudKit (automatic via SwiftData) | Zero backend cost; iCloud sync out of the box |
| Notifications | UNUserNotificationCenter | Local notifications; no push server needed |
| Widgets | WidgetKit | Small + Medium widgets |
| IAP | StoreKit 2 | Modern async API; no server validation for non-consumables |
| Minimum target | iOS 17.0 | SwiftData requires iOS 17; covers 85%+ of active devices |
| Statement import (V1.1) | Vision (PDF OCR) + CSV parsing | On-device; user shares statement via Files/Share Sheet |
| Email parsing (V1.1) | NaturalLanguage + regex | On-device; no data leaves the phone |

### Data Model

```swift
// Core entity
@Model class Subscription {
    var id: UUID
    var createdAt: Date
    var updatedAt: Date
    var name: String
    var iconName: String?           // SF Symbol or bundled asset
    var colorHex: String?
    var url: String?                // cancel/manage deep link
    var price: Decimal
    var currencyCode: String        // ISO 4217
    var billingCycle: Int16         // BillingCycle enum raw value
    var customCycleDays: Int16?
    var billingAnchorDate: Date     // known/first charge date
    var nextRenewalDate: Date       // computed on save, indexed
    var isTrial: Bool
    var trialEndDate: Date?
    var categoryId: UUID?
    var owner: Int16                // SubscriptionOwner enum
    var notes: String?
    var isArchived: Bool
    var reminderDaysBefore: String? // comma-separated: "7,3,1,0"
    var lastUsedDate: Date?
    var monthlyUsageCount: Int16?
    var priceHistory: [PriceChange]
}

@Model class PriceChange {
    var id: UUID
    var subscription: Subscription
    var oldPrice: Decimal
    var newPrice: Decimal
    var detectedAt: Date
    var currencyCode: String
}

@Model class Category {
    var id: UUID
    var name: String
    var iconName: String?
    var colorHex: String?
    var sortOrder: Int16
}
```

```swift
enum BillingCycle: Int16, Codable, CaseIterable {
    case weekly = 0
    case biweekly = 1
    case monthly = 2
    case quarterly = 3
    case semiannual = 4
    case yearly = 5
    case custom = 6
}

enum SubscriptionOwner: Int16, Codable {
    case me = 0
    case shared = 1
    case partner = 2
    case family = 3
}
```

### Service Catalog Format (bundled JSON)

```json
{
  "id": "netflix",
  "name": "Netflix",
  "icon": "tv",
  "colorHex": "#E50914",
  "category": "entertainment",
  "defaultPrices": [
    { "tier": "Standard with Ads", "price": 6.99, "currency": "USD", "cycle": "monthly" },
    { "tier": "Standard", "price": 15.49, "currency": "USD", "cycle": "monthly" },
    { "tier": "Premium", "price": 22.99, "currency": "USD", "cycle": "monthly" }
  ],
  "cancelUrl": "https://www.netflix.com/cancelplan"
}
```

### Key Technical Decisions

1. **SwiftData over raw Core Data** — less boilerplate, automatic CloudKit integration, modern Swift concurrency support. Trade-off: iOS 17+ only.
2. **Local notifications only** — no push server, no APNS certificates, no backend at all. Limitation: iOS caps at 64 scheduled notifications. Mitigation: only schedule alerts for next 21 days, refresh weekly via background task.
3. **No Plaid / no bank linking** — this is a feature, not a limitation. Zero compliance burden, zero ongoing API costs, zero privacy liability.
4. **Bundled JSON catalog over API** — services don't change fast enough to justify a server. Ship updates with app versions.

### Next Renewal Date Calculation

Critical logic — must handle calendar months correctly (not just +30 days):

```swift
func computeNextRenewal(from reference: Date = .now) -> Date {
    let calendar = Calendar.current
    var candidate = billingAnchorDate

    if isTrial, let trialEnd = trialEndDate, trialEnd > reference {
        return trialEnd
    }

    let component: Calendar.Component
    let value: Int

    switch BillingCycle(rawValue: billingCycle) {
    case .weekly:       component = .day;   value = 7
    case .biweekly:     component = .day;   value = 14
    case .monthly:      component = .month; value = 1
    case .quarterly:    component = .month; value = 3
    case .semiannual:   component = .month; value = 6
    case .yearly:       component = .year;  value = 1
    case .custom:       component = .day;   value = Int(customCycleDays ?? 30)
    case .none:         component = .month; value = 1
    }

    while candidate <= reference {
        candidate = calendar.date(
            byAdding: component, value: value, to: candidate
        ) ?? candidate.addingTimeInterval(86400 * Double(value))
    }

    return candidate
}
```

### Notification Scheduling Flow

```
User saves/edits subscription
    → computeNextRenewal() updates nextRenewalDate
    → NotificationScheduler.reschedule(for: subscription)
    → Remove all pending requests with subscription.id prefix
    → For each day in reminderDaysBefore:
        Schedule UNNotificationRequest at 9:00 AM local, (nextRenewal - N days)
        Identifier: "\(subscription.id)_\(daysBeforeValue)"
    → Cap check: if total pending > 60, drop furthest-out alerts
```

---

## Build Plan

### Week 1: Core Data Model + Main UI

| Day | Deliverable |
|-----|-------------|
| 1-2 | Xcode project setup (SwiftUI, iOS 17+); SwiftData model; CloudKit container; repository layer with CRUD; unit tests for date calculations |
| 3-4 | Service catalog JSON (200+ entries); add/edit subscription flow (search catalog + custom entry); billing cycle picker; trial toggle |
| 5 | Dashboard home screen (burn rate number, sorted list, color-coded urgency); swipe actions; empty state + onboarding |

### Week 2: Notifications + Widget + Ship

| Day | Deliverable |
|-----|-------------|
| 6-7 | Notification engine (permission request, per-sub configurable alerts, trial escalation, batch reschedule); device testing |
| 8 | WidgetKit (small: monthly spend; medium: next 3 renewals); timeline refresh on data change |
| 9 | StoreKit 2 paywall (non-consumable); settings screen (currency, reminder defaults, CSV export, app icons) |
| 10 | QA pass; App Store screenshots; metadata + description; privacy label; submit for review |

### Week 3: V1.1 — Discovery & Intelligence

| Day | Deliverable |
|-----|-------------|
| 11 | Bank statement import (PDF/CSV via Files picker or Share Sheet); Vision framework OCR for PDF, direct parsing for CSV; recurring charge detection via merchant name frequency; suggestion UI for user confirmation |
| 12 | On-device email receipt scanning (Share Sheet intake); regex + NLP extraction for Stripe/Apple/Google/PayPal receipt formats; suggestion UI |
| 13 | Screen Time usage correlation (research DeviceActivity entitlement first; fallback to manual); ROI badge per subscription |
| 14 | Price increase detection (edit-triggered delta detection; history storage; monthly summary notification; price history chart) |

### Week 4: Family + Guides + Launch

| Day | Deliverable |
|-----|-------------|
| 15-16 | Family sharing (CKShare shared container; mine/shared/partner tags; household view; duplicate detection) |
| 17 | Cancellation guides (30-50 hard-to-cancel services; step-by-step with deep links) |
| 18 | Marketing launch (Reddit posts, Product Hunt, App Store Search Ads $5-10/day, short-form video content) |

### Cut List (if behind schedule, cut from bottom)

1. Family sharing → V1.2
2. Cancellation guides → V1.2
3. Screen Time integration → V1.2
4. Email scanning → post-launch update
5. Bank statement import → post-launch update
6. **Never cut:** notifications, widgets, iCloud sync, paywall

---

## App Store Strategy

### Keywords to Target

Primary (high intent):
- "subscription tracker"
- "manage subscriptions"
- "cancel subscriptions"
- "subscription manager"

Long-tail:
- "free trial reminder"
- "recurring payments tracker"
- "bill tracker"
- "subscription spending"

### Positioning in Description

Lead with the two pain points this app solves that competitors don't:
1. No bank account required (vs. Rocket Money, Copilot)
2. No subscription fee (vs. Rocket Money, Copilot, Monarch)

### Launch Channels

| Channel | Approach |
|---------|----------|
| Reddit | r/personalfinance, r/financialindependence, r/frugal, r/ios — genuine "I built this" posts |
| Product Hunt | Launch day post with demo GIF |
| App Store Search Ads | $5-10/day on primary keywords; optimize after 2 weeks of data |
| TikTok/Reels | "Total annual spend reveal" shock content — the number is the hook |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| App Store rejection | Blocks launch | Privacy label is clean; no Plaid = no financial data scrutiny. Test StoreKit sandbox early. |
| iOS 64-notification cap | Broken reminders for power users | Only schedule next 21 days; refresh weekly via BGTaskScheduler |
| iCloud sync conflicts | Data corruption | SwiftData + CloudKit handles last-writer-wins automatically; acceptable for simple model |
| Bobby ships a major update | Reduced differentiation | Bobby has been semi-abandoned for years; even if they update, our notification reliability + email scanning is unique |
| Email parsing low accuracy | Feature disappointment | Start conservative: only auto-detect well-structured receipts; flag low-confidence for user review; frame as "suggestions" not "found" |
| Screen Time API locked behind Family Controls | Feature blocked | Research entitlement before committing; fallback to user self-report or Shortcuts automation |
| Low conversion rate | Revenue miss | $7.99 one-time is low risk for users; the free tier is generous enough to generate reviews but limited enough to upsell |

---

## Success Metrics (3-Month Targets)

| Metric | Target |
|--------|--------|
| App Store rating | ≥ 4.6★ |
| Downloads (organic + paid) | 2,000 |
| Paid conversions | 500 (25% conversion) |
| Net revenue | ~$3,400 |
| DAU/MAU ratio | ≥ 15% (widget-driven) |
| 1-star reviews mentioning notifications | 0 |

---

## Open Questions

- [ ] SwiftData vs. raw Core Data? SwiftData is cleaner but iOS 17+ only and has known bugs with complex predicates. Decision: start with SwiftData, fall back only if we hit blockers.
- [ ] App name: "SubTracker" may conflict with existing apps sharing similar names. Alternatives: "BurnRate", "SubWatch", "Renew", "SubGuard". Check trademark/App Store availability before committing.
- [ ] Currency handling: support multi-currency from day 1 or assume single currency? Recommendation: single default currency for MVP, multi-currency in V1.1.
- [ ] Minimum iOS version: 17.0 (SwiftData) vs 16.0 (Core Data, wider reach). Decision: iOS 17 — the 15% of users on older versions aren't the target demographic.
