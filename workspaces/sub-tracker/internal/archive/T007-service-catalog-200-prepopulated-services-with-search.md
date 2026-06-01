---
id: T007
title: Service catalog — 200+ prepopulated services with search
severity: high
status: closed
phase: 2
layer: frontend
repo: subtracker
opened: S3 2026-06-01
closed: S3 2026-06-01
---

## Problem

Users must manually type all subscription details. SPEC feature #1 (P0): add subscription from 200+ pre-loaded service catalog with names, default prices, categories, and SF Symbol icons. Catalog is a bundled JSON file shipped with the app.

## Acceptance Criteria

- [x] Bundled JSON catalog with 200+ popular services
- [x] Each entry has: name, defaultPrice, currencyCode, billingCycle, category, sfSymbol
- [x] ServiceCatalog model to load and search the catalog
- [x] Searchable service picker in the add flow (search by name)
- [x] Selecting a service pre-fills name, price, cycle, and icon
- [x] Custom entry option for services not in catalog
- [x] Unit tests for catalog loading and search

## Resolution
249-entry services.json bundled (22 categories, SF Symbols, brand colors). Prices stored as strings to prevent Decimal precision loss. ServiceCatalog singleton with case-insensitive search. ServicePickerView with search bar + Custom Entry option. Pre-fills name/price/cycle/icon/color into AddEditSubscriptionView. Subscription rows display icons. 10 catalog tests, 54/54 total pass. Verified JSON present in app bundle. Default prices are seed estimates pending real-data pass.

Closed S3 2026-06-01.
