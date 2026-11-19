# Phase 5 — Connected finance operations UI

**Gate: PASS. Architectural review pending. STOP before Phase 6.**
Date: 2026-11-19 IST. Base: phase-04-vertical-slice / 13fe35d792c2fb47a84604e21966ad4a2bd2048b.
Branch: codex/phase-05-operations-ui. Checkpoint: phase-05-operations-ui, created only after required checks.
This report is prepared before its own commit; resolve the annotated checkpoint for its exact SHA. Final
commit, remote branch/tag verification and clean-tree result are supplied in the publication chat handoff.
No previous tag/default-branch change, paid/public deployment, subagent or later-phase work.

## A. Product views

- / — Operations overview: actual persisted counts, outcome distribution, known flagged net by currency,
  recent activity and one-PDF upload. Not a marketing page or extraction playground.
- /runs — Invoice Operations: bounded history/review queue with shareable filters/search and real row links.
- /runs/:runId — source-and-decision workbench: business identity/status/amount, source PDF, primary exception,
  relevant financial values, owner/next action, all findings, PO context, evidence/history and safe diagnostics.

Foundation status, phase badges, unavailable processing and future-tense shell copy are retired. The forest
identity, product name and no-payment/posting boundary remain. React Router + TanStack Query replace shell
local-state routing and scattered requests. Explicit display types and a single API client own API boundaries.
The frontend never performs financial evaluation, selects a PO, changes policy or verifies model evidence.

## B. Dashboard metrics

| Metric | Exact definition |
|---|---|
| Total invoices | Persisted invoice submissions/analysis runs, including repeated analyses; not unique invoice business keys |
| Ready to process | Completed READY_FOR_AP runs |
| Needs review | Completed REVIEW_REQUIRED runs |
| Blocked | Completed BLOCKED runs |
| In progress | QUEUED + RUNNING runs |
| Processing failed / interrupted | Separate technical terminal counts |
| Decision distribution | Actual ready/review/blocked counts; widths from those counts and accessible numeric labels |
| Invoice value requiring attention | Known extracted invoice NET of completed REVIEW_REQUIRED/BLOCKED runs, grouped by currency |

The approved API-local flagged_invoice_net_by_currency projection uses exact Decimal addition, preserving
large/subminor values. Missing net/currency records are excluded and disclosed via missing count. Repeated
analyses count separately; the UI explicitly says this is not unique payable exposure. No savings/loss/ROI,
accuracy, hours saved, cost, fake counters, chart library or AP-cycle-time claim. Average time was not added.

After the genuine UI smoke: 4 total/completed, 1 ready, 1 review, 2 blocked, 0 in-progress/failed/interrupted;
known flagged net INR130000. Before smoke: 3 total/completed, 1 of each outcome; INR100000 flagged net.
The extra 30000 is a repeated analysis, not additional authoritative billing or money saved.

## C. Queue

Columns: invoice + supplier, gross invoice total/currency, business/execution status, primary issue/outcome,
owner, exact/relative updated time and open action. Header/footer make gross-vs-net basis clear.
Filters: All, Ready, Needs review, Blocked, Processing, Failed, Interrupted. Search invoice number/supplier.
URL-backed status/q state; current bounded list is at most 100 recent runs, explicitly disclosed.
Pointer rows and actual keyboard/modifier-capable links open the workspace. Mobile rows retain every data
cell in a stacked grid, without horizontal page clipping. Unknown reason codes use generic readable fallback.

## D. Decision workspace

READY: positive status, actual PASS findings, genuinely verified reference count when supported, and the
required supported-controls/no-payment-posting disclaimer. Unreported individual checks are not invented.
BLOCKED: primary backend finding and exact provided values lead, followed immediately by resolution owner
and recommended next action. All independent blockers/review/PASS/information findings remain available.
REVIEW: same owner/action structure. SCAN_CONFLICT keeps source verification as backend primary and displays
the independent arithmetic finding in the same prominent brief: 82600 expected / 86200 printed / 3600 difference.
PROCESSING_FAILED: technical explanation from sanitized code; decision=null; explicitly not financial rejection.
INTERRUPTED: no AP decision, no automatic restart; retry is an explicit upload-again link.

PO candidates are returned snapshots, including authorized net, status, vendor record and identification
provenance. Identity is explicitly separate from eligibility. Multiple candidates remain informational
alternatives with Human confirmation required; no selection, confirmation, approval or reevaluation action.
All finding codes render generically using supplied content, including future unknown codes.

## E. Evidence

- NATIVE_VERIFIED -> Source verified, page and Verified source text quote.
- SOURCE_LOCATED_UNVERIFIED -> Source needs review, clearly labelled extraction reference, never verified quote.
- MISSING -> Source not confirmed. Unknown normalized values remain an em dash.
- Image/mixed-source facts explicitly say they have not been independently text-verified.
- Unverified raw model claims can be shown as claims while the document-stated value remains unknown.

No source evidence promotion, confidence score, highlight, OCR accuracy, fabricated bounds or filled financial
facts. Scan optional line.net remains None. PDF uses the real run-scoped endpoint with a native iframe and
Open source document/new-tab fallback. Native mobile PDF painting varies; links are always retained. No PDF
base64/paths or raw provider data enter diagnostics. Technical unknowns display an em dash; real zero stays zero.

## F. Upload and real workflow

Select or drop exactly one PDF; show actual filename/type/size, with B/KiB/MiB formatting and 8MiB guidance.
Backend validation remains authoritative. Stale selection clears after invalid replacement; no auto-submission
or automatic upload retry. Busy submit is disabled and announces uploading without fake percentages.
202 navigates immediately to the run; poll actual detail every 1000ms only for QUEUED/RUNNING. Terminal states
stop polling and invalidate queue/dashboard. Shared query keys prevent overlapping duplicate view requests.
Real stage rows control the timeline. Only a returned RUNNING stage animates; no artificial stage timing.
Polite async announcements, native details disclosures and explicit retry links preserve workflow accessibility.

## G. Design and visual QA

Design hierarchy followed: product invariants > Hallmark > Vercel interaction standard > Taste critique.
Before implementation: old UI inspected at 1440px, actual code/contracts read, short design note committed.
Hallmark v2.0.0 installed/read from https://github.com/Nutlope/hallmark/tree/main/skills/hallmark.
Vercel current command.md: https://github.com/vercel-labs/web-interface-guidelines/blob/main/command.md.
Taste 2.5.1 installed/read after implementation from https://github.com/Leonxlnx/taste-skill/tree/main/skills/taste-skill.
Skill files remain locally available under ignored tmp/phase05-skills for follow-up turns; no global installation.

Chosen system: warm neutral canvas, white surfaces, forest/charcoal horizontal navigation, slate text, restrained
semantic colors, compact operational tables, system sans hierarchy, tabular figures, 4px rhythm and small radii.
One token system owns fonts/palette/spacing/radii/shadows/motion. No marketing hero, ornamental images or card maze.
Hallmark app scope explicitly excludes marketing hero/fold/word-budget/photo rules. Its brand redesign scaffold
was adapted to the existing app. The signature is the source-and-decision workbench, not a generic KPI grid.

Audit sequence: actual app -> Hallmark sweep -> Vercel review -> Taste critique -> relevant fixes -> frontend
tests/typecheck/build -> viewport/keyboard/reduced-motion verification. All review was in-thread, no agents.
Baseline Hallmark: 69 Floor findings / 39 Reflex / 4 warnings. First implemented sweep: 4 Floor findings, fixed
768px header overflow, input-edge contrast and disabled fill/ink/cursor channels. Prettier made a heading-count
accent detectable; count was moved beside the semantic heading instead of inside it. Final confirming five-view sweep: **0 FAIL / 0 REFLEX / 0 WARN / 3 ANSWERED**, exit0, 25 rendered captures. F1 preserves the supplied disclaimer; F25 measures clipped semantic
headers rather than mobile data cells. Actual geometry proved all visible cells stay within 390px.

Deliberately rejected Taste marketing requirements: full-screen sections, mandatory hero entrances, shader
backgrounds, creative moments, photography, zooms and looping cards. They conflict with the product's repeated
finance work, Hallmark app scope and the user's restrained-motion requirements. No Taste marketing gate is
claimed passed. Applied critique: stronger hierarchy, shared edges, less box nesting, clearer evidence affordance,
readable PDF frame and independent scan discrepancy/source-uncertainty explanations.

Browser QA used actual local Chrome, first with Vite then the compiled React build served directly by FastAPI.
15 real-data captures: overview, queue, READY, REVIEW and BLOCKED at 1440/1024/390. Seven deterministic API
states: queued/running/failure/interruption/long text/empty/error, clearly test-only and never persisted.
Verified no page overflow, every mobile data cell retained, decision-before-source mobile order, visible skip
focus, keyboard search/filter/row links/disclosures, source 200, reduced-motion spinner disabled, no uncaught JS.

Representative local screenshots (ignored, not committed as giant assets):
- tmp/phase05-qa/overview-1440.png
- tmp/phase05-qa/blocked-1024.png
- tmp/phase05-qa/queue-390.png
- tmp/phase05-qa/review-390.png
- tmp/phase05-qa/ready-1440.png
- tmp/phase05-qa/deterministic-failed-390.png
- tmp/phase05-qa/deterministic-empty-390.png
- tmp/phase05-qa/live-processing-1440.png and live-blocked-1440.png

No claim of a formal accessibility certification or measured human five-second study. The actual first desktop
screen exposes the requested counts together, and the blocked brief exposes amount/owner/action without logs.

## H. Exact automated checks

Repository root:

```powershell
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest-phase05-acceptance --tb=short
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
.venv/Scripts/python scripts/verify_manifests.py
.venv/Scripts/python scripts/verify_git_hygiene.py
.venv/Scripts/python -m pip check
npm --prefix frontend ls --depth=0
npm --prefix frontend audit --audit-level=moderate
```

Browser checks:

```powershell
$env:AP_COMPASS_UI_URL='http://127.0.0.1:8005'
node frontend/scripts/qa.mjs
# Performed once against Vite 5175 after automated tests; do not repeat for screenshots:
$env:AP_COMPASS_UI_URL='http://127.0.0.1:5175'
node frontend/scripts/smoke.mjs --live-upload
# Resumed only the same completed run to finish native-PDF popup assertions:
node frontend/scripts/smoke.mjs --resume 3af82d60d6624971b7aa48de920407d5
```

| Check | Actual result |
|---|---|
| Backend | **280 passed**, zero failures, one existing Starlette/AnyIO warning, 49.42s |
| Backend scope | All original 268 tests unchanged + 3 dashboard projection + 9 SPA routing tests |
| Frontend | **32 passed**; includes all requested display/workflow cases, actual polling stop, exact precision/identifier/scan/drag/drop/copy-error checks |
| TypeScript | tsc -b PASS |
| Production build | Vite 7.3.8 PASS, 1747 modules; 307.28kB JS / 33.52kB CSS uncompressed (97.02/6.99kB gzip) |
| Manifests | PASS: original 6 vendors / 7 POs / 3 billed records / 10 scenarios |
| Hygiene / dependencies | PASS: 11 exclusions/PDF bytes intact; pip check clean; npm tree valid, zero audit vulnerabilities |
| Actual browser | 15 real viewport captures + 7 deterministic states, keyboard/reduced-motion, zero uncaught application JS |
| Protected diff | Empty for financial/domain/document/AI/contracts/DB/orchestration, manifests, PDFs, original tests, Docker |

Development failures retained: initial frontend 25/27 (query mock received TanStack context and selectors matched
repeated finding values); wrapper/scoped selectors fixed both. Test-query exact options caused TypeScript errors
and were corrected. One SPA test failed on Windows backslashes; route normalization fixed it (9/9 focused then
280/280 full). Earlier sandbox localhost access, skill-root path and working-directory command attempts failed;
using verified paths/local execution resolved them. Vite's initial high audit finding was patched 7.2.2 -> 7.3.8,
without force upgrades, and audit is now zero. A PDF-plugin network-idle screenshot wait timed out; final QA
waits for specific UI readiness instead. No unresolved test/application failure remains.

## I. Genuine UI smoke

Actual OVERBILLED_PARTIAL.pdf selected in Chrome -> POST 202 QUEUED -> workspace polling saw three RUNNING /
Reading invoice observations -> COMPLETED/BLOCKED. Run ID 3af82d60d6624971b7aa48de920407d5.
**Exactly one new Gemini generation**: gemini-3.5-flash-lite, native_text; 542 input / 920 output tokens.
Extraction 3312ms; matching 2ms; evaluation 2ms; total_processing 3389ms. All returned evidence states native verified.
Extracted Aster Systems / OVERBILLED_PARTIAL-2026 / PO-3015 / INR net30000 tax5400 total35400.
Required reasons PO_BALANCE_EXCEEDED and PO_QUANTITY_EXCEEDED retained, plus PO_LINE_BALANCE_EXCEEDED,
PO_MATCH_CONFIRMED and BANK_DETAILS_NOT_PROVIDED. Primary values: authorized200000 / billed175000 /
remaining25000 / invoice30000 / excess5000. Owner Procurement; exact backend correction/amendment action displayed.
No stronger model or metadata dependency; existing runtime adapter and provider configuration remain unchanged.

The source PDF opened in a real new tab and returned application/pdf with actual PDF signature. Initial harness
popup matching accidentally included an embedded iframe and stalled after successful extraction. It was corrected
to page+opener matching, and the SAME persisted run resumed without upload/inference. Queue contained the new
run; dashboard total/blocked increased by one; reload returned an identical snapshot. This was not a second smoke call.
Details and actual stage timestamps: PHASE_05_LIVE_RESULTS.json. Visual/type/behavior tests use deterministic
fakes only where explicitly labelled; they are not presented as provider evidence.

Authoritative-row SHA256 before AND after this UI run:
7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398.
All previous live runs/documents survived server restart; browser viewing/history did not invoke Gemini again.

## J. Architecture changes / files

No shared Pydantic shape, finance rule, document grounding, AI adapter, procurement seed, fixture outcome,
DB schema or orchestration semantic changed. Two small backend view-integration changes only:
1. Approved API-local known-net-by-currency projection + missing count, with exact arithmetic tests.
2. Identified/reported static deep-link blocker fixed by narrow React entry fallback; API/assets/unknown paths
   retain 404, Windows behavior covered. This is serving behavior, not orchestration/business logic.

Created frontend typed client/types/query hooks, shell, overview/queue/workspace, shared components, centralized
formatting/tokens/base, 32 tests and explicit QA/live smoke scripts. Updated Vite config/dependencies/lock,
index/meta/noscript, main/styles; added formatter/test config. Created backend spa.py and 12 tests; modified
only dashboard projection and static mount wiring. .gitignore excludes Hallmark artifacts. Updated README,
status/memory/decision log; OPERATIONS_UI, design note/QA, this report and sanitized JSON evidence added.

## K. Git

Branch codex/phase-05-operations-ui from exact reviewed Phase 4 tag. Commit message:
feat: build connected AP operations workspace. Annotated checkpoint phase-05-operations-ui is created/pushed
only after the gate passes. Exact SHA/remote verification/clean-tree result are in final publication handoff.
Existing remote https://github.com/Arnavvats287/ap-compass.git retained; no force/default-branch/prior-tag changes.

## L. Known limitations

Native iframe PDF rendering varies, especially mobile/headless; real source-open links are the fallback.
List/filter scope is 100 recent runs; no full-history server filtering/pagination. Counts/value include repeated
analyses, explicitly not unique invoices/liability. System font rendering varies by OS; no remote-font dependency.
Single-process backend and restart-interruption limits remain. No Confirm PO, approval, reevaluation, tolerance
editor, supplier/email/ERP/payment action, auth suite, batch, analytics/charts, model selector, new edge-case
fixtures, Docker/public/paid hosting or Phase 6. No general extraction accuracy or accessibility-certification claim.

## M. Gate / segment checklist

**PASS.** A nontechnical user can submit a PDF, watch persisted backend stages, read the business decision,
amounts, owner/action and source evidence, then return to a real-data queue/overview. One actual UI upload,
three existing live outcomes, all automated suites and required viewport/interaction QA support this statement.

- [x] Original backend regressions and focused frontend cases pass.
- [x] Actual primary inference, true stages, persisted source/result/reload and unchanged authority verified.
- [x] Design note first, coherent tokens, Hallmark/Vercel/Taste sequence and rejected conflicts documented.
- [x] No fabricated finance/evidence/metrics or unapproved contract/engine/schema change.
- [x] Status/memory updated from evidence; passing checkpoint only after checks.

STOP for architectural review. Phase 6 is not authorized.


## Final design command evidence

```powershell
$env:HALLMARK_PUPPETEER = Join-Path (Get-Location) 'frontend'
node tmp/phase05-skills/hallmark/scripts/sloplint.mjs frontend/src/styles.css frontend/src/tokens.css frontend/src/base.css frontend/src/App.tsx frontend/src/Overview.tsx frontend/src/Queue.tsx frontend/src/Workspace.tsx frontend/src/components.tsx --scope app --genre modern-minimal --render --url http://127.0.0.1:8005 --url http://127.0.0.1:8005/runs --url http://127.0.0.1:8005/runs/3af82d60d6624971b7aa48de920407d5 --url http://127.0.0.1:8005/runs/e0eb6a058c574f66aa48cb474e28a33f --url http://127.0.0.1:8005/runs/7b3a699bea514c7f9eed52b34d90d639
```

Actual: exit0, 0 FAIL, 0 REFLEX, 0 WARN, 3 ANSWERED across 8 source files / 5 real-data routes;
25 captured pages. In frontend directory, `npm exec -- prettier --check src scripts vite.config.ts
vitest.config.ts index.html .prettierrc.json` passed. The last frontend suite after semantic heading cleanup
is 32/32, TypeScript/build exit0. No further application code edits after those checks.
