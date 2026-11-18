# AP Compass — Project Status / Gate Register

**Updated:** 2026-11-19 (IST)
**Current gate:** Phase 03 — PARTIAL; offline and primary live verified, stronger-model inference blocked.
**Verified base:** Phase 2 accepted by user review; 6d9963a6a8883ea87c6a4457e0ce0353c28491a8.
**Branch:** codex/phase-03-document-engine, based on the Phase 2 tag (not GitHub's older default branch).
**Complete Phase 3 checkpoint:** NOT CREATED. Review commit/push outcome recorded in final chat after publication.
**Deadline:** Saturday 2026-11-21 (IST). No public deployment or later-phase work authorized here.

| Phase | State | Evidence | Blocker |
|---|---|---|---|
| 01 Foundation | ACCEPTED by user review | Original checkpoint preserved | — |
| 02 Finance engine | ACCEPTED by user review | Original 129 tests still pass; checkpoint preserved | — |
| 03 Document engine | PARTIAL; review required | 205 tests pass; Flash-Lite actual native/scan inference; genuine native grounding; image-only fixture | Flash has no successful native/scan inference; HTTP 504/timeouts |
| 04 Orchestration + API | LOCKED | Not implemented | No authorization |
| 05 Operations UI | LOCKED | Foundation shell only | No authorization |
| 06 Scenarios + evaluation | LOCKED | Existing manifests unchanged | No authorization |
| 07 Release | LOCKED | No deployment work | No authorization |

## Current assignment

Phase 3 only. Implementation complete for review with an external live-escalation blocker. STOP; no Phase 4.
See docs/PHASE_03_REPORT.md and docs/PHASE_03_LIVE_RESULTS.json. No agents were started.

## Verified Phase 3 evidence (2026-11-19 IST)

| Check | Observed result |
|---|---|
| Full suite | 205 passed: 129 unchanged existing + 76 document tests; zero failures; 1 existing warning; 25.12s |
| Frontend build / pip check | Pass; no UI source changes; no broken dependencies |
| Static oracle | Pass: 6 vendors / 7 POs / 3 billed / 10 expected cases, untouched |
| PDF fixtures | Original four unchanged; new SCAN_CONFLICT has no usable text; actual image rendered and visually inspected |
| Resource/security tests | 512 MiB OS cap enforced; 12s parser timeout, size/page limits, mixed routing, strict schema and no tool authority verified |
| Protected-file diff | Finance rules/contracts/DB/API/frontend/manifests/original tests/Docker/scripts unchanged |
| Model metadata | Both IDs visible, generateContent advertised; this alone is not inference verification |
| Flash-Lite live | HAPPY_CLEAN and OVERBILLED_PARTIAL 13/13 fields, all NATIVE_VERIFIED; SCAN_CONFLICT 12/13, unverified source |
| Scan extraction error | Optional line net 70000 supplied although absent from image; preserved as observed error, never promoted to native verification |
| Stronger model | Eight explicit native/scan attempts across documented configurations; no output; later HTTP 504/timeouts |
| Total live generation attempts | 14 explicit attempts, 3 successful Flash-Lite responses; failed usage remains unknown, not zero |
| Git hygiene | Key ignored; 11 exclusions pass; all five fixture files retain exact indexed bytes |

## Problems and unresolved items

- Full Phase 3 gate pending successful Flash inference/benchmark; no passing Phase 3 tag.
- Early rich generation grammar rejected; minimal grammar plus strict local bounds fixed Flash-Lite generation.
- Buyer-heading grounding bug caught by adversarial test and fixed; final tests pass.
- Existing Starlette/AnyIO warning remains nonblocking. Windows sandbox asyncio needs approved execution.
- No scan OCR verification, general table coverage, live escalation success, orchestration or deployment claimed.
- SDK dependency requires Pydantic >=2.12.5; installed/tested pin is 2.14.3. Shared contract shapes are unchanged.

## Historical evidence

Phase 1: docs/PHASE_01_REPORT.md, tag phase-01-foundation at 12e4a5229903213017a852507d049133a1a7b871.
Phase 2: docs/PHASE_02_REPORT.md, tag phase-02-finance-engine at 6d9963a6a8883ea87c6a4457e0ce0353c28491a8.
Both accepted by explicit user review; neither tag is changed. Current work is a review branch, not a completed Phase 3 checkpoint.

## Handoff

Review the adapter/source verification and external Flash availability. A bounded Phase 3 repair or explicit
routing-acceptance decision is required. Do not infer permission for Phase 4, another model or a paid service.
