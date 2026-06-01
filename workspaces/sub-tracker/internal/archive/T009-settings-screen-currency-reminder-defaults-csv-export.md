---
id: T009
title: Settings screen — currency, reminder defaults, CSV export
severity: medium
status: closed
phase: 2
layer: frontend
repo: subtracker
opened: S3 2026-06-01
closed: S3 2026-06-01
---

## Problem

No settings screen exists. Users cannot change default currency, configure default reminder days for new subscriptions, or export their data. SPEC Day 9 deliverable.

## Acceptance Criteria

- [x] Settings view accessible from main navigation
- [x] Default currency picker (common currencies)
- [x] Default reminder days configuration for new subscriptions
- [x] CSV export of all subscriptions via share sheet
- [x] App version display
- [x] Build succeeds and tests pass

## Resolution
SettingsView with gear icon in toolbar. Default currency picker (21 currencies via @AppStorage), default reminder days (ReminderDaysPicker), CSV export via share sheet (CSVExporter with proper escaping), app version + sub count. New subs read default reminder days from settings. 5 CSV tests, 64/64 total pass.

Closed S3 2026-06-01.
