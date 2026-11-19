# AP Compass — Project Memory (living handoff)

**Last reviewed:** 2026-11-19 (IST)
**Repository status:** Native source association and recognized table completeness verified on development-only fixtures.
**Current authorized segment:** `06B.2E.1 NATIVE SOURCE GENERALIZATION & INVOICE COMPLETENESS` only.
**Deadline:** Saturday 2026-11-21 (IST); target Friday evening feature freeze.
**Maintainers:** Builder owns product decisions; Codex implements one authorized phase; architectural review gates further work.

> Repo-local continuity. Status is evidence, not completion by assertion. Latest user acceptance/routing adjustment is recorded in ADR-016 and the handoff below.

## Phase 6B.2E.1 handoff

Base `4bac08cd84226703cdcef2b76089f72f4e920cbe`. Split-label and complete visual table quotes can verify with bounded delimiter formatting when field/row, value, currency and conflict checks pass. In three synthetic omission cases the base returned Ready on reconciling facts. The new recognized-table gate now withholds line evidence and the existing source rule returns Review. One fully supported reformatted invoice moved from 0/18 to 18/18 native references and Ready. Full regression passed 508 backend and 58 frontend tests, plus real private Docker/Chrome and persisted restart checks. Frozen results and PDFs matched the base, with zero held-out access and zero Gemini requests. Financial logic, contracts and parser subprocess limits stayed unchanged. See `docs/PHASE_06B2E1_SOURCE_GENERALIZATION_REPORT.md`. Stop before independent evaluation.

## Phase 6B.2D.2 handoff

Base `b06b34d01a07f6543bfe048d22627be115f37033`. Private mode uses fail-closed backend Basic auth and exact origin, and defaults to uploads disabled. Admission is bounded before reading requests, file/DB creation is compensated on failure, and a same-database instance lock protects restart reconciliation. One private Docker worker ran as UID 10001. Chrome rendered authenticated source PDF, saved an audited missing-PO reassessment and previewed 5% tolerance while preserving original decisions. Normal container recreation kept four snapshots, PDFs and audit history. Complete regression passed 488 backend and 58 frontend tests. No production business, evidence or provider changes, no benchmark changes, and zero Gemini requests. The runbook uses labeled controlled fixtures and works through outages. Remote gateway and public deployment remain outside this gate. See `docs/RELEASE_HARDENING_REPORT.md` and `docs/FIVE_MINUTE_DEMO_RUNBOOK.md`.

## Phase 6B.2D.1 handoff

Base `bc674cac698a1c09ab94ff8b93592c50b5ebdad2`. Original synthetic red tests showed legacy USD and `$` amounts could verify against extracted INR and reach Ready. The shared legacy/geometry amount predicate now requires exact magnitude and compatible printed denomination, checks the actual raw source token, and keeps quantities denomination-free. Conflicting amounts remain source-uncertain and enter Review. The existing proven currency mismatch against PO authority still Blocks. The bounded omitted-row, issuer-role, and equal-amount diagnostics did not add any completeness or layout rule. Frozen result and fixture hashes stayed intact. No live inference or benchmark reruns. See `docs/PHASE_06B2D1_EVIDENCE_INTEGRITY_REPORT.md` and stop before release hardening.

## Phase 6B.2C.4 handoff

Production at `9c2e795a3090f340696e6aaf9be65cde45d3d33f` stayed byte-identical. The original archive, oracles, source annotations, scorer and four published reports kept their hashes. Post-fix Layer B evidence improved from 122/135 to 123/135 development and 37/100 to 54/100 held-out. Exact decisions stayed 9/10 and 3/6. Development scope routes to Procurement; held-out H04 remains AP due to unsupported item-code evidence. Live used eight attempts. H01 completed with 11/11 exact critical fields and unnecessary Review. H04, OVERBILLED_PARTIAL and H05 failed technically. H03 and H06 skipped at the cap. No completed live non-Ready target. No observed false Ready or unsafe attestation. See `evaluation/results/postfix-v1/`, `docs/POSTFIX_V1_OFFLINE_COMPARISON.md`, and `docs/PHASE_06B2C4_POSTFIX_VALIDATION.md`. Stop for release review.

## Phase 6B.2C.3 handoff

From `fb2a4535cc3e32a15c139fdfc59250b85e84a936`, added bounded parser-owned rectangles for narrow adjacent header-cell and table-row localization. All 26 original synthetic test cases pass, covering repeated distinct rows, mistaken buyer/amount associations, and conflicting totals or PO references. Verified explicit items outside an approved matched PO route to Procurement with an authorization and amendment-or-correction action. Missing or unverified identifiers remain AP clarification. Image-only source Review now gives scan-specific guidance. No Gemini, held-out rerun, policy, ledger, API or UI changes. The four frozen result hashes are unchanged. Exact tests, performance and snapshot evidence are in `docs/PHASE_06B2C3_REPORT.md`. Stop before independent post-fix validation.

## Phase 6B.2C.2 handoff

From `0e7c421573023ce0c3da2433aed0409d5bedfa7a`, sealed the development runner and first results before opening the independent archive. Development finance 13/13, offline PDF 9/10 exact decisions. Held-out offline 3/6 exact, 0/3 false-ready, 3/3 unnecessary Review. All 72 labelled critical fields matched. Live H01 and H03 completed with four total primary generations, including HTTP 503 and 504 retries. Both decisions were unnecessary source Review on exact critical fields. H04 and H05 skipped at the cap. No production behavior or frozen inputs changed. First results and exact denominators are in `evaluation/results/v1/` and `docs/PHASE_06B2C2_BENCHMARK_REPORT.md`. Private originals remain byte-identical in ignored storage. Benchmark verification passed: 394 backend plus 2 known xfails, 19 runner, 58 frontend. Stop for remediation review.

## Phase 6B.2C.1 handoff

Verified base `64bf8695b34e2125a8a240f8e1f233dbd745ce88`. Frozen development registry `data/golden_dataset_v1.json` contains 14 entries and 13 unique submissions, including ten hash-locked PDFs. `AMBIGUOUS_PO` is shared with human workflow regression and counts once per submission. Both separate PO-action targets passed with trusted facts. F1–F3 remain specification-only historical probes. `SCOPE_UNAUTHORIZED_LINE` correctly reviews only line 2, but the owner and action differ from the frozen Procurement and amendment/correction targets. Both mismatches are recorded as strict expected failures. No production logic changed. `STATEMENT_PRIOR_BALANCE` is Ready on trusted current-invoice facts, with provider extraction and grounding still unmeasured. Both new PDFs reproduce byte-for-byte and were visually inspected. Zero Gemini calls and no held-out data generated or inspected. Detailed commands and gate are in `docs/PHASE_06B2C1_REPORT.md`. Stop for review before executing a dataset-wide integration or live benchmark.

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
- `05.1 VISUAL REFINEMENT`: accepted by explicit user review; checkpoint4e9665daac7dda661f19217ab9ba8630c640b839 preserved.
- `06A POLICY IMPACT + TRACE`: PASS,review pending;299 backend +47 frontend tests,one live PRICE extraction,zero-AI previews and two creative browser iterations.
- `06B.1 HUMAN PO RESOLUTION`: locally verified; source/ledger immutable; stop for review.
- `FURTHER 06B SCENARIOS`: LOCKED; no additional creative-case/correction authorization.
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

## Historical Phase 6A handoff

**Task:** Phase6A complete; PASS; STOP for architectural/visual review. No Phase6B authorization.
**Base/branch/checkpoint:**4e9665daac7dda661f19217ab9ba8630c640b839 (phase-05-1-visual-refinement),
codex/phase-06a-policy-decision-trace,phase-06a-policy-decision-trace. Exact new SHA/remote/clean-tree
verification accompanies final publication handoff. Previous checkpoints/default branch preserved.
**Policy:** API-local POST /api/runs/{id}/policy-preview; only Decimal0.02/0.05,no floats/extra controls.
Stored invoice + current trusted authority + copied recorded PolicyV1 → same build_context/evaluate.
Original run/active policy never change; preview is transient,not persisted. HTTP404/409/422 safe rejections.
Tests forbid extraction,PDF reads and non-SELECT SQL. Current-authority reload and deterministic repeat proven.
No shared contract,DB schema,finance/document/AI rule,seed or original fixture changes. ADR-019.
**Trace:** Five returned stages map to connected execution nodes; PASSED does not mean ready. Separate
recorded business outcome. Actual measured timings preferred,then valid timestamps,else—; subsecond ms shown.
Only RUNNING connector moves; reduced motion disables connector/spinner/selection/result motion.
**Creative scope:** Supplementary user override explicitly includes overview/shared visual system. Actual
screens/critique/spec before changes; absent tmp/ui-reference.mp4 acknowledged. Editorial Georgia/system
sans,asymmetric attention bento,deep forest policy/trace,mint/citrus and readable white queue. Original CSS/
native controls,no new design dependency or copied Pro source. Two rendered browser iterations and audits.
**Tests:**299 backend PASS,52.18s,one existing Starlette warning;47 frontend PASS,6.55s; typecheck/build PASS,
1751modules,JS316.59kB/CSS61.08kB (gzip99.34/10.87kB). Manifests/hygiene/pip PASS;npm audit0 vulnerabilities.
**Browser:** Core15 actual-data views +7 test-only states,focused12 recorded/preview states +3 running states
at1440×1000/1024×900/390×844 PASS. Keyboard/focus/long values/no-overflow/real states/reduced-motion and
all persisted snapshots/active-policy comparisons pass. Hallmark0FAIL/0WARN/3ANSWERED; Vercel/Taste review.
One concurrent Chrome PDF network-idle timeout resolved by unchanged-suite sequential rerun; no weakened test.
**Live:** Exactly1 Flash-Lite generation forPRICE_3PCT; no metadata/stronger calls. Run d2269cade6cb4dca94e6239e5658d25a,
native_text,8 critical headers match,13 refs independently NATIVE_VERIFIED. Qty10/unit1030/net10300/tax1854/
gross12154/PO-2010. Recorded2% REVIEW_REQUIRED/PRICE_VARIANCE; preview5% READY_FOR_AP; original unchanged.
Input542/output681 tokens; extraction5807/matching2/evaluation2/total5852ms. Actual running trace screenshot
captured during that call; later redesign running captures are explicitly TEST_ONLY.0 new inference in previews
or creative override. Overbilling5% still BLOCKED; duplicate5% still BLOCKED/EXACT_DUPLICATE (offline API).
**Authority:** hash still7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398. Five-run snapshot
fingerprint83b19fa7ce0fa3dadf5de1d0a244e6552c13453e5cf8bfb0b779838fca993881 stable during final core QA.
**Local demo:**8006 using runtime/phase04-smoke-0221866e9e214f3a84149d1f79098bd9 DB/documents. Five analyses:
ready1/review2/blocked2; flagged INR net140300 includes repeat analyses,not savings/unique exposure. Original
PRICE remains review in history despite ready preview. Older8005 left untouched. Runtime one-generation guard
and logs ignored. New PRICE PDF generated from unchanged manifest; original five PDF bytes unchanged.
**Docs:**POLICY_PREVIEW,PHASE_06A_DESIGN/REPORT/LIVE_RESULTS,ADR-019; UI/API docs updated. Screenshots ignored
in tmp/phase06a-design-before,iteration1,after (policy subdirectories). No giant screenshots committed.
**Limits:**Current rather than historical authority in previews; no saved simulation/global policy editor/
confirmation/approval/reevaluation/action history/new creative fixtures/deployment. Native mobile/headless PDF
can be blank; source-open fallback works. Single-process/in-process queue and bounded worklist remain.
**Next:** Review only; do not start Phase6B.


## Phase 6A.1 handoff — 2026-11-19

Base95e6e66ea6c9ce7d48f10466f40d9aa4af0e89d1; branch codex/phase-06a1-signature-ui;
checkpoint phase-06a1-signature-ui. Complete SHA/remote proof accompany final publication handoff.
User accepted6A functionality but rejected visual quality; this is a frontend-only repair, not6B.
Baseline + two fresh rendered iterations: tmp/phase06a1-before,iteration1,after. Actual app8006 and existing
five live analyses reused. No upload/new inference; generation guard still contains only the prior6A call.
Attention outcome orbit uses real counts, flagged NET retains repeated-analysis/currency caveats. Compact
source/decision spread top323px vs414px baseline. Evidence precedes optional audit; ambiguousPO alternatives
stay initially visible. Full-width process spine and independent outcome destination; actual-only motion.
Policy comparison full width, original recorded badge retained in desktop rail; semantics/API unchanged.
299 backend PASS52.90s (one existing warning),48 frontend PASS5.72s,typecheck/build/manifests/hygiene/pip
PASS,npm audit0. JS319.50kB/gzip100.13,CSS70.59kB/gzip12.23; no dependency additions. Core15 actual views
+7 controlled states; policy12 recorded/preview +3 labelled TEST_ONLY active traces. Additional keyboard
anchor/source-alignment checks and actual Chrome frame recording; results/screenshots in ignoredtmp.
PRICE recorded2% remains REVIEW,5% previewREADY; overbilling remainsBLOCKED. All persisted snapshots and
active policy unchanged. Authority SHA256 remains7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398.
Protected backend/data/fixtures/client/types unchanged. Hallmark0FAIL/0WARN/1chart waiver/3answered;
Vercel and Taste review documented. No full assistive-technology certification or speed benchmark claimed.
Remaining limits: mobile/native PDF may be blank (source-open fallback); many evidence references still
lengthen mobile cases; original backend explanation prose deliberately unchanged. Review only; no6B.


## Last handoff — Phase 6B.1, 2026-11-19

Base b8e5ced6e7dcb3774364cfef44f1a0be0f06a5d0; branch codex/phase-06b1-human-resolution;
checkpoint phase-06b1-human-resolution. ExactSHA/remote verification accompany final publication.
New pure domain human_resolution.py rederives authoritative context,validates missing PO/approved vendor/
same-vendor candidate/rationale,and substitutes only the PO identity rule. Normal evaluator and all rules
unchanged. No extracted-PO rewrite,policy weakening or evidence promotion. App also requires completed
source and intersection of original candidate IDs/current canonical candidates. Recorded source policy,
current procurement/billing snapshots. API-local response models; shared v1 contracts unchanged.
ReviewService stores action+fullDecision+Policy atomically with source/authoritySHA256,time,DEMO label and
provenance. Migration002 adds new table/version marker/triggers only;first-confirmation-wins+UUID replay;
no edits/deletes/replacement inserts. Original JSON/stages/authority/policy never updated by confirmation.
One-query queue projection labels reviewed assessment separately. Dashboard/filter counts remain recorded;
policy preview still evaluates original automated context (explicit UI/docs disclosure).
328backend PASS58.00s/one existing warning;58frontend PASS;typecheck/build/manifests/hygiene8PDF/pip/npm0 PASS.
Actual browser2 regression uploads use TEST_ONLY provider+realPDFgrounding/API/DB. MISSING_PO_VALID run
099a7620a724409bbe03cbc58b63cd6c/action54411285e8874a2d9e4f4b5aeb22564f:REVIEW→READY withPO1042.
AMBIGUOUS_PO runf81ab36476594ee8b12d77d595f88330/action814571fb44904c019e6af52b0eebce12:REVIEW→REVIEW,
missing qty/price/item mapping retained. No invented source facts. Current policy stays2%; all ceilings retained.
Migration verified twice on actual populated old-runtime copy;old7tables' rows unchanged. Restart hashes for
bothrun/action/PDF sets match;runtime verifier confirms source fingerprints/policy and current authoritySHA
f6e95512f3e71d59bf512c1afc861e69587c3bbf40a9400c0f6c04739d02bf31 (canonical typed-master basis).
0newGemini calls;prior6A generation guard still1. Two fake extraction calls only; reviewed UI labels TEST_ONLY.
App8007/runtime/phase6b1-demo is copied demo data;older8006 untouched. Screens/results tmp/phase6b1-qa,
phase6b1-core-qa,phase6b1-policy-qa; migration/restart/invariant JSON ignored. Core15+7/policy12+3 andreview
1440/1024/390 modal/keyboard/focus/overflow PASS. Native modal can visit browser chrome at Tab boundary;
background app controls remain inert,then focus returns. Controlled pre-confirmation screenshots labelled
TEST_ONLY and never saved. No extra actions on rerun.
DEMO reviewer identity is not authenticated. Required release safeguard before public write exposure recorded
in ADR-020/HUMAN_PO_RESOLUTION. No maker-checker/auth/payment/ERP/hosting/correction/undo/additional scenarios.
Original6PDF/frozen manifests unchanged;one separate new regression scenario and reusedAMBIGPDF. Review only.

## Phase 6B.2A partial review

REPRODUCTION INCOMPLETE — INVESTIGATION REQUIRED. Static review of F1–F3 and safe target criteria are recorded. Three benign offline API controls passed. No bypass probes were run and all three runtime findings remain inconclusive. Baseline 328 backend and 58 frontend tests passed. Zero Gemini requests. Production and frozen business oracles unchanged. See docs/ADVERSARIAL_REPRODUCTION_REPORT.md and docs/ADVERSARIAL_EVALUATION_PLAN.md.

## Phase 6B.2B defensive document hardening

Branch `codex/phase-06b2b-document-hardening` from `f7f669821464183bcad6d8802177d2e170187285`. Supported native headers are compared across the document. Mixed raster uncertainty uses a sanitized technical gate when bank details are unresolved. Native pages with extractable text and a uniform render fail before inference. Existing benign controls pass. Exact historical audit scenarios remain inconclusive. See `docs/PHASE_06B2B_REPORT.md` for test evidence and measured latency. Zero Gemini requests.

## Phase 6B.2B.1 review handoff

Usable mixed documents with unresolved raster now complete with document-content Review, or retain an independent Block. The optional adapter-owned marker persists in JSON and old records keep the historical omission. No schema migration. Bank evidence and document uncertainty remain distinct. Policy preview and PO reassessment retain the marker. The normal logo can still require review. See ADR-022 and PHASE_06B2B1_REPORT.md for evidence, limits and the checkpoint. Zero live Gemini calls.

Verification: 354 backend and 58 frontend tests passed, build and dependency checks passed, real Chrome mixed Review verified and seven historical runs and two actions preserved after restart.
