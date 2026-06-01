---
id: T003
title: Add/edit subscription flow
severity: high
status: closed
phase: 2
layer: frontend
repo: subtracker
opened: S2 2026-06-01
closed: S2 2026-06-01
---

## Problem

No UI to create or edit subscriptions. Phase 1 gate blocked.

## Acceptance Criteria

- [x] AddEditSubscriptionView form with name, price, billing cycle, start date, trial toggle, owner, notes
- [x] Billing cycle picker with custom days option
- [x] Live next-renewal-date preview in form
- [x] Form validation: non-empty name, positive price, valid custom days
- [x] Save creates new Subscription or updates existing, sets nextRenewalDate
- [x] ContentView shows subscription list sorted by next renewal, empty state, add button
- [x] Tap row opens edit sheet, swipe to delete
- [x] displayName on BillingCycle and SubscriptionOwner enums, CaseIterable on SubscriptionOwner

## Resolution
Built AddEditSubscriptionView with full form (name, price, cycle, start date, trial, owner, notes), live next-renewal preview, validation. Updated ContentView with subscription list, empty state, add/edit sheets, swipe-to-delete. Added displayName + CaseIterable to enums. Code committed in SubTracker repo.

Closed S2 2026-06-01.
