# AP Compass — Project Status / Gate Register

**Updated:** 2026-11-19 IST.
**Current gate:** Phase 5 connected operations UI PASS; architectural review pending. STOP before Phase 6.
**Base:** phase-04-vertical-slice / 13fe35d792c2fb47a84604e21966ad4a2bd2048b.
**Branch:** codex/phase-05-operations-ui. **Checkpoint:** phase-05-operations-ui, published only after checks.
Resolve the annotated tag for exact SHA; final commit/push/clean-tree evidence is in the publication chat.
No prior-tag/default-branch alteration. Deadline remains Saturday 2026-11-21 IST.

| Phase | State | Evidence |
|---|---|---|
| 01 Foundation | ACCEPTED | Checkpoint preserved |
| 02 Finance | ACCEPTED | Original financial code/tests unchanged |
| 03/3.1 Extraction | ACCEPTED | Original document/AI code/tests unchanged; primary only |
| 04 API/orchestration | ACCEPTED | User review passed; original workflow/tests unchanged |
| 05 Operations UI | PASS, review pending | Connected real-data UI, 280 backend + 32 frontend tests, browser/live smoke |
| 06 Scenarios | LOCKED | No new fixtures/scenarios authorized |
| 07 Release | LOCKED | No public/paid/Docker deployment |

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
