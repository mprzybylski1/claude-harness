---
id: T004
title: Dashboard burn rate + urgency coloring
severity: high
status: closed
phase: 2
layer: frontend
repo: subtracker
opened: S2 2026-06-01
closed: S2 2026-06-01
---

## Problem

No burn rate calculation or visual urgency indicators. Dashboard incomplete for Phase 1 gate.

## Acceptance Criteria

- [x] monthlyEquivalent computed property on Subscription normalizes all billing cycles to monthly
- [x] BurnRateHeader shows monthly and yearly totals with active subscription count
- [x] Urgency coloring on renewal dates: red (today/overdue), orange (1-3 days), yellow (4-7 days)
- [x] Subscription list in Upcoming Renewals section

## Resolution
Added monthlyEquivalent to Subscription, BurnRateHeader with monthly/yearly totals, urgency coloring on renewal dates, and Upcoming Renewals section in dashboard. Code committed in SubTracker repo.

Closed S2 2026-06-01.
