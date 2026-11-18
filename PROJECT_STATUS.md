# AP Compass — Project Status / Gate Register

**Updated:** 2026-11-19 (IST)
**Current gate:** Phase 3 stabilized — revised required-provider acceptance PASS; architectural review pending.
**Stabilization base:** f8ce2026fb18b52fbd1d358d92c4b904311174e1.
**Branch:** codex/phase-03-document-engine.
**Verified checkpoint reference:** phase-03-document-engine (created after required checks; resolve tag for SHA).
**Publication:** Final commit/tag/push verification reported in chat after this evidence file is committed.
**Deadline:** Saturday 2026-11-21 (IST). Stop after stabilization; Phase 4 is not authorized.

| Phase | State | Evidence / limits |
|---|---|---|
| 01 Foundation | ACCEPTED by user review | Checkpoint unchanged |
| 02 Finance engine | ACCEPTED by user review | Original tests still pass; checkpoint unchanged |
| 03 + 3.1 Document engine | Revised gate PASS; review pending | 229 tests, real primary-only scan smoke and prior native proof; escalation optional/disabled, live-unverified |
| 04 Orchestration + API | LOCKED | Not implemented; no authorization |
| 05 Operations UI | LOCKED | Foundation shell only |
| 06 Scenarios + evaluation | LOCKED | Manifests unchanged |
| 07 Release | LOCKED | No deployment work |

## Verified stabilization evidence

| Check | Actual result |
|---|---|
| Final backend suite | 229 passed, zero failures, one existing Starlette/AnyIO warning; 35.85s |
| Regression preservation | 129 unchanged Phase 1/2 tests plus 100 document tests (76 previous + 24 stabilization) |
| Frontend production build | PASS, 1682 modules; no source changes |
| Manifest / hygiene / pip | PASS; original procurement/fixture expectations unchanged; no broken dependencies |
| Primary-only mode | No optional metadata, provider construction or generation; native/scan both primary |
| Optional failure retention | Valid incomplete/uncertain primary preserved for outage/timeout/quota; failed attempts visible |
| Unusable primary | Malformed/empty/unavailable without usable facts remains typed technical failure |
| Counts | Metadata-only and deadline-cancelled unstarted inference not counted as generation |
| One real extra generation | Flash-Lite SCAN_CONFLICT, 3241ms adapter / 2686ms model; 1399 input + 914 output = 2313 tokens; thinking unknown |
| Real grounded scan | 13/13 adapter fields; line.net=None, gross=86200; all evidence unverified |
| Existing evaluator | REVIEW_REQUIRED; arithmetic discrepancy 3600 retained |
| Flash traffic in stabilization | Zero metadata and zero inference requests |
| Protected diff | Finance/contracts/DB/API/UI/manifests/old domain tests/all fixtures/dependencies/Docker unchanged |

## Release decision and limits

ADR-016 records the explicit user adjustment: one live working provider required; stronger escalation optional.
GEMINI_ESCALATION_ENABLED=false is the code/sample/local default. Enable only after genuine stronger inference
is verified. Previous Flash failures remain historical facts, never represented as successes.
Conservative source verification and scan uncertainty remain; no OCR or general accuracy claim.
No ledger writes, shared-contract changes, orchestration, UI work, paid service or new model.
A new short-deadline count regression initially failed; request-local tracking fixed it before the final 229-test pass.

## Reports and handoff

Current: docs/PHASE_03_1_REPORT.md and docs/PHASE_03_1_LIVE_RESULTS.json.
Historical Phase 3: docs/PHASE_03_REPORT.md and docs/PHASE_03_LIVE_RESULTS.json; actual failures preserved.
Phase 1/2 tags remain at 12e4a5229903213017a852507d049133a1a7b871 and 6d9963a6a8883ea87c6a4457e0ce0353c28491a8.

Stop for architectural review. Do not start Phase 4 automatically.
