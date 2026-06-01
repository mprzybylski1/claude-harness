---
id: T006
title: Notification engine — permission, scheduling, 64-cap, rescheduleAll
severity: high
status: closed
phase: 2
layer: frontend
repo: subtracker
opened: S3 2026-06-01
closed: S3 2026-06-01
---

## Problem

Phase 2 P0: reliable renewal notifications are the #1 differentiator. Needs permission request, per-sub configurable reminders, global rescheduleAll with 21-day window and 60-cap, trial escalation. Bobby's broken notifications are their top complaint — must not repeat.

## Acceptance Criteria

- [x] NotificationScheduler with rescheduleAll as primary entry point
- [x] Computes all requests across all subs, filters past dates and beyond 21 days
- [x] Sorts by fire date, takes nearest ≤60 (leaves headroom under iOS 64 cap)
- [x] Per-sub save triggers rescheduleAll
- [x] Permission request on first subscription add
- [x] Notification identifiers use subscription.id prefix for clean removal
- [x] Protocol abstraction over UNUserNotificationCenter for testability
- [x] Unit tests for scheduling logic (TDD)
- [x] Device testing flagged as remaining work (not claimable this session)

## Resolution
NotificationScheduler with rescheduleAll entry point, NotificationCenterProtocol for testability, 21-day window, 60-cap, permission request, reminder UI (ReminderDaysPicker toggles for 7/3/1/0 days), wired into app launch + sheet dismiss + delete. 12 scheduler tests, 44/44 total pass. REMAINING: BGTaskScheduler background refresh, trial escalation alerts, real-device delivery testing.

Closed S3 2026-06-01.
