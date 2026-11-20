# AP Compass — Project Status / Gate Register

**Updated:** 2026-11-20 IST.
**Current gate:** Phase G.3 launch and intake policy verified for local review.
**Base:** e5e8a183ad7063b815310b7f2e2234048ec6564d.
**Branch:** codex/phase-g3-launch-intake. **Checkpoint:** phase-g3-launch-intake.
See the [Phase G.3 report](docs/PHASE_G3_LAUNCH_EXPERIENCE_REPORT.md) for the Chrome review, recorded intake policy comparison and regression evidence.
See the [Phase G.2 report](docs/PHASE_G2_OPERATIONS_REDESIGN_REPORT.md) for captures, the eight-file rehearsal and regression results.
See the [Phase G.1 report](docs/PHASE_G1_WORKSPACE_REDESIGN_REPORT.md) for before and after captures, Chrome checks and frontend regression results.
See the [final automation quality report](docs/FINAL_AUTOMATION_QUALITY_REPORT.md) for the controlled comparison. Ready increased from 2/12 to 6/12 across the evaluated Ready targets, with 0/14 false Ready outcomes on either side.
No prior-tag/default-branch alteration. Deadline remains Saturday 2026-11-21 IST.

| Phase | State | Evidence |
|---|---|---|
| 01 Foundation | ACCEPTED | Checkpoint preserved |
| 02 Finance | ACCEPTED | Original financial code/tests unchanged |
| 03/3.1 Extraction | ACCEPTED | Original document/AI code/tests unchanged; primary only |
| 04 API/orchestration | ACCEPTED | User review passed; original workflow/tests unchanged |
| 05 Operations UI | ACCEPTED | User confirmed functional gate passed; existing checkpoint preserved |
| 05.1 Visual refinement | ACCEPTED | Two rendered iterations, 280 backend + 32 frontend tests, 15 real-data views + 7 deterministic states; zero model calls |
| 06A Policy and trace | Functionally accepted; refinement accepted in6A.1 | 299 backend +47 frontend tests; one live PRICE extraction, zero-AI previews; two creative browser iterations |
| 06A.1 Signature UI | ACCEPTED | b8e5ced6e7dcb3774364cfef44f1a0be0f06a5d0 checkpoint preserved |
| 06B.1 Human PO resolution | Local PASS; review pending |328backend/58frontend tests; append-only action; source/ledger unchanged;0Gemini |
| 06B.2B.1 Mixed-document review | ACCEPTED | Verified base for golden dataset preparation |
| 06B.2C.1 Golden dataset preparation | ACCEPTED | Frozen as the base for the independent benchmark |
| 06B.2C.2 Frozen baseline and independent benchmark | Complete for review | Development B 9/10 exact decisions, independent B 3/6. Live used four generations across two completed submissions. Both had exact supported field values and unnecessary source Review. See the benchmark report for coverage and exclusions. |
| 06B.2C.3 Source grounding and scope remediation | Verified base | 422 backend, including 26 development layout tests, and 58 frontend passed. Scope owner/action assertions pass without XFAIL. |
| 06B.2C.4 Post-fix validation | Complete for release review | Offline evidence 123/135 development, 54/100 held-out. Decisions 9/10 and 3/6. Eight live generations yielded one Review and three terminal technical failures. No completed live non-Ready target. |
| 06B.2D.1 Financial evidence integrity | Backend and frontend verification passed | Shared native source-currency invariant. 471 backend and 58 frontend tests passed, including 49 dedicated tests and controlled persisted reload without historical/audit changes. |
| 06B.2D.2 Private demo release hardening | Verified for controlled demonstration | 488 backend and 58 frontend tests passed. Real private Docker and Chrome acceptance, persistent PDF and audit restart checks, and four controlled demo scenarios. Zero Gemini requests. See [release report](docs/RELEASE_HARDENING_REPORT.md). |
| 06B.2E.1 Source generalization and completeness | Verified for independent evaluation | 508 backend and 58 frontend tests passed. Bounded field and full-row quote forms, recognized omitted-line Review, private Docker and restart verified. Frozen evidence matched. No held-out PDF access or Gemini requests. See [source report](docs/PHASE_06B2E1_SOURCE_GENERALIZATION_REPORT.md). |
| 06B.2F.1 Premium dashboard | Locally verified for review | Needs Attention spotlight, recorded outcomes, recent vendor ranking and queue sort. 63 frontend and 17 private-demo tests passed, with scoped Chrome QA. No backend or frozen evaluation changes. See [dashboard report](docs/PHASE_06B2F1_PREMIUM_DASHBOARD_REPORT.md). |
| 06B.2F.2 Batch upload and Excel export | Locally verified for review | Five Chrome uploads completed serially using disposable private storage and controlled extraction. XLSX matched five records and 15 findings. 67 frontend and 77 relevant backend tests passed. Zero Gemini calls. See [batch and Excel report](docs/PHASE_06B2F2_BATCH_EXCEL_REPORT.md). |
| 06B.2F.3 Final demo experience | Locally verified for submission review | Chrome verified four journey endings, real live stages, reduced motion, and gross totals from eight stored runs. Serial batch and Excel repeated successfully. 69 frontend and 4 focused backend tests passed. Zero Gemini calls. See [demo report](docs/PHASE_06B2F3_FINAL_DEMO_REPORT.md). |
| 07 Release | LOCKED | Remote/public hosting and paid deployment await explicit authorization |

## Verified Phase 6A evidence

- Read-only API-local policy preview uses stored invoice/current trusted authority and the unchanged
  build_context/evaluate functions. Decimal0.02/0.05 only; extra controls/float inputs rejected. No shared
  contract/schema/financial/document/provider/authority change. No run/stage/policy/ledger writes by previews.
- **299 backend tests pass** (280 original +19 new),52.18s,one existing warning; **47 frontend tests pass**
  (32 original +15 new),6.55s. Typecheck/build PASS;1751modules,JS316.59kB/CSS61.08kB (gzip99.34/10.87kB).
- Manifest/hygiene/pip PASS; npm audit0 vulnerabilities. Existing PDF/manifests unchanged; generated only
  the frozen PRICE_3PCT native PDF. Hygiene byte check now accurately reports6 fixture PDFs.
- One genuine browser PRICE upload,run d2269cade6cb4dca94e6239e5658d25a:Flash-Lite/native_text,
 8 critical headers match oracle,13 source refs NATIVE_VERIFIED. At2% REVIEW_REQUIRED/PRICE_VARIANCE;
  at5% preview READY_FOR_AP. Original decision unchanged. Input542/output681 tokens; extraction5807ms,
  matching2ms/evaluation2ms/total5852ms. Exactly1 generation overall,0 during creative redesign/previews.
- Overbilling stays BLOCKED at5% in real API/browser; duplicates stay BLOCKED/EXACT_DUPLICATE in API tests.
  Tests forbid extractor/PDF access and all non-SELECT SQL during previews; snapshots/stages/authority/policy
  remain identical. Authority hash still7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398.
- Actual stage-driven trace:compact completed nodes and separate business outcome; actual-only RUNNING
  connector animation; milliseconds/unknown timing preserved. Native details and reduced motion verified.
- User creative override expressly authorized overview/shared visual refinement. Pre-edit critique/spec,
  two actual Chrome iterations:asymmetric attention bento,editorial Georgia/system sans,forest trace/preview,
  mint/citrus,readable white queue. Reference video absent; no inspection claim. No design dependency added.
- Core browser15 real views +7 test states PASS; focused12 recorded/preview states +3 running states across
 1440×1000/1024×900/390×844 PASS. Hallmark rendered0FAIL/0WARN/3ANSWERED; Vercel/Taste reviews recorded.
  One concurrent Chrome PDF navigation timeout resolved by rerunning the unchanged suite alone.
- Current app http://127.0.0.1:8006;5 actual analyses,ready1/review2/blocked2. Preview-ready does not change
  recorded counts. Runtime/smoke guard/screenshots ignored. No stronger model,6B,approval or deployment work.
- Reports:POLICY_PREVIEW.md,PHASE_06A_DESIGN.md,PHASE_06A_REPORT.md,PHASE_06A_LIVE_RESULTS.json; ADR-019.

## Phase 5.1 publication verification

Fresh checkpoint checks:280 backend passed in50.46s (one existing warning),32 frontend passed in6.00s;
typecheck/build/manifests/hygiene/pip PASS. Actual Chrome:15 real-data views +7 deterministic states PASS,
with separate sticky/no-overlap/mobile-order/comparison checks. All persisted snapshots unchanged; zero API
mutations and **0 new Gemini calls**. No application changes in the publication task. Protected backend/data
diff empty against accepted Phase5. Exact commands/classification:docs/PHASE_05_1_REPORT.md sectionJ.

## Verified Phase 5.1 evidence

- Rendered baseline critique before UI edits; two visual iterations using actual persisted READY/REVIEW/BLOCKED runs.
- Attention summary and financial comparison are the only two signature patterns. Existing metric definitions,
  amounts, evidence states, owner/actions, payment disclaimer and decisions retained.
- All **280 backend tests pass**, zero failures, one existing warning, 50.76s. All **32 frontend tests pass**,
  final5.63s; typecheck/build PASS, 1747 modules. Original tests unchanged.
- Final browser QA:15 real-data views at1440×1000/1024×900/390×844,7 test-only states, keyboard/search/filter/
  disclosures/PDF200/reduced-motion/overflow pass. One first-iteration rapid-search timeout was reproduced and
  fixed with immediate input state while retaining URL synchronization; final QA passes.
- Zero Gemini calls or API mutations; all four stored snapshots and summaries deep-equal before/after browsing.
  Authoritative-row hash still7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398.
- Hallmark rendered five-route audit:0FAIL/0WARN/3ANSWERED; final static0FAIL/0WARN/1ANSWERED. Vercel review
  and app-specific Taste critique complete. Marketing hero/photo/shader/loop prescriptions rejected.
- Manifests/hygiene/pip/npm tree pass; no dependency changes. Backend/data/API/query/types/format/test diff empty.
- Screenshots local/ignored:tmp/phase051-before, tmp/phase051-iteration1, tmp/phase051-after. Native PDF frame
  may be blank in mobile headless Chrome; functional open-source fallback retained.
- Full critique, commands, screenshot comparison matrix, audit decisions and limits:docs/PHASE_05_1_REPORT.md.

## Verified Phase 5 evidence

- All **280 backend tests pass**, zero failures, one existing warning, 49.42s: original 268 + 3 display
  projection tests + 9 static-route tests. Original test files and business outcomes unchanged.
- All **32 frontend tests pass**; TypeScript tsc -b and Vite 7.3.8 production build PASS, 1747 modules.
- Manifests/hygiene/pip check PASS; npm dependency tree valid and audit zero vulnerabilities after non-major
  Vite security patch. Runtime/.env/screenshots/local skill installs ignored; no frontend credentials.
- Three routes: overview, Invoice Operations queue and /runs/:id decision workspace. Typed API client,
  TanStack Query active-only 1000ms polling, real persisted stages, terminal invalidation and reload support.
- Exact known-net by currency projection only; unknown amounts excluded/disclosed, repeats count separately.
- Real Chrome QA: 15 actual-data views across 1440/1024/390, 7 explicitly deterministic API states, no page
  overflow, keyboard/skip/filter/disclosures/PDF response, reduced motion and no uncaught application JS.
- Actual one-PDF browser upload OVERBILLED_PARTIAL: run 3af82d60d6624971b7aa48de920407d5,
  RUNNING observed three times, then COMPLETED/BLOCKED. One Flash-Lite call, no stronger request.
- Live facts: Aster / PO-3015 / INR net30000 tax5400 gross35400; remaining25000, excess5000, owner Procurement,
  value+quantity+line commitment controls. Returned evidence native verified. No financial workaround.
- Live measured extraction3312/matching2/evaluation2/total3389ms; 542 input / 920 output tokens.
- Source opened, queue/dashboard refreshed, snapshot identical after reload, no repeat inference. Initial
  PDF popup harness mismatch was corrected by resuming this SAME run, not by another upload.
- Authority before/after hash identical: 7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398.
- Current demo history: 4 submissions, 1 ready / 1 review / 2 blocked; flagged known INR net130000 including
  repeated analysis, not unique payable exposure. Existing Phase 4 runs/documents survive restart.

## Scope and decisions (Phase 5 history)

No shared-contract, financial/document/AI rule, DB schema, orchestration, seed or fixture change. Small backend
changes: approved dashboard read projection and identified/reported static deep-link serving fix (ADR-018).
The design note predates implementation. Hallmark app redesign, Vercel QA, then Taste critique applied;
marketing heroes/shaders/mandatory loops/photography rejected in favor of finance work and reduced motion.
Final audit/screenshot details in PHASE_05_REPORT and DESIGN_QA. Review remains in-thread; no agents.

## Local review and limitations (Phase 5 history)

Compiled UI/backend http://127.0.0.1:8005 in local Chrome; Vite http://127.0.0.1:5175 proxies it. The default
8000 port belongs to an older process and was not overwritten. Existing demo DB/document location documented
in OPERATIONS_UI. Native PDF embeds vary by browser; source-open links remain available. Queue filters cover
100 recent runs. Original single-process/restart limits remain. No approval, confirmation, reevaluation,
policy editor, batch, model selector, payment/ERP/email, auth suite, analytics, new fixtures or deployment.

Current evidence: docs/PHASE_05_REPORT.md, OPERATIONS_UI.md, PHASE_05_DESIGN_NOTE.md, PHASE_05_DESIGN_QA.md,
PHASE_05_UI_QA_RESULTS.json and PHASE_05_LIVE_RESULTS.json. Screenshots stay in ignored tmp/phase05-qa.
All encountered test/harness failures are documented and resolved. No general accuracy/accessibility certification.
Next action: architectural review or an explicit repair prompt. Do not start Phase 6 automatically.


## Phase 6A.1 verified refinement — 2026-11-19

Frontend-only redesign from exact95e6e66 base. Two fresh rendered iterations against persisted data at8006:
real-count attention orbit/ledger, compact aligned case spread, earlier evidence and optional audit disclosure,
full-width execution spine with independent business outcome, full-width hypothetical policy comparison.
299 backend tests passed in52.90s (one existing Starlette deprecation);48 frontend tests passed in5.72s;
typecheck/build passed. Final assets JS319.50kB/gzip100.13; CSS70.59kB/gzip12.23. No dependency changes.
Manifests6vendors/7POs/3billed/10cases; hygiene11exclusions/6PDFs; pip check clean; npm audit0 vulnerabilities.
Core Chrome15 real views +7 controlled states; focused policy12 recorded/preview views +3 labelled TEST_ONLY
active traces; keyboard/focus/no-overflow/reduced-motion checks. Additional source alignment/anchor checks and
actual Chrome interaction recording. Full details and paths in docs/PHASE_06A1_REPORT.md.
Hallmark0FAIL/0WARN,1 real-data-chart waiver,3 existing answered findings; Vercel/Taste app-scope review.
Protected backend/contracts/API/client/finance/extraction/orchestration/data/fixtures unchanged. Authority hash
7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398 unchanged; all five persisted run snapshots
unchanged during browser checks. **0 new Gemini calls**. No6B features, release work or deployment.


## Phase 6B.1 actual evidence — 2026-11-19

User accepted6A.1. New isolated pure evaluate_with_confirmed_po changes only validated PO identity resolution;
ordinary evaluate/matching/rules/shared contracts remain unchanged. New API-local POST po-confirmations and
GET review-history; current candidate intersection,approved vendor,required rationale and UUID key. Original
policy/current authority. Separate typed action/reassessment; original run and stage rows never overwritten.
Migration002 adds review_action/schema_migration/append-only triggers. One source run/first-confirmation-wins,
BEGIN IMMEDIATE,atomic insert; identical-key replay safe. Queue uses one joined query and labels reviewed
assessment separately; filters/dashboard remain recorded automated decisions. Demo reviewer is unauthenticated.
Release requires a basic access safeguard before exposing writes publicly. No approval/payment/auth/deployment.

328backend tests PASS58.00s (one existing Starlette deprecation);58frontend tests PASS; typecheck/build,
manifest6vendors/7POs/3billed/10frozen cases,hygiene11exclusions/8PDFs,pip check,npm audit0 PASS.
Actual Chrome upload/confirm saved two actions with TEST_ONLY extraction and real native grounding/API/DB:
MISSING_PO_VALID originalREVIEW→confirmedPO1042READY; AMBIGUOUS_PO originalREVIEW→confirmedPO1042REVIEW,
CRITICAL_FIELD_MISSING/LINE_MAPPING_UNRESOLVED retained. Both survive actual server restart with identical
run/review/PDF hashes. Old6vendors/7POs/7lines/3billed/5runs/25stages/1policy rows unchanged on migrated copy.
Core browser15views+7controlled states,policy12recorded/preview+3controlled traces,review workflows/modal at
1440/1024/390 pass keyboard/focus/overflow/no-fake-approval checks. No further actions on verification reruns.
0newGemini calls; two fake-provider extraction calls for actual regression uploads,clearly labelled. New
separate human-resolution manifest/PDF only; frozen seed/fixture manifests and original6PDF bytes unchanged.
Reports:HUMAN_PO_RESOLUTION.md,PHASE_06B1_REPORT.md; ADR-020. Local app8007 uses runtime/phase6b1-demo copy;
older8006 untouched. No corrections/undo/multiple confirmations or new creative showcase cases. Stop for review.

## Phase 6B.2A partial review

REPRODUCTION INCOMPLETE — INVESTIGATION REQUIRED. Static review of F1–F3 and safe target criteria are recorded. Three benign offline API controls passed. No bypass probes were run and all three runtime findings remain inconclusive. Baseline 328 backend and 58 frontend tests passed. Zero Gemini requests. Production and frozen business oracles unchanged. See docs/ADVERSARIAL_REPRODUCTION_REPORT.md and docs/ADVERSARIAL_EVALUATION_PLAN.md.

## Phase 6B.2B defensive document hardening

Branch `codex/phase-06b2b-document-hardening` from `f7f669821464183bcad6d8802177d2e170187285`. Supported native headers are compared across the document. Mixed raster uncertainty uses a sanitized technical gate when bank details are unresolved. Native pages with extractable text and a uniform render fail before inference. Existing benign controls pass. Exact historical audit scenarios remain inconclusive. See `docs/PHASE_06B2B_REPORT.md` for test evidence and measured latency. Zero Gemini requests.

## Phase 6B.2B.1 review handoff

Usable mixed documents with unresolved raster now complete with document-content Review, or retain an independent Block. The optional adapter-owned marker persists in JSON and old records keep the historical omission. No schema migration. Bank evidence and document uncertainty remain distinct. Policy preview and PO reassessment retain the marker. The normal logo can still require review. See ADR-022 and PHASE_06B2B1_REPORT.md for evidence, limits and the checkpoint. Zero live Gemini calls.

Verification: 354 backend and 58 frontend tests passed, build and dependency checks passed, real Chrome mixed Review verified and seven historical runs and two actions preserved after restart.
