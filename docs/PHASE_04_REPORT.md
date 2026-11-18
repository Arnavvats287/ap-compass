# Phase 4 — Real end-to-end orchestration + API

**Date:** 2026-11-19 IST. **Gate: PASS; architectural review pending. STOP before Phase 5.**
Base: phase-03-document-engine / c0d06f07fc3d0d70b26318dc247778402dd1fbab.
Branch: codex/phase-04-orchestration-api. Existing remote: https://github.com/Arnavvats287/ap-compass.git.
Verified publication target: annotated phase-04-vertical-slice. This report is committed with that checkpoint;
resolve the tag for the exact SHA. Final commit/push/clean-tree evidence is supplied in the chat after publication.
Previous tags/default branch are unchanged. No agents, deployment or later-phase work.

## A. Architecture

POST upload -> bounded validation -> opaque local PDF -> persisted QUEUED run/stages -> tracked async task ->
real Phase 3 extraction -> complete trusted snapshots -> build_context -> evaluate -> persisted COMPLETED decision.
The orchestrator only coordinates existing adapters. Business rules remain entirely in the pure engine.
One application semaphore serializes the complete workflow; subsequent runs remain QUEUED. No Redis/Celery/queue.
SQLite transactions close before inference. RunStage rows exclusively own stage state; run JSON stores stages=[].
Detail uses one joined read for an atomic run/stage snapshot. Legacy embedded stages cannot override rows.
PolicySnapshot insert-or-verify prevents same-version drift; exact evaluated policy is stored with each decision.

AP_COMPASS_DOCUMENT_DIR defaults to runtime/documents. Generated opaque IDs, exclusive temporary writes,
fsync and atomic replace; no original filenames or raw PDF JSON. Serving resolves through a run and refuses
unsafe/symlink/outside-root paths. Startup marks leftover QUEUED/RUNNING work INTERRUPTED/SERVER_RESTART,
clears decisions, ends RUNNING stages and skips pending stages. No model replay. Shutdown cancels/awaits tasks.
See ORCHESTRATION_API.md for full ownership, errors, configuration and limitations.

## B. API

| Endpoint | Observed/implemented behavior |
|---|---|
| GET /api/health | 200; real DB query, unchanged safe response |
| POST /api/runs | Exactly one multipart file, accepted PDF -> 202 {run_id, execution_state:QUEUED}; no wait for processing |
| GET /api/runs?limit=50 | Recent summaries; 1..100; one SQL query, no N+1 |
| GET /api/runs/{id} | Complete reconstructed RunSnapshotV1, stages from rows; unknown ->404 |
| GET /api/runs/{id}/document | That run's PDF; application/pdf, no-store, nosniff, fixed inline invoice.pdf; unknown/unsafe ->404 |
| GET /api/policy | Actual current immutable PolicyV1; editing absent |
| GET /api/dashboard | Actual persisted total/in-progress/completed/ready/review/blocked/failed/interrupted counts |

Summary includes timestamps/state, nullable outcome/vendor/invoice number/gross/currency/primary reason/owner.
Decimal strings remain exact. No financial aggregate, fake KPI or currency mixing. No reevaluation endpoint.
Actual Uvicorn HTTP startup/read/shutdown smoke on 127.0.0.1:8014 also passed health/policy/dashboard/runs=200,
without any inference. Live invoice tests used real ASGI routes/lifespan in-process, not a standalone extraction helper.
Health: {"status":"ok","service":"ap-compass","version":"0.1.0","database":"ok"}.

## C. Actual stage lifecycle

Real HAPPY_CLEAN run 7b3a699bea514c7f9eed52b34d90d639, UTC 2026-11-18 (2026-11-19 IST):

| Stage | Final state | Persisted start UTC | Persisted finish UTC |
|---|---|---|---|
| received | PASSED | 23:21:04.299011 | 23:21:04.299011 |
| extracting_invoice | PASSED | 23:21:04.313010 | 23:21:07.537450 |
| matching_records | PASSED | 23:21:07.538450 | 23:21:07.547451 |
| evaluating_controls | PASSED | 23:21:07.548451 | 23:21:07.565453 |
| finalizing | PASSED | 23:21:07.565453 | 23:21:07.571465 |

Creation actually persists received PASSED and four QUEUED stages; task start persists RUNNING/extracting RUNNING.
An event-paused fake extractor proved GET detail remains RUNNING/extracting RUNNING with no finish timestamp;
a second submitted run stays QUEUED. Releasing the event completes both, without arbitrary assertion sleeps.

Actual persisted timeout integration run 3af1cf0318c3478994864523fe9f71d7 (TEST DATA, no real provider timeout):

| Stage | Final state | Persisted start UTC | Persisted finish UTC |
|---|---|---|---|
| received | PASSED | 23:23:50.266917 | 23:23:50.266917 |
| extracting_invoice | FAILED | 23:23:50.279925 | 23:23:50.297909 |
| matching_records | SKIPPED | null | 23:23:50.297909 |
| evaluating_controls | SKIPPED | null | 23:23:50.298908 |
| finalizing | SKIPPED | null | 23:23:50.298908 |

Execution PROCESSING_FAILED / decision=null / PROVIDER_TIMEOUT. Failure tokens unknown, not zero.
Exact source: PHASE_04_FAILURE_EXAMPLE.json, read from the final test's actual SQLite records.

## D. Offline integration outcomes

Providers are deterministic TEST DATA; actual PDF parsing, independent evidence grounding, DB authority,
context/matching, finance, stages and API serialization are real. No normal test uses Gemini/network.

| Scenario | Execution | Business outcome | Required codes observed | Calls | Ledger changed? |
|---|---|---|---|---|---|
| HAPPY_CLEAN | COMPLETED | READY_FOR_AP | PO_MATCH_CONFIRMED | 1 fake / 0 live | No |
| HAPPY_PARTIAL | COMPLETED | READY_FOR_AP | PO_MATCH_CONFIRMED | 1 fake / 0 live | No |
| OVERBILLED_PARTIAL | COMPLETED | BLOCKED | PO_BALANCE_EXCEEDED, PO_QUANTITY_EXCEEDED; PO-3015 retained | 1 fake / 0 live | No |
| DUPLICATE_REISSUED | COMPLETED | BLOCKED | EXACT_DUPLICATE | 1 fake / 0 live | No |
| SCAN_CONFLICT | COMPLETED | REVIEW_REQUIRED | TOTAL_RECONCILIATION_FAILED, SOURCE_EVIDENCE_MISSING | 1 fake / 0 live | No |
| Simulated provider timeout | PROCESSING_FAILED | null | execution_error_code=PROVIDER_TIMEOUT | 1 simulated attempt / 0 live | No |
| Restart (both QUEUED and RUNNING) | INTERRUPTED | null | SERVER_RESTART; no active stages | 0 live/recalls | No |
| Invalid MIME/size/empty/signature | Request 415/413/400 | No run | Request rejection | 0 fake/live | No |
| Malformed PDF with signature | PROCESSING_FAILED | null | INVALID_PDF after 202 | 0 provider calls | No |
| Missing credentials | PROCESSING_FAILED | null | CONFIGURATION; health still 200 | 0 live | No |
| Policy version collision | PROCESSING_FAILED | null | INTERNAL_ERROR; original policy retained | 1 fake / 0 live | No |

Each of the five fixture integrations reloads the identical complete snapshot and identical source bytes from
an app recreated with the same DB/document directory, with extraction count unchanged. All authority table
columns/values (Vendor, PurchaseOrder, POLine, PriorBilledInvoice) are snapshotted before/after and equal.

## E. Genuine Gemini E2E

Command after the offline gate passed:
`.venv/Scripts/python scripts/smoke_phase04.py --live --output tmp/phase04-live-results.json`.
Exactly **3 generation calls**, one each, actual/requested model **gemini-3.5-flash-lite**, official
client.aio.models.generate_content (Gemini Developer API v1beta). Zero metadata lookups, zero Flash calls.
No real API error, retries or missing/incorrect critical fields observed. This is a three-document check,
not a general model-accuracy benchmark. Prior Phase 3 smoke results are separate historical evidence.

All expected header facts match actual adapter output: vendor, invoice identity/date, PO, currency, net/tax/gross.
Date is 2026-11-14 and currency INR for all three. Exact expected/extracted pairs and every field evidence
state are preserved in PHASE_04_LIVE_RESULTS.json. Actual lines also match the printed fixture facts below.

| PDF | Vendor / invoice / PO (expected = extracted) | qty / unit net / optional line net | Header net / tax / gross | Source evidence |
|---|---|---|---|---|
| HAPPY_CLEAN | Orion Office Products / HAPPY_CLEAN-2026 / PO-6001 | 48 / 1000 / 48000; OR-SUPPLY-01 | 48000 / 8640 / 56640 | 13 refs NATIVE_VERIFIED |
| OVERBILLED_PARTIAL | Aster Systems / OVERBILLED_PARTIAL-2026 / PO-3015 | 6 / 5000 / 30000; AS-SERVICE-01 | 30000 / 5400 / 35400 | 13 refs NATIVE_VERIFIED |
| SCAN_CONFLICT | Kaveri Logistics / SCAN_CONFLICT-2026 / PO-4002 | 7 / 10000 / None; KL-FREIGHT-01 | 70000 / 12600 / 86200 | 13 refs SOURCE_LOCATED_UNVERIFIED |

Scan optional line net stays unknown; post-grounding output is not a claim that the model stopped calculating it.
Gross remains 86200, net+tax remains 82600, difference 3600. No total correction/evidence upgrade.

| PDF | Route | Actual execution / decision (matches oracle) | Reason codes | Extraction / matching / evaluation / total ms | Tokens input/output |
|---|---|---|---|---|---|
| HAPPY_CLEAN | native_text | COMPLETED / READY_FOR_AP, yes | PO_MATCH_CONFIRMED, BANK_DETAILS_NOT_PROVIDED | 3213 / 2 / 10 / 3259 | 543 / 913 |
| OVERBILLED_PARTIAL | native_text | COMPLETED / BLOCKED, yes | PO_MATCH_CONFIRMED, PO_BALANCE_EXCEEDED, PO_QUANTITY_EXCEEDED, PO_LINE_BALANCE_EXCEEDED, BANK_DETAILS_NOT_PROVIDED | 2680 / 1 / 1 / 2716 | 542 / 681 |
| SCAN_CONFLICT | image_only | COMPLETED / REVIEW_REQUIRED, yes | PO_MATCH_CONFIRMED, SOURCE_EVIDENCE_MISSING, TOTAL_RECONCILIATION_FAILED, BANK_DETAILS_NOT_PROVIDED | 3696 / 1 / 1 / 3738 | 1399 / 914 |

Total_processing is measured from workflow start to immediately before final commit, excludes upload/queue wait;
individual operation timings exclude surrounding transition commits. No invented model cost or unreported tokens.
The final atomic-read/failure-usage hardening was regression-tested without spending further live requests.

## F. Persistence and ledger evidence

After all three live runs, the app was stopped/recreated with the same DB/document directory. GET detail
was identical for extracted invoice, full decision/findings, policy, candidates, timings, usage and stages;
GET document SHA256 matched the original PDF for each. **Zero generation calls on reload.**
Live dashboard: total_runs=3, in_progress=0, completed=3, ready=1, review_required=1, blocked=1,
processing_failed=0, interrupted=0. No financial totals or savings were invented.

Canonical SHA256 over every authoritative table column/value, before AND after all live analyses:
`7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398`.
SQLite file hashes are not compared because legitimate run/history writes change the file. The authoritative
rows themselves remain equal; no analysis consumes PO balance. Procurement models/schema/seed are unchanged.

## G. Security

PASS: traversal/Windows/duplicate/Unicode filenames ignored; generated IDs unique; raw PDF kept outside SQLite;
wrong MIME, >8MiB, empty, signature-invalid, multiple files/extra fields/malformed multipart rejected before work;
chunked envelope bounded; extra/wrong/missing file fields also manually verified 400 with no run;
deep malformed PDF becomes technical failure; unknown/malformed run IDs cannot select
filesystem paths; corrupt document ID traversal receives 404; safe serving headers; no paths in document errors.
Tests exercise sensitive exception payloads and confirm no account/API-key strings in responses/logs. Error
codes are allowlisted at contract boundary; provider messages are never persisted or logged. Staged secret/hygiene
verification is performed again before publication. No auth/public hosting/rate limiter was added.

## H. Full regression

Exact final automated commands, repository root:

```powershell
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest-phase04-final --tb=short
.venv/Scripts/python scripts/verify_manifests.py
.venv/Scripts/python scripts/verify_git_hygiene.py
.venv/Scripts/python -m pip check
npm --prefix frontend run build
git diff --exit-code c0d06f07fc3d0d70b26318dc247778402dd1fbab -- backend/app/domain backend/app/documents backend/app/db data frontend tests/fixtures backend/tests/test_finance_engine.py backend/tests/test_document_engine.py Dockerfile .dockerignore
```

| Check | Actual result |
|---|---|
| Final backend suite | **268 passed**, zero failures/errors, one existing Starlette/AnyIO warning, 46.24s |
| Counts | 30 foundation + 99 finance + 100 document + 39 Phase 4 tests |
| Frontend TypeScript/Vite | PASS, 1682 modules, 3.36s; frontend source unchanged |
| Manifests | PASS, 6 vendors / 7 POs / 3 billed invoices / 10 original scenarios |
| Git hygiene | PASS, 11 exclusions, indexed PDFs intact, .env/runtime files ignored |
| Dependency consistency | No broken requirements; new pinned python-multipart==0.0.34 |
| Protected code/data diff | Empty; existing financial/document rules, DB schema, manifests, fixtures and UI unchanged |
| Live API slice | 3/3 desired decisions; actual Uvicorn read/health HTTP check also passed |
| Reload/restart | Full snapshot/PDF reload without inference; queued/running recovery tests pass |

Development failures recorded honestly: first integration run had 31 passing tests and two setup/cleanup errors
because pytest generated an 8MiB parameter ID exceeding Windows path bounds. A first attempted repair encountered
Windows cp1252 decoding of the Unicode filename test; explicit UTF-8 + short IDs resolved it. Integration then
passed 35 tests. First full run: 265 passed / 1 failed because Phase 1 asserted POST uploads did not exist.
Only that obsolete assertion changed from 404/405 to 415 on missing multipart. Next full run: 266 passed.
Two final correctness tests (atomic detail read and failure usage) yield final 268 passed. No unresolved failure.

## I. Contract changes

Only approved shared addition: RunSnapshotV1.execution_error_code: str | None = None, with allowlist/state
validation and backward default. ADR-017 records approval. No other shared field, financial semantics,
matching behavior, provider prompt, seed expectation, fixture, database table or migration changed.
API-local CreatedRun/RunSummary response models do not change financial contracts.

Important files created: api/runs.py; orchestration/documents.py, repository.py, service.py;
tests/test_orchestration_api.py; scripts/smoke_phase04.py; ORCHESTRATION_API.md; this report and two evidence JSONs.
Modified: main.py wiring/lifespan; ai/gemini.py primary-only metadata-free runtime; contracts approved field;
requirements.txt multipart; .env.example document storage; test_foundation.py one obsolete assertion;
README/CONTRACTS/DOCUMENT_ENGINE/DECISION_LOG/PROJECT_STATUS/memory documentation.

## J. Git

Dedicated branch codex/phase-04-orchestration-api from the exact approved checkpoint. Passing commit uses
`feat: integrate persistent invoice processing workflow`; annotated tag phase-04-vertical-slice is created
only after checks. Existing GitHub remote is retained, no force push/default-branch change. Exact SHA,
remote branch/tag verification and clean-tree result are reported in the final publication handoff.

## K. Limitations

Single-process in-memory task scheduling only; queued/running work is interrupted on restart, no replay or
cross-process queue/semaphore. Dashboard currently projects all persisted snapshots in one query; large-history
optimization deferred. No OCR/general layout accuracy guarantee; scans remain source-unverified. No stronger
inference used or claimed. No UI integration, human approval/PO confirmation, reevaluation, policy editing,
auth suite, rate limiter, delete/retention/orphan cleanup, object storage, Docker/paid deployment or Phase 5.
A DB failure after document write can leave an orphan file. Total DB outage can prevent error persistence;
logs stay sanitized and startup reconciles unfinished work when DB access returns. No public release claim.

## L. Gate / completed segment-template checklist

**PASS.** A real uploaded PDF produced a persisted, reloadable, explainable AP decision through real Flash-Lite
extraction and unchanged deterministic controls, with actual stages and no authority mutation.

- [x] Required offline fixture, technical failure, restart, security, live-stage and reload cases pass.
- [x] All earlier tests retained; only the obsolete Phase 1 absent-endpoint assertion updated.
- [x] Three genuine permitted API E2E calls documented; no Flash or metadata requests.
- [x] Ledger/master rows identical; no unauthorized contract/schema/business changes.
- [x] No fake progress, metrics, approvals or source verification.
- [x] PROJECT_STATUS and memory updated from observed evidence.
- [x] Passing checkpoint publication performed only after verification; exact SHA/push in final handoff.

STOP for architectural review. Phase 5 is not authorized.
