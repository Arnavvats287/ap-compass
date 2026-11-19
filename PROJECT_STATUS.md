# AP Compass — Project Status / Gate Register

**Updated:** 2026-11-19 IST.
**Current gate:** Phase 5 accepted by user; Phase 5.1 visual refinement PASS, review pending. STOP before Phase 6.
**Base:** phase-05-operations-ui / 8816cff9ee721bfdf2ce35ac5faf4601eb3f18df.
**Branch:** codex/phase-05-1-visual-refinement. Accepted `phase-05-operations-ui` checkpoint preserved.
Checkpoint-only publication authorized after fresh checks. Checkpoint name: `phase-05-1-visual-refinement`.
Exact SHA and independently verified remote publication/clean-tree evidence are in the publication handoff.
No prior-tag/default-branch alteration. Deadline remains Saturday 2026-11-21 IST.

| Phase | State | Evidence |
|---|---|---|
| 01 Foundation | ACCEPTED | Checkpoint preserved |
| 02 Finance | ACCEPTED | Original financial code/tests unchanged |
| 03/3.1 Extraction | ACCEPTED | Original document/AI code/tests unchanged; primary only |
| 04 API/orchestration | ACCEPTED | User review passed; original workflow/tests unchanged |
| 05 Operations UI | ACCEPTED | User confirmed functional gate passed; existing checkpoint preserved |
| 05.1 Visual refinement | PASS, review pending | Two rendered iterations, 280 backend + 32 frontend tests, 15 real-data views + 7 deterministic states; zero model calls |
| 06 Scenarios | LOCKED | No new fixtures/scenarios authorized |
| 07 Release | LOCKED | No public/paid/Docker deployment |

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

## Scope and decisions

No shared-contract, financial/document/AI rule, DB schema, orchestration, seed or fixture change. Small backend
changes: approved dashboard read projection and identified/reported static deep-link serving fix (ADR-018).
The design note predates implementation. Hallmark app redesign, Vercel QA, then Taste critique applied;
marketing heroes/shaders/mandatory loops/photography rejected in favor of finance work and reduced motion.
Final audit/screenshot details in PHASE_05_REPORT and DESIGN_QA. Review remains in-thread; no agents.

## Local review and limitations

Compiled UI/backend http://127.0.0.1:8005 in local Chrome; Vite http://127.0.0.1:5175 proxies it. The default
8000 port belongs to an older process and was not overwritten. Existing demo DB/document location documented
in OPERATIONS_UI. Native PDF embeds vary by browser; source-open links remain available. Queue filters cover
100 recent runs. Original single-process/restart limits remain. No approval, confirmation, reevaluation,
policy editor, batch, model selector, payment/ERP/email, auth suite, analytics, new fixtures or deployment.

Current evidence: docs/PHASE_05_REPORT.md, OPERATIONS_UI.md, PHASE_05_DESIGN_NOTE.md, PHASE_05_DESIGN_QA.md,
PHASE_05_UI_QA_RESULTS.json and PHASE_05_LIVE_RESULTS.json. Screenshots stay in ignored tmp/phase05-qa.
All encountered test/harness failures are documented and resolved. No general accuracy/accessibility certification.
Next action: architectural review or an explicit repair prompt. Do not start Phase 6 automatically.
