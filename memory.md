# AP Compass — Project Memory (living handoff)

**Last reviewed:** 2026-11-19 (IST)
**Repository status:** Phase 3 stabilized; revised required-provider gate PASS with 229 tests and real primary-only scan proof. Architectural review pending; optional escalation disabled/unverified.
**Current authorized segment:** `03.1 DOCUMENT STABILIZATION` only; complete and stop for review.
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
- `03 DOCUMENT ENGINE`: revised gate PASS after stabilization; 229 tests, genuine primary native/scan proof; optional escalation disabled, architectural review pending.
- `04 ORCHESTRATION + API`: real persisted execution; requires passing 02 and 03.
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

**Current task:** Phase 3.1 stabilization complete; revised Phase 3 required-provider gate PASS. STOP for review.
**Evidence:** Final 229 tests pass (129 unchanged Phase 1/2 + 100 document), zero failures, one existing warning;
frontend build, manifest, Git hygiene and dependency checks pass. Financial rules/contracts/DB/API/UI/manifests,
all fixtures and dependencies unchanged. No agents or later phases.
**Runtime:** GEMINI_ESCALATION_ENABLED=false by default/local/sample; native and scans primary-only, no optional
metadata/provider construction/calls. Enabled mode remains bounded, with valid primary retention on optional
outage/timeout/quota and honest failure metadata. No usable primary means technical failure. No evidence upgrade.
**Live proof:** Exactly one extra Flash-Lite SCAN_CONFLICT generation plus primary metadata lookup; zero Flash
requests. Grounded line.net=None, gross=86200, unchanged evaluator REVIEW_REQUIRED with 3600 discrepancy;
all scan evidence remains unverified. Prior native successes remain valid historical evidence.
**Metrics:** 3241ms adapter / 2686ms model; 1399 input, 914 output, 2313 total tokens; thinking not reported.
**Scope decision:** ADR-016 explicitly requires one working provider and makes escalation optional. Stronger
inference is not verified; keep disabled until separately proven, with no more probes in this pass.
**Repository:** codex/phase-03-document-engine from f8ce2026fb18b52fbd1d358d92c4b904311174e1; passing checkpoint
reference phase-03-document-engine. Final SHA/push result in chat after commit. Phase 1/2 tags unchanged.
**Reports:** docs/PHASE_03_1_REPORT.md and docs/PHASE_03_1_LIVE_RESULTS.json; earlier Phase 3 failures preserved.
**Next authorized action:** Architectural review or bounded repairs only; no automatic Phase 4.
