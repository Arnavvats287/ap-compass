# AP Compass — Project Memory (living handoff)

**Last reviewed:** 2026-11-19 (IST)
**Repository status:** Phase 5 accepted by user. Phase 5.1 visual refinement PASS: 280 backend + 32 frontend tests, real-data browser QA, zero new model calls; review pending.
**Current authorized segment:** `05.1 VISUAL REFINEMENT` only; complete and stop for review.
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
- `05 OPERATIONS UI`: accepted by user; original checkpoint preserved.
- `05.1 VISUAL REFINEMENT`: PASS, review pending; two rendered iterations, 280 backend + 32 frontend tests, zero new inference calls.
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

**Current task:** Phase 5.1 creative visual refinement complete; PASS; STOP for review. No Phase 6 authorization.
**Base/branch:** phase-05-operations-ui / 8816cff9ee721bfdf2ce35ac5faf4601eb3f18df;
codex/phase-05-1-visual-refinement. Checkpoint-only publication now authorized after fresh acceptance.
Checkpoint name: phase-05-1-visual-refinement; full SHA/remote/clean-tree evidence in publication handoff.
Prior checkpoints/default branch unchanged.
**Design:** Baseline real-app critique before UI changes; two rendered iterations. Retained forest/paper brand,
strengthened existing attention summary and backend monetary comparisons, compacted mobile counts/evidence,
clarified upload and queue/disclosure affordances. Immediate local search value prevents observed fast-keystroke
loss during URL navigation; URL state retained. No new metrics/workflow actions or financial calculations.
**Checks:** Publication rerun:280 backend PASS,50.46s,one existing warning;32 frontend PASS,6.00s. Typecheck/build PASS,
1747 modules, JS308.18kB/CSS39.04kB. Manifests/hygiene/pip/npm tree pass. Original tests/dependencies unchanged.
**Browser:** Actual compiled app8005 and existing persisted data. 15 real views at 1440×1000/1024×900/390×844,
7 deterministic non-persisted states. Keyboard/skip/search/filter/row links/disclosures/source200/reduced motion/
long values/mobile overflow checks pass. Baseline,iteration1,final screenshots in ignored tmp/phase051-*.
Initial iteration1 keyboard timeout reproduced character loss; fixed and final full QA passes.
**Audits:** Hallmark app/redesign rendered 0FAIL/0WARN/3ANSWERED (5 routes/25 shots), final static 0FAIL/0WARN/
1ANSWERED. Vercel review and Taste app critique complete. Marketing hero/section pacing/photo/shader/loop
recommendations rejected for operational usability. No formal accessibility certification claim.
**Truth:** Zero new Gemini calls or API mutation requests. Four snapshots/summaries identical before/after final
QA; fingerprint 790793570c14d5821823cc0c38de5e6beed6ace38de906c6f443dfdbf1871c91.
Authoritative-row hash still 7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398.
Backend/data/contracts/API/query/format/financial/document/provider/orchestration/security unchanged. Scan still
printed86200,expected82600,difference3600,optional line net unknown; source uncertainty remains independent.
**Demo data:** Reused Phase4 smoke DB/documents runtime/phase04-smoke-0221866e9e214f3a84149d1f79098bd9;
4 analyses ready1/review1/blocked2; flagged known net INR130000 including repeated analyses, not savings or
unique payable exposure. Existing live blocked run3af82d60d6624971b7aa48de920407d5 stillPO-3015,remaining
25000/net30000/excess5000,gross35400,Procurement owner/action. No resubmission performed.
**Limits:** Browser-dependent native PDF embed can be blank in mobile headless Chrome; open-source fallback
remains. 100 recent-run scope; no Confirm PO/approval/reevaluation/policy/model selector/batch/auth/deployment.
**Reports:** docs/PHASE_05_1_CRITIQUE.md (pre-edit), docs/PHASE_05_1_REPORT.md (before/after matrix,commands,
audits,design decisions,limitations). Phase5 report remains historical accepted evidence.
**Publication QA:**15 real-data views +7 deterministic states pass in tmp/phase051-publish; separate Chrome
sticky/no-column-overlap/mobile-order/amount/caveat checks pass. Backend/data diff empty. No UI changes or new
inference in publication task. docs/PHASE_05_1_REPORT.md sectionJ records exact publication checks.
**Next:** Review only; no automatic Phase6 or further visual repair.
