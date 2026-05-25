---
id: T038
title: prepare_opus_context.py invariants section missing source attribution (S6 C#11)
severity: low
status: closed
phase: 2
layer: infra
opened: S8 2026-05-25
closed: S8 2026-05-25
---

## Problem

S6 Concern #11. Opus reviewing the context couldn't tell whether repo-local or harness fallback invariants were embedded.

## Acceptance Criteria

- [x] Section title includes `[Source: repo-local — <path>]` or `[Source: harness fallback — <path>]`.

## Resolution

S8 2026-05-25: `inv_source` variable tracks which file was resolved; section title now includes `[Source: <inv_source> — <inv_path>]`.
