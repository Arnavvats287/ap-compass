# AP Compass — Project Status / Gate Register

**Updated:** 2026-11-19 IST.
**Current gate:** Phase 4 vertical slice PASS; architectural review pending. STOP before Phase 5.
**Authorized base:** phase-03-document-engine / c0d06f07fc3d0d70b26318dc247778402dd1fbab.
**Branch:** codex/phase-04-orchestration-api.
**Checkpoint:** phase-04-vertical-slice, published only after required checks; resolve tag for exact SHA.
**Publication evidence:** Final SHA/branch/tag remote verification and clean-tree status are reported in the
final chat after this file is committed. No force push/default-branch change or prior-tag alteration.
**Deadline:** Saturday 2026-11-21 IST.

| Phase | State | Evidence |
|---|---|---|
| 01 Foundation | ACCEPTED by user | Original checkpoint preserved |
| 02 Finance | ACCEPTED by user | All 99 finance tests unchanged/passing |
| 03/3.1 Extraction | ACCEPTED by user | All 100 document tests unchanged/passing; primary only |
| 04 Orchestration + API | PASS; review pending | Real upload -> persisted stages -> Gemini -> pure decision -> reload |
| 05 Operations UI | LOCKED | Foundation shell only; no authorization |
| 06 Scenarios | LOCKED | Original manifests/fixtures unchanged |
| 07 Release | LOCKED | No deployment/public release work |

## Verified evidence

- Final full suite: **268 passed**, zero failures/errors, one existing warning, 46.24s.
  30 foundation + 99 finance + 100 document + 39 new API/integration tests.
  One Phase 1 absent-upload assertion now expects 415 for missing multipart; no financial assertion changed.
- Frontend TypeScript/Vite production build PASS, 1682 modules; source unchanged.
- Manifest validator PASS: 6 vendors, 7 POs, 3 billed invoices, 10 scenarios.
- Git hygiene PASS: 11 exclusions, PDFs intact, .env/runtime ignored; pip check no broken requirements.
- Actual Uvicorn HTTP boot/read/shutdown PASS: health, policy, dashboard, runs=200; no inference needed.
- Exactly 3 real Flash-Lite API E2E generations: HAPPY_CLEAN READY, OVERBILLED_PARTIAL BLOCKED,
  SCAN_CONFLICT REVIEW, all COMPLETED. Zero metadata or optional Flash requests. Expected fields match.
- Genuine source: native refs independently verified; scan refs unverified; optional scan line.net=None,
  gross 86200 and arithmetic discrepancy 3600 preserved. No source evidence upgrade or finance workaround.
- Extraction/total ms: clean 3213/3259; overbilled 2680/2716; scan 3696/3738.
  Reported input/output tokens: 543/913, 542/681, 1399/914. One model call each; no invented cost/usage.
- All three full snapshots and PDF hashes identical after app recreation; zero additional generation calls.
- Authoritative table hash before/after: 7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398.
- Event-synchronized test proves active extraction progress and second run QUEUED. Restart tests interrupt both
  QUEUED/RUNNING work with SERVER_RESTART; no active stages or automatic model replay remain.
- RunStage is the sole stage store. InvoiceRun JSON stages=[]; detail uses one atomic joined query.
- Policy version collisions fail without overwriting existing PolicySnapshot. Authority rows never mutate.

## Contract and implementation boundaries

Only approved shared addition: RunSnapshotV1.execution_error_code: str | None = None (ADR-017), allowlisted
and null for nontechnical states. Historical JSON remains valid. Existing tables/schema, financial rules,
matching, evidence grounding, seed/fixture manifests and PDFs, frontend and Docker are unchanged.
Runtime extractor bypasses per-invoice model metadata dependency; credentials missing -> controlled run
CONFIGURATION failure, healthy application. Escalation remains disabled; Flash was never called in Phase 4.

## Limitations / handoff

Single-process in-process scheduling, one active workflow. Persist DB and document directory together; use one
Uvicorn worker. Restart interrupts rather than replays. Scans remain unverified; no OCR/general accuracy claim.
No frontend upload/queue/dashboard integration, approval, reevaluation/policy editor, auth/rate-limit suite,
retention/orphan cleanup, distributed queue, cloud storage or deployment. Dashboard scans run snapshots in one
query; large-history optimization deferred. DB outage can prevent failure persistence; no fabricated completion.

Current reports: docs/PHASE_04_REPORT.md, docs/PHASE_04_LIVE_RESULTS.json,
docs/PHASE_04_FAILURE_EXAMPLE.json, docs/ORCHESTRATION_API.md. Historical reports remain unchanged.
No failed test remains. Prior development failures and the narrow Phase 1 assertion update are documented.
Next action: architectural review or bounded repair prompt only. Do not start Phase 5 automatically.
