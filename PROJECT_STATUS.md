# AP Compass — Project Status / Gate Register

**Updated:** 2026-11-19 00:51 IST  
**Current gate:** Segment 01 — NOT STARTED / NOT VERIFIED  
**Build/deploy URL:** Not provided  
**Latest verified commit:** None  
**Upcoming deadline:** Friday 2026-11-20 evening feature freeze; Saturday 2026-11-21 submission.

> Status is an evidence register, not an intention list. `DONE` means code ran and acceptance evidence exists. Never mark a segment done based only on generated code or an assistant assertion.

| Segment | State | Key acceptance evidence | Branch / commit | Blockers |
|---|---|---|---|---|
| 01 Foundation | NOT STARTED | None; 4 real PDFs, correct seed, backend/frontend boot and tests must be shown | — | — |
| 02 Finance engine | LOCKED (01) | Pure engine regressions, no ledger mutation | — | — |
| 03 Document engine | LOCKED (01) | Live Gemini text PDF, scan route, safe errors | — | API key entitlement unverified |
| 04 Orchestration + API | LOCKED (02, 03) | Real PDF → persisted stages → real decision → refresh | — | — |
| 05 Operations UI | LOCKED (04 for wiring) | Uploaded real invoice, evidence, dashboard/history, business next action | — | — |
| 06 Scenarios + evaluation | LOCKED (vertical slice) | >=2 edge cases live, actual measured outcomes | — | Creative fourth case open |
| 07 Delivery + demo | LOCKED (05, 06) | External link, recording <=5 minutes, submit link | — | Host/links unverified |

## Current work assignment

- **Authorized scope:** Only `prompts/SEGMENT_01_FOUNDATION.md`.
- **Parallel workers:** None until 01 passes. After 01, split 02/03 with zero shared-contract edits.
- **Acceptance blocker:** Any failed backend test, missing/incorrect seed/fixture arithmetic, frontend/backend cannot boot, or unreviewed contract break.
- **Next assistant response expected after report:** Audit actual Segment 01 evidence and issue a targeted repair prompt **or** separate Segment 02 and Segment 03 prompts with file ownership.

## Execution evidence log

| Date/time IST | Segment | Commands/tests actually run | Result | Link/commit | Reviewed by |
|---|---|---|---|---|---|
| 2026-11-19 00:51 | Pre-build planning | Starter pack unpacked/inspected; no app run | PLANNED ONLY | — | — |

## Bug and blocker log

| ID | Severity | Description | Owner | Status / reproducer |
|---|---|---|---|---|
| — | — | No implementation bugs verified yet | — | — |

## Handoff protocol

Each segment completion report **must** include: git commit/diff summary, commands + literal pass/fail counts, endpoint/UI smoke-test evidence, relevant fixture decisions, deviations from contracts, files changed, blockers and exact segment completed. Copy `prompts/SEGMENT_REPORT_TEMPLATE.md` and complete it without guessing. If a command was not run, mark `NOT RUN`.

Codex must update this file only from directly observed work. The builder sends report/results to ChatGPT, which returns the next prompt. No silent auto-advance.
