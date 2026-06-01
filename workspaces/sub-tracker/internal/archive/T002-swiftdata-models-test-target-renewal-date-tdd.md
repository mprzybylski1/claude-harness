---
id: T002
title: SwiftData models + test target + renewal-date TDD
severity: high
status: closed
phase: 2
layer: fullstack
repo: subtracker
opened: S2 2026-06-01
closed: S2 2026-06-01
---

## Problem

No unit-test target, no SwiftData models, no renewal-date computation. Phase 1 gate blocked.

## Acceptance Criteria

- [x] Unit-test target added to pbxproj with TEST_HOST/BUNDLE_LOADER
- [x] Shared scheme at xcshareddata/xcschemes/SubTracker.xcscheme
- [x] SwiftData models: Subscription, PriceChange, Category with CloudKit-compatible defaults
- [x] BillingCycle and SubscriptionOwner enums
- [x] computeNextRenewal uses anchor-relative computation (no month-end drift)
- [x] 17 passing tests covering all billing cycles, month-end clamping, leap years, trials, edge cases
- [x] modelContainer wired in SubTrackerApp
- [x] CLAUDE.md test command grep pattern updated for Swift Testing

## Resolution
Added unit-test target with shared scheme, SwiftData models (Subscription, PriceChange, Category) with CloudKit-compatible defaults, and TDD'd computeNextRenewal with anchor-relative algorithm. 17 tests passing. Fixed CLAUDE.md test grep. Code committed in SubTracker repo (5db137b).

Closed S2 2026-06-01.
