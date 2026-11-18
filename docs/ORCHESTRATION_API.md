# Phase 4 — Persistent orchestration and API

The application now coordinates the existing document adapter and pure financial engine.
It does not interpret invoices or make financial decisions in routes or orchestration.

## Flow and ownership

`POST /api/runs` bounds/validates the upload, atomically stores the accepted bytes under a
server-generated opaque document ID, creates a QUEUED snapshot and five stage rows, and
submits an in-process asyncio task. It returns HTTP 202 without awaiting extraction.

`RunService.process(run_id)` is independently callable. One application-level semaphore
permits one complete workflow at a time. Waiting tasks leave their runs QUEUED. The flow is:

1. RUNNING / extracting_invoice: read this run's stored PDF and await the injected extractor.
2. matching_records: validate all trusted vendor/PO/billed payloads and call existing `build_context`.
3. evaluating_controls: insert-or-verify immutable PolicySnapshot and call existing `evaluate`.
4. finalizing: persist decision, findings, primary reason, owner/action, candidates, exact policy,
   source/model/schema, available usage, measured timings, and COMPLETED state.

All database transactions are short and closed before model inference. Authority snapshots
are read only. No Vendor, PurchaseOrder, POLine or PriorBilledInvoice writes occur during analysis.
READY, REVIEW and BLOCK are successful COMPLETED analyses. Technical failures have decision=null.

`InvoiceRun.payload` contains a validated RunSnapshotV1 with **empty stages**.
`RunStage` rows are the sole authoritative stage representation. Detail composes both using
one joined SQL read, avoiding run/stage read skew even with sqlite3 legacy transaction behavior.
Legacy embedded stage arrays are ignored on reads and stripped on updates. No schema migration
or new tables were needed. Policy rows with a reused version and different payload fail closed.

## Lifecycle and restart

Fixed order: received, extracting_invoice, matching_records, evaluating_controls, finalizing.
Creation marks received PASSED with timestamps; remaining stages are QUEUED with no invented start.
Each actual work boundary persists RUNNING then PASSED; a business exception does not fail a stage.
Technical failure marks the active stage FAILED and later queued stages SKIPPED, with finish timestamps.
Skipped stages have no fictitious start time. No progress sleeps/timers exist in the service.

Shutdown cancels tracked tasks and awaits them. On next startup, every leftover QUEUED/RUNNING
run is marked INTERRUPTED / SERVER_RESTART, decision=null; active stages become FAILED and queued
stages SKIPPED. Nothing automatically replays a model request. Existing terminal history is retained.
Provider clients are scoped to one extraction and closed in finally, including cancellation.

## Files and upload bounds

AP_COMPASS_DOCUMENT_DIR defaults to repository-relative runtime/documents. AP_COMPASS_DB_PATH
defaults to runtime/ap-compass.db. Configure both to persistent storage together.
Never use an uploaded filename. Disk names are generated lowercase UUID hex plus .pdf.
Writes use an exclusive temporary file, fsync and atomic replace. IDs must match 32 lowercase
hex characters; symlinks/resolved paths outside the configured root are refused.
Documents resolve only through an existing run record. PDFs are never stored in SQLite JSON.

Multipart must contain exactly one UploadFile named file, MIME application/pdf. The complete
envelope is bounded at 8 MiB + 64 KiB before multipart parsing/spooling, including chunked input;
the file is read with an 8 MiB + 1 byte cap and rejected above 8 MiB. Empty/signature-invalid
files receive 400; wrong MIME 415; size violations 413. Extra files/fields and malformed multipart
receive 400. Valid signature is request acceptance, not a claim of successful deep parsing.
Deep parser failures occur in the persisted asynchronous run, before inference.

The whole-envelope cap also bounds filename/header overhead. This matters because multipart
part limits alone do not bound uploaded file spooling; see [Starlette request documentation](https://starlette.dev/requests/).
The added parser is [official python-multipart 0.0.34](https://pypi.org/project/python-multipart/0.0.34/).

## Runtime extraction and safe telemetry

Production `extract_runtime_pdf` uses gemini-3.5-flash-lite only, with escalation disabled.
Invalid/missing credentials or enabled optional configuration fail the run with CONFIGURATION,
without preventing application startup or health checks. No Flash requests are made.
Production generation has no mandatory models.get dependency; actual SDK generation errors
remain typed. Standalone diagnostics retain explicit metadata verification.
Existing bounded parsing, inference timeout/retry and evidence grounding are unchanged.

Run metadata uses existing model_id, source_route, extraction_schema_version, usage and timings.
Actual returned model version is preferred where reported. Failed generations count; metadata-only
attempts do not. Token sums stay null if any contributing call has unknown usage; known reported
usage is retained even for an invalid extraction response. Timings use perf_counter, in milliseconds:
extraction, matching, evaluation and total_processing (workflow start to immediately before final
commit; excludes queue wait/upload). Technical failure records elapsed work and total time as well.
No cost/confidence/savings are fabricated. Logs contain only run ID, internal stage, allowlisted category.

## Frozen API responses

| Endpoint | Behavior |
|---|---|
| GET /api/health | Existing real SQLite health response; no credential dependency |
| POST /api/runs | Multipart file; 202 {run_id, execution_state: QUEUED} |
| GET /api/runs?limit=50 | Summary array, 1..100 limit; newest first; one query, no stage N+1 |
| GET /api/runs/{id} | Reconstructed RunSnapshotV1, authoritative stage rows; 404 unknown |
| GET /api/runs/{id}/document | That run's PDF, fixed inline invoice.pdf; 404 unknown/missing/unsafe |
| GET /api/policy | Current immutable PolicyV1; no editing |
| GET /api/dashboard | Persisted counts: total_runs, in_progress, completed, ready, review_required, blocked, processing_failed, interrupted |

Summary fields: id, created_at, updated_at, execution_state, nullable outcome/vendor_name/invoice_number/
total/currency/primary_reason_code/owner. Decimal totals serialize as strings. Dashboard has no monetary
aggregation or cross-currency sums. It currently projects persisted snapshots in one query; large-history
optimization is deferred. Document headers: application/pdf, Cache-Control:no-store, nosniff.
No reevaluation endpoint, approval workflow, policy editor, upload UI or dashboard UI was added.

## Approved contract addition and limitations

Only shared addition: RunSnapshotV1.execution_error_code: str | None = None (ADR-017).
It is null in QUEUED/RUNNING/COMPLETED; technical terminal states accept only allowlisted codes.
Old snapshots omitting it remain readable. Error messages, provider bodies and bank data never enter it.
Unexpected exceptions map to INTERNAL_ERROR; restart reconciliation uses SERVER_RESTART.

This is a single-process/local persistent store: run one Uvicorn worker against its DB/document directory.
There is no durable/distributed queue, automatic retry after restart, cross-process semaphore, retention/delete,
authentication, public-hosting rate limiting, cloud storage, UI integration or deployment work.
No guarantee of multi-process restart coordination is made. A filesystem write followed by database failure
can leave an orphan document; no delete/repair workflow was authorized. Health tests DB availability only.
Filesystem/database failure may prevent error persistence; sanitized task logging and next-start recovery
are the fallback, never fabricated completion. Scans remain unverified and conservatively require review.

## Local use

```powershell
.venv/Scripts/python -m pip install -r backend/requirements-dev.txt
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --env-file .env --host 127.0.0.1 --port 8000
curl.exe -F "file=@tests/fixtures/HAPPY_CLEAN.pdf;type=application/pdf" http://127.0.0.1:8000/api/runs
```

Keep the key only in ignored server-side .env. Without --env-file, configure process environment explicitly.
Normal automated tests use deterministic fakes and no network/key. Manual live smoke is opt-in:
`.venv/Scripts/python scripts/smoke_phase04.py --live --output tmp/phase04-live-results.json`.
It uses real POST/detail/document endpoints via ASGI, the actual default runtime extractor, persisted DB/files,
and app recreation. It caps generation at three total requests, forbids metadata/other-model requests, and
retains only sanitized synthetic report fields. Do not rerun it casually; it consumes real provider quota.
