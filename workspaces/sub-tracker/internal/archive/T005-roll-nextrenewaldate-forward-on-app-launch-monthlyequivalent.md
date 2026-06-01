---
id: T005
title: Roll nextRenewalDate forward on app launch + monthlyEquivalent tests
severity: high
status: closed
phase: 2
layer: frontend
repo: subtracker
opened: S3 2026-06-01
closed: S3 2026-06-01
---

## Problem

nextRenewalDate is stored but never recomputed after time passes. Dashboard degrades within one billing cycle and Phase 2 notifications will schedule from stale dates. Also monthlyEquivalent has zero tests (Opus S2 Concerns 1+2).

## Acceptance Criteria

- [x] refreshRenewals function rolls forward stale nextRenewalDate values
- [x] Only updates when nextRenewalDate < startOfDay(now) — today's renewals stay visible
- [x] Skips subscriptions already in the future (no unnecessary CloudKit writes)
- [x] Wired into ContentView.onAppear
- [x] monthlyEquivalent covered by tests for all 7 billing cycles plus edge cases
- [x] Unit tests for rollforward logic (TDD)

## Resolution
Added Subscription.refreshRenewals static function that rolls forward stale nextRenewalDate values (< startOfDay). Wired into ContentView.onAppear. Skips archived subs and future dates. Added 15 new tests (10 monthlyEquivalent + 5 refreshRenewals). 32/32 pass.

Closed S3 2026-06-01.
