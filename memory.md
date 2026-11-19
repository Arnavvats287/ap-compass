# AP Compass — Project Memory (living handoff)

**Last reviewed:** 2026-11-19 (IST)
**Repository status:** Phase 5 connected operations UI PASS: 280 backend + 32 frontend tests, one actual UI inference, real-data browser QA; architectural review pending.
**Current authorized segment:** `05 OPERATIONS UI` only; complete and stop for review.
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
- `04 ORCHESTRATION + API`: ACCEPTED by explicit user review; checkpoint unchanged.
- `05 OPERATIONS UI`: gate PASS; 280 backend + 32 frontend tests, real UI upload and viewport/interaction QA; review pending.
- `06 SCENARIOS + EVAL`: richer edge cases and frozen evaluation; after connected vertical slice.
- `07 RELEASE`: security checks, deploy smoke test, real video and submission; after core gates.

Read `docs/SEGMENTS_AND_PARALLELISM.md` for ownership, scope cuts and acceptance gates.

## Current known unknowns (not blockers for 01)

- Primary Flash-Lite is verified for native/scan; stronger inference remains disabled/unverified.
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

**Current task:** Phase 5 operations UI complete; gate PASS; STOP for architectural review. Phase 6 not authorized.
**Base/branch:** 13fe35d792c2fb47a84604e21966ad4a2bd2048b / codex/phase-05-operations-ui.
**Checkpoint:** phase-05-operations-ui; resolve annotated tag for SHA. Exact final commit/push/clean-tree
verification in publication chat after commit. Previous tags and default branch preserved.
**Checks:** 280 backend (268 original unchanged + 12 projection/static tests) and 32 frontend tests PASS;
TypeScript/build PASS (1747 modules), manifests/hygiene/pip PASS, npm tree/audit clean. One existing warning.
**UI:** / overview, /runs URL filters/search, /runs/:id PDF/decision/findings/owner/action/evidence/PO/diagnostics.
Central typed API/Query, active-only 1000ms polling, terminal invalidation, no client financial decisions or
source verification. Exact decimal formatting without Number-based money arithmetic; unknowns stay unknown.
**Live:** One genuine browser upload of OVERBILLED_PARTIAL, run 3af82d60d6624971b7aa48de920407d5. Actual
RUNNING/read stage observations then COMPLETED/BLOCKED. One Flash-Lite generation, no stronger calls;
542 input / 920 output tokens. extraction3312/matching2/evaluation2/total3389ms. Aster PO-3015 retained;
net30000/gross35400 vs remaining25000/excess5000, Procurement action; returned source refs native verified.
**Reload/ledger:** Source opened, new queue/dashboard data and identical reload verified without new inference.
Hash unchanged: 7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398. PDF popup harness
initially matched iframe; fixed and resumed same completed run without resubmission. No provider/business failure.
**QA:** Actual Chrome, 15 real-data captures at1440/1024/390 plus7 deterministic API states, keyboard/skip/
filters/disclosures, reduced-motion, no clipping or uncaught app JS. Deterministic states not persisted as real
runs. Screenshots ignored in tmp/phase05-qa. Hallmark v2 app/redesign -> Vercel -> Taste2.5 critique; marketing
hero/shader/photo/loop prescriptions rejected. Skill files persist in ignored tmp/phase05-skills, not global.
**Backend scope:** Approved known flagged invoice NET grouped by currency, missing count disclosed, repeat
analyses count; plus reported frontend deep-link fallback blocker fixed with API/asset404 preservation.
No shared contracts/finance/document/AI/DB/orchestration/seeds/fixtures/original tests changed. ADR-018.
**Demo:** Local compiled UI/backend8005, Vite5175 (older8000 process untouched). Existing Phase4 smoke DB/docs
reused; now4 submissions (ready1/review1/blocked2), known flagged net INR130000 including repeat analysis.
Not unique payable exposure/savings. OPERATIONS_UI documents paths and default development commands.
**Limits:** Browser-dependent PDF embed with open-source fallback;100 recent-run filter scope; no Confirm PO,
approval, reevaluation, policy editor, batch/model selector/ERP/email/payment/auth suite/new scenarios/deployment.
Original single-process restart behavior remains; no general model-accuracy/accessibility-certification claim.
**Reports:** PHASE_05_REPORT, OPERATIONS_UI, PHASE_05_DESIGN_NOTE/QA and sanitized UI_QA/LIVE_RESULTS JSONs.
**Next authorized action:** Architectural review or explicitly requested repair only. No automatic Phase 6.
