---
id: T119
title: add --layer flag to promote_raised_concern.py
severity: low
status: closed
phase: 2
layer: tooling
# repo: <name from workspace.yaml repos list>
opened: S21 2026-05-28
closed: S21 2026-05-28
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

- [x] `--layer` accepts the same choices as create_ticket.py (`backend`, `frontend`, `fullstack`, `infra`, `process`, `tooling`) and is forwarded
- [x] When `--layer` is omitted, default remains `tooling` (backwards compat)
- [x] Tests cover with-flag, without-flag, and invalid-value paths (TestLayerFlag)

## Resolution
Refactored promote_raised_concern.py CLI from sys.argv parsing to argparse. Added --layer flag with the same choices as create_ticket.py (backend/frontend/fullstack/infra/process/tooling); defaults to 'tooling' for backwards compat. Forwarded to create_ticket.py subprocess. 3 new tests in TestLayerFlag.

Closed S21 2026-05-28.
