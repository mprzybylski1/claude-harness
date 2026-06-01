---
id: T008
title: WidgetKit — small (monthly spend) and medium (next 3 renewals)
severity: high
status: closed
phase: 2
layer: frontend
repo: subtracker
opened: S3 2026-06-01
closed: S3 2026-06-01
---

## Problem

SPEC P0 feature #7: home screen widgets are a high retention driver. Small widget shows monthly burn rate. Medium widget shows next 3 upcoming renewals with urgency coloring. Requires widget extension target, shared App Group for SwiftData access, and timeline refresh on data change.

## Acceptance Criteria

- [x] Widget extension target added to Xcode project
- [x] App Group configured for shared SwiftData access between app and widget
- [x] Small widget displays monthly burn rate total
- [x] Medium widget displays next 3 upcoming renewals with names, prices, and dates
- [x] Timeline provider refreshes data from shared SwiftData store
- [x] Build succeeds with widget extension

## Resolution
Widget extension target with small (monthly spend) and medium (next 3 renewals) widgets. WidgetDataProvider pure logic with 5 tests. App Group shared container for SwiftData access. Model files copied to widget target for compilation. Both targets build. Widget rendering requires home screen testing (deferred). 59/59 tests pass.

Closed S3 2026-06-01.
