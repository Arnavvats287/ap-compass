# Stable contracts and boundaries — v1

This is the minimum architecture to keep future policy changes local rather than requiring an application rewrite.

## System decomposition

```
frontend (React): dashboard / run workspace / evidence / small policy drawer
      | HTTP JSON, versioned typed response
api (FastAPI): upload + run endpoints + read projections
      |                           |
orchestrator (persisted stages)    document adapter (PyMuPDF/Gemini)
      |                           |
      +--> ExtractedInvoiceV1 ----+
                |
       evaluation engine (pure Python)
         vendor resolution -> PO identity -> line mapping ->
         amount/quantity/duplicate/bank checks -> decision
                |
        DecisionV1 + FindingV1  --> persistence/read projections
```

## Contract objects

- `ExtractedInvoiceV1`: raw and normalized vendor name, invoice number, invoice date, PO reference, currency, invoice net, tax, total, invoice lines (description, optional item code, qty, unit price, net), optional bank instructions, and per-critical-field evidence (`raw_value`, `page`, `quote`, `route`, `evidence_state`). Missing fields must be nullable.
- `EvidenceState`: `NATIVE_VERIFIED | SOURCE_LOCATED_UNVERIFIED | MISSING`. Model-provided quote alone does not establish verification.
- `EvaluationContextV1`: a snapshot of the extracted invoice, canonical vendor (or absence), matching PO candidates, selected PO (or absence), immutable prior billed records, and authoritative procurement records. Record all selection provenance.
- `PolicyV1`: immutable snapshot including `price_tolerance_pct` (Decimal, default `0.02`), `require_explicit_po` (true), `amount_rounding_allowance` (`1.00` INR), `commitment_overrun_allowance` (`0.00`), plus version and effective timestamp. Other fixed gates live in the documented domain rules, not component conditions.
- `FindingV1`: `{code, severity, title, explanation, source_type, evidence_refs[], owner?, next_action?, values?}`; severity `PASS|INFO|REVIEW|BLOCK`, descriptions must be understandable to a nontechnical AP analyst.
- `DecisionV1`: `{outcome: READY_FOR_AP|REVIEW_REQUIRED|BLOCKED, findings[], primary_reason_code?, next_action?, owner?, policy_version}`; exactly one outcome after a completed analysis.
- `RunSnapshotV1`: `{id, execution_state, decision|null, stages[], extracted_invoice|null, candidates[], document_id, source_route?, timings?, usage?, created_at, updated_at}`. Do not mix an incomplete run with a business decision.
- `RunExecutionState`: `QUEUED|RUNNING|COMPLETED|PROCESSING_FAILED|INTERRUPTED`. `StageState`: `QUEUED|RUNNING|PASSED|WARNING|FAILED|SKIPPED`.

## Evaluation rules

- `evaluate(context, policy)` should be deterministic with no DB, network or AI calls; authoritative data passed as immutable snapshots.
- PO identity is decided before PO eligibility. An explicit but mismatched/overbilled PO remains visible as evidence with BLOCK finding.
- Money comparisons use Decimal and documented amount basis. Same PO invoice cannot exceed its remaining net value or remaining line quantities. Price tolerance does not override total authorization.
- For missing explicit PO, an identified plausible candidate may be recommended, but automatic ready requires explicit or audited human confirmation under initial policy.
- `READY_FOR_AP` only if mandatory source-supported fields, verified vendor, eligible PO, line scope, duplicate, arithmetic and currency checks pass. A scanned image with only model-provided evidence is review-only under v1.
- `PROCESSING_FAILED` is a technical run state with decision `null`; reviewable ambiguous business facts are `COMPLETED` with `REVIEW_REQUIRED`.
- `prior_billed_invoice` records are authoritative seed history and are never changed by upload, reevaluation, or demo reset.

## API v1: freeze names, allow additive optional fields

- `GET /api/health`: status and build metadata (no secrets).
- `POST /api/runs`: multipart one PDF; returns `run_id`, execution state; actual upload and processing.
- `GET /api/runs`: recent summary list (one GET, not N+1 per row).
- `GET /api/runs/{id}`: full run snapshot and real stage progress, typed nullable fields.
- `GET /api/runs/{id}/document`: controlled PDF serving for evidence inspection.
- `GET /api/dashboard`: aggregate from persisted run history (no mock production metrics).
- `GET /api/policy`: current policy and version.
- `POST /api/runs/{id}/reevaluate`: OPTIONAL; persist a new evaluation/revision; do not mutate original.

## Business/UI language

- `READY_FOR_AP` -> `Ready to process`; `REVIEW_REQUIRED` -> `Needs review`; `BLOCKED` -> `Blocked`.
- Present *what happened, why it matters, amount affected, who acts, what next* first.
- Human confirmation is a separately recorded action, never the LLM choosing a payment authorization.
- If a new reason code is not recognized by UI, render its provided `title`, `explanation`, `severity`, and `next_action` instead of crashing.

## Database / versioning rules

- Separate `Vendor`, `PurchaseOrder`, `POLine`, `PriorBilledInvoice`, `InvoiceRun`, `RunStage` and `PolicySnapshot`. `Finding` and evidence can initially be JSON on run; add columns/tables only when justified.
- Store source route, model ID, extraction schema version and policy snapshot/version on each run.
- Run-specific processing/errors are not written to the billed ledger. Seed script must be idempotent.
- Prefer additive schema changes and migrations. Avoid destructive table recreation outside an explicitly demo-only reset command.
