# AP Compass — Project Memory (living handoff)

**Last reviewed:** 2026-11-19 (IST)
**Repository status:** Phase 4 vertical slice PASS: 268 tests, three genuine API E2E outcomes, reload proof, unchanged ledger. Architectural review pending.
**Current authorized segment:** `04 ORCHESTRATION + API` only; complete and stop for review.
**Deadline:** Saturday 2026-11-21 (IST); target Friday evening feature freeze.
**Maintainers:** Builder owns product decisions; Codex implements one authorized phase; architectural review gates further work.

> Repo-local continuity. Status is evidence, not completion by assertion. Latest user acceptance/routing adjustment is recorded in ADR-016 and the handoff below.

## North star

Build **AP Compass â€” Invoice Operations & Exception Resolution** for Zamp AI Solutions Associate PS-1. The product is a finance operations workstation for an AP analyst: real invoice PDF â†’ real extraction â†’ authoritative vendor/PO checks â†’ deterministic decision â†’ evidence, next action/owner, live stage history and a usable dashboard. The buyer should see what happened, why, how much is affected, and who acts next. **No payment/posting authority.**

Zamp's required deliverables: a **live, runnable process** and a **five-minute-or-shorter demo video**. Show actual stages as they execute, past runs/statuses/outputs, a happy path, and meaningful nontrivial edge cases. The official PDF is the submission authority; `docs/REFERENCE_SPEC_V3.md` is background design, not automatic feature authorization.

## Nonnegotiable financial and AI boundaries

1. Model extracts invoice data only. Deterministic code owns vendor/PO authorization, duplicate checks, money, policies, decisions and next-action mapping.
2. Python `Decimal` or integer minor units for money. Compare invoice **net** against PO **net**, not gross vs net. Validate quantities, unit-price tolerance, stated totals and mapped item scope.
3. **PO identity precedes financial eligibility.** An explicitly referenced overbilled PO is still recognized, then blocked with the correct exception; don't drop it as `PO_NOT_FOUND`.
4. The billed ledger and PO commitments are authoritative and immutable under analysis runs. Re-running an invoice **must not consume PO balance**.
5. Missing/uncertain fields remain `null`, never zero or fabricated. Native-text evidence, unverified scanned-source evidence, and missing evidence must not be conflated.
6. Business outcome `READY_FOR_AP | REVIEW_REQUIRED | BLOCKED` is separate from execution `QUEUED | RUNNING | COMPLETED | PROCESSING_FAILED | INTERRUPTED`. Technical failure yields **no successful business decision**.
7. Actual persisted stages, never fake progress or financial metrics. Financial readiness is **not** posting, payment, or final Finance approval.
8. Untrusted PDFs cannot instruct the system or obtain tools/DB write access. Keep provider secrets server-side and bank data out of logs/unauthenticated diagnostics.
9. Business rule changes use isolated evaluators + policy versions and regression tests; do not rewrite UI, prompts, API and matching engine for simple tolerance updates.
10. Do not build LangGraph, autonomous agents, vector search, ERP/email integration, payments, a full approval workflow, learned auto-approval hints, or a batch inbox for this submission.

## Locked initial stack and boundaries

- Frontend: React + TypeScript + Vite; Tailwind + shadcn/ui if it doesn't obstruct shipping; TanStack Query for server state.
- Backend: FastAPI + Pydantic, pure Python finance domain engine, SQLAlchemy/SQLModel, SQLite on persistent single-instance storage.
- Documents: PyMuPDF native extraction; one Gemini model for structured extraction, with multimodal path for scans. **Model ID/API entitlement must be smoke-tested with the actual key**, not assumed.
- Progress: persisted stage transitions + polling. Single deployment container if feasible; no distributed queue.
- Primary views: dashboard/review queue, single-route live-run/decision/evidence workspace; small policy control only after vertical slice.
- Authoritative contracts: `docs/CONTRACTS.md`; seed oracle: `data/seed_manifest.json`; fixture oracle: `data/fixture_manifest.json`.

## Current fixture baseline (synthetic, not measured results)

Seed: **6 vendors, 7 purchase orders, 3 prior billed invoices**. Fixture manifest: **10 expected scenarios**. Generate **4 native-text PDFs in Segment 01** only. Complete edge-case PDFs after core pipeline is working.

Minimum happy path: `HAPPY_CLEAN`, `HAPPY_PARTIAL` (partial invoice is within remaining PO authorization). Critical business regressions: `OVERBILLED_PARTIAL`, `DUPLICATE_REISSUED`, `AMBIGUOUS_PO`; later scanned conflicting total, changed bank instruction, unknown vendor and injection tests. Final 2â€“4 showcased edge cases are **not fully frozen**: preserve the capabilities now and choose one creative scenario with the builder after MVP. See `docs/EDGE_CASE_BACKLOG.md`.

## Segments and dependency gates

- `01 FOUNDATION`: accepted by user architectural review; checkpoint `phase-01-foundation` unchanged.
- `02 FINANCE ENGINE`: accepted by explicit user review; tag phase-02-finance-engine unchanged.
- `03 DOCUMENT ENGINE`: ACCEPTED by explicit user review; primary native/scan evidence; optional escalation disabled.
- `04 ORCHESTRATION + API`: gate PASS; 268 tests and genuine persisted API E2E; architectural review pending.
- `05 OPERATIONS UI`: live dashboard/workspace against actual API; shell can start earlier, final integration after 04.
- `06 SCENARIOS + EVAL`: richer edge cases and frozen evaluation; after connected vertical slice.
- `07 RELEASE`: security checks, deploy smoke test, real video and submission; after core gates.

Read `docs/SEGMENTS_AND_PARALLELISM.md` for ownership, scope cuts and acceptance gates.

## Current known unknowns (not blockers for 01)

- Which Gemini model is actually enabled and adequate under the project's own API key?
- Exact persistent deployment host and ability to keep app available during interview?
- Whether to implement analyst Confirm-PO action and policy rerun after MVP passes?
- Final creative fourth demo edge case (decide later; no schema rewrite permitted without review)?

## Work/review handshake

1. At start of a Codex task, read `AGENTS.md`, this `memory.md`, `PROJECT_STATUS.md`, `docs/CONTRACTS.md`, and the relevant segment prompt. Do **only** the authorized segment.
2. Before coding: inspect existing repo and choose small bounded changes; **do not** auto-advance segments.
3. Before finishing: run real commands/tests, show results, update `PROJECT_STATUS.md` with evidence, and use `prompts/SEGMENT_REPORT_TEMPLATE.md` for the handoff. Never mark gates passed without proof.
4. Builder sends Codex report (plus logs/diffs if failing) to ChatGPT. ChatGPT reviews it and issues exactly the next bounded prompt or a repair prompt.
5. Changes to financial invariants, shared typed contracts, DB schema or segment scope require explicit approval and a line in `docs/DECISION_LOG.md`.

## Last handoff

**Current task:** Phase 4 orchestration + API complete; gate PASS; STOP for architectural review. Phase 5 not authorized.
**Base/branch:** c0d06f07fc3d0d70b26318dc247778402dd1fbab / codex/phase-04-orchestration-api.
**Checkpoint:** phase-04-vertical-slice; resolve annotated tag for SHA. Exact commit/push/clean-tree verification
in final chat after commit. Preserve all previous tags and default branch.
**Checks:** 268 passed (30 foundation, 99 finance, 100 document, 39 new integration/API), zero failures/errors,
one existing warning, 46.24s. Build 1682 modules PASS; manifests/hygiene/pip PASS. Actual Uvicorn HTTP
health/policy/dashboard/runs PASS and shutdown clean, no inference. Only obsolete Phase 1 upload-absence assertion
updated to expect 415. Initial oversized test-ID and obsolete assertion failures resolved and documented.
**Live:** Exactly three actual API E2E Flash-Lite generations, no metadata/Flash requests. HAPPY_CLEAN COMPLETED/
READY; OVERBILLED_PARTIAL COMPLETED/BLOCKED with PO-3015, value+quantity controls; SCAN_CONFLICT COMPLETED/REVIEW,
gross86200/discrepancy3600/optional line netNone, all scan refs unverified. Native refs independently verified.
Actual input/output tokens: 543/913, 542/681, 1399/914. Extraction/total ms: 3213/3259, 2680/2716, 3696/3738.
**Persistence:** All full live snapshots/documents identical after app recreation, zero model calls on reload.
Authority row hash unchanged: 7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398.
RunStage rows exclusively own stages; payload stages=[]; detail atomic joined query. Policy version drift fails.
**Execution:** Tracked async tasks, per-app semaphore1, queued runs wait, no transactions during inference.
Restart reconciles queued/running as INTERRUPTED/SERVER_RESTART with no active stages/replay. Expected failures
persist sanitized categories, no business decision; actual business REVIEW/BLOCK remain COMPLETED.
**Documents:** AP_COMPASS_DOCUMENT_DIR default runtime/documents; bounded one-PDF upload, opaque IDs, atomic
writes, run-scoped safe serving. Credential-less app boots/health works; extraction fails CONFIGURATION.
**Contract:** Only approved execution_error_code optional field + state/allowlist validation, ADR-017.
No DB schema, finance/matching/evidence rules, seed/fixture/PDF, frontend or Docker change. Multipart dependency added.
**Limits:** Single process/worker, no durable queue/restart replay/auth/retention/orphan cleanup/cloud/deployment.
Dashboard currently projects all snapshots in one query. No generalized accuracy claim, OCR, stronger model,
UI integration, approval or reevaluation. DB outage can prevent error persistence; do not claim successful completion.
**Reports:** docs/PHASE_04_REPORT.md, docs/PHASE_04_LIVE_RESULTS.json, docs/PHASE_04_FAILURE_EXAMPLE.json,
docs/ORCHESTRATION_API.md. Historical Phase 3 failures/scope adjustment remain in their original reports/ADRs.
**Next authorized action:** Architectural review or explicitly requested repair only. No automatic Phase 5.
