---
id: T053
title: S9 carry-forward backlog (#5 #6 #9–#15) — minor fixes
severity: low
status: closed
phase: 2
layer: infra
opened: S10 2026-05-26
closed: S10 2026-05-26
---

## Problem

Minor S9 Opus findings and S8 carry-forwards that did not yet have tickets:

- **S9 #5**: `extract_carry_forwards.py` — ages are relative to LAST WRITTEN REVIEW, not live
  session; undocumented semantic.
- **S9 #6**: `generate_ticket_index.py` — aging section header omitted when no stale tickets;
  indistinguishable from generator regression.
- **S9 #9** [S8 #5]: `regenerate_ticket_index.py:_is_closed_ticket` — `Path.resolve()`
  symlink canonicalisation; switch to lexical `.parts`.
- **S9 #10** [S8 #6]: `prepare_opus_context.py` — invariants source labeled "repo-local"
  when `--repo` not supplied (reads harness root file, not a workspace repo).
- **S9 #11** [S8 #9]: No test for `regenerate_ticket_index.py` workspace T016 attribution fix.
- **S9 #12** [S8 #10]: `test_telemetry.py:test_exits_on_invalid_yaml` — f-string
  interpolates `tmp_path` without `repr()`, brittle on paths with spaces.
- **S9 #13** [S8 #11]: T026 closed ticket resolution says "off by default" but S7 flipped it
  to default-on; no forward-pointer in the ticket.
- **S9 #14** [S8 #12]: `analyze_tool_log.py:78` — empty-string default key for session-less
  records groups them together; add comment explaining the intent.
- **S9 #15** [S8 #13]: `prepare_opus_context.py:check_utcnow` — `harness_config.py` docstring
  contains the word "utcnow" as an example check name; triggers false positive WARN.

## Acceptance Criteria

- [ ] `extract_carry_forwards.py` — docstring on `_current_session_number` documents the
      "ages relative to last written review" semantic.
- [ ] `generate_ticket_index.py` — aging section header always emitted; body is `*(none)*`
      when no stale tickets.
- [ ] `regenerate_ticket_index.py:_is_closed_ticket` — uses `Path(file_path).parts` not
      `Path(file_path).resolve().parts`.
- [ ] `prepare_opus_context.py:_build_invariants_section` — label is "harness root" when
      `--repo` not supplied, "repo-local" when `--repo` is given and file exists, "harness
      fallback" when `--repo` given but repo-local file absent.
- [ ] `test_workspace_path_flags.py` — test for T016 attribution in workspace context.
- [ ] `test_telemetry.py:test_exits_on_invalid_yaml` — paths quoted with `repr()`.
- [ ] `docs/tickets/closed/T026-*.md` — resolution note added about S7 default-on flip.
- [ ] `analyze_tool_log.py:78` — comment explaining empty-string grouping sentinel.
- [ ] `prepare_opus_context.py:check_utcnow` — `harness_config.py` excluded from grep.
- [ ] All existing tests still pass; static analysis PASS after fix.

## Notes

S9 #8 [S8 #4] (bootstrap rate-limit) explicitly marked "not actionable yet" — excluded.

## Resolution

Fixed all 9 items in the S9 carry-forward backlog:
#5: extract_carry_forwards._current_session_number docstring documents 'ages relative to last written review' semantic.
#6: generate_ticket_index.py always emits '## Aging Tickets' header with '*(none)*' body when empty; surface_stale_tickets.py updated to recognise '*(none)*' as clean state.
#9: regenerate_ticket_index._is_closed_ticket uses lexical Path.parts (no resolve()).
#10: prepare_opus_context.py labels invariants 'harness root' (no --repo), 'repo-local' (--repo given, file exists), 'harness fallback' (--repo given, file absent).
#11: Added 3 TestT016WorkspaceAttribution tests verifying workspace sessions.md is used.
#12: test_telemetry.py subprocess f-string paths now use repr() for quote safety.
#13: T026 closed ticket resolution notes S7 default-on policy flip with commit reference.
#14: analyze_tool_log.py empty-string session key documented with inline comment.
#15: prepare_opus_context.check_utcnow excludes harness_config.py to eliminate false positive.

Closed S10 2026-05-26.
