# SubTracker

Privacy-first iOS subscription tracker. One-time purchase, no bank link, no backend.

This workspace is managed by the Claude harness.

## Session protocol

At session start, run `/session-start`. Context files for this workspace:

- `sessions.md` — session log
- `tickets/INDEX.md` — ticket overview
- `SPEC.md` — full product spec (problem, competitors, architecture, build plan)

## Project Status

**Phase:** Planning (not yet started implementation)
**Target:** Ship MVP to App Store within 2 weeks of starting development.

## Repos

_See workspace.yaml for declared repos._

The Xcode project does not exist yet. First implementation session should:
1. Create `/Users/mprzybylski/Documents/Projects/SubTracker/` directory
2. Initialize Xcode project (iOS App, SwiftUI, SwiftData)
3. Set up git repo
4. Update `workspace.yaml` path if needed

## Key Context for Future Sessions

### What This Is

A subscription/recurring expense tracker for iOS that differentiates on:
1. **No bank link** — manual entry + on-device email scanning (V1.1)
2. **No subscription fee** — $7.99 one-time purchase
3. **Reliable notifications** — the #1 failure of existing privacy-first trackers
4. **iCloud sync** — zero backend, zero cost, solves data-loss complaints

### What It Is NOT

- Not a full budgeting app (no Plaid, no transaction categorization, no net worth)
- Not a bank aggregator
- Not a subscription service itself

### Technical Decisions (Locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| UI framework | SwiftUI | Modern, widget support, less boilerplate |
| Persistence | SwiftData | CloudKit sync for free; iOS 17+ acceptable |
| Min iOS | 17.0 | SwiftData requirement; target demographic skews newer |
| Backend | None | Local-only + CloudKit; zero ops cost |
| Notifications | Local (UNUserNotificationCenter) | No push server needed |
| IAP | StoreKit 2, non-consumable | No subscription; no server validation |
| Widgets | WidgetKit (small + medium) | Retention driver |

### Architecture Overview

```
┌─────────────────────────────────────┐
│         SwiftUI Views               │
│  (Dashboard, Add/Edit, Settings)    │
├─────────────────────────────────────┤
│         View Models                 │
│  (subscription list, burn rate)     │
├─────────────────────────────────────┤
│      SwiftData Model Layer          │
│  Subscription, PriceChange, Category│
├──────────────┬──────────────────────┤
│  CloudKit    │  UNNotification      │
│  (iCloud)    │  (local alerts)      │
└──────────────┴──────────────────────┘
```

No network layer. No API clients. No server.

### Critical Implementation Notes

- **Notification reliability is the #1 differentiator.** Test on real devices. Bobby's broken notifications are their top complaint — we must not repeat this.
- **iOS caps local notifications at 64.** Mitigation: only schedule next 21 days, refresh weekly via BGTaskScheduler.
- **Next renewal date calculation must use Calendar month arithmetic**, not naive +30 days. See SPEC.md for the algorithm.
- **Service catalog is a bundled JSON file** (~200 entries). Ship updates with app versions, not a server.

### Build Plan Summary

- **Week 1:** Data model, CRUD, service catalog, add/edit flow, dashboard
- **Week 2:** Notifications, widgets, StoreKit paywall, QA, App Store submit
- **Week 3:** Email scanning, Screen Time correlation, price history
- **Week 4:** Family sharing, cancellation guides, marketing launch

Full day-by-day breakdown in `SPEC.md` under "Build Plan".

## Commands

All commands assume `cwd = ~/Documents/Projects/SubTracker`.

### Run tests (simulator)

```bash
xcodebuild -project SubTracker.xcodeproj -scheme SubTracker \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' test 2>&1 \
  | grep -E "Test Suite|Test case|Executed|error:|BUILD (SUCCEEDED|FAILED)"
```

### Build for device

```bash
xcodebuild -project SubTracker.xcodeproj -scheme SubTracker \
  -destination 'id=00008140-000270A8143B801C' build
```

### List available simulators

```bash
xcrun simctl list devices available | grep -E "iPhone|iPad"
```
