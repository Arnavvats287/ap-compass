# Phase 6A — Policy impact and dynamic decision trace

2026-11-19 IST. **PHASE 6A PASS — stop for architectural/visual review.**
Base:phase-05-1-visual-refinement /4e9665daac7dda661f19217ab9ba8630c640b839.
Branch:codex/phase-06a-policy-decision-trace. Checkpoint:phase-06a-policy-decision-trace.
Exact final commit SHA and independently verified remote branch/tag publication accompany the final handoff.
No previous tag or repository default-branch change is authorized.

## A. Policy architecture

POST policy-preview is API-local validation plus a small read-only coordinator. It loads the completed run,
uses stored ExtractedInvoiceV1, copies its immutable PolicyV1 with only tolerance changed, derives a stable
preview version from policy content, loads current trusted vendor/PO/history snapshots via the existing
repository, and calls the unchanged build_context(...) then evaluate(context,policy). Both2%/5% choices use
this identical code path. No new financial evaluator, JavaScript financial rule or policy registry.

All other recorded policy fields are retained. Previews are not saved as PolicySnapshot or a run revision.
changed compares the business decision excluding policy_version, not just the top-level outcome or policy ID.
Current trusted records can change after a historical run; the UI says Current trusted records, rather than
promising unchanged historical authority. ADR-019 and POLICY_PREVIEW.md document this deliberate boundary.

## B. Hard-control proof

PO commitment, quantity/line authorization and billed duplicates remain independent mandatory engine rules.
Changing the unit-price tolerance cannot bypass them. The API accepts no override for explicit PO, amount
allowance, commitment overrun, evidence or identity. Extra fields are rejected. Protected controls are locked
information, never fake toggles. The financial domain source and original domain tests are unchanged.

## C. API

`POST /api/runs/{run_id}/policy-preview`, body `{"price_tolerance_pct":"0.05"}` or `"0.02"`.
Existing Amount rejects binary floats/bools; finite Decimal validation and a two-value allowlist reject
unsupported values. Equivalent Decimal spellings canonicalize to0.02/0.05. API-local response contains full
original_policy, preview_policy, original_decision, preview_decision, changed. No shared contract changes.

- **200**: completed business analysis with stored invoice, decision and policy.
- **404**: unknown run.
- **409**: queued/running/failed/interrupted or missing completed analysis.
- **422**: unsupported/invalid tolerance, float/bool/non-finite/container input or extra control fields.
- **503**: sanitized failure evaluating invalid trusted inputs; no fake business decision is persisted.

Selecting either tolerance makes an explicit request. No request on mount/disclosure; both choices are
initially unselected, so2% can be requested without selecting5% first. Pending disables controls, preserves
layout and waits for the actual response. Error/retry is explicit. No global policy editing or apply button.

## D. No-AI / non-mutation proof

The preview coordinator imports no document or provider code. Tests forbid extraction, PDF-store reads and
all SQL statements other than SELECT during previews. Run JSON, RunStage rows, policy rows, authority rows
and active policy remain equal before/after. Repeated identical previews are deterministic. A separate test
changes a trusted PO status in a temporary database to prove current authority is reloaded and remains locked.
These are test-only data changes, never changes to manifests or the live ledger.

Real browser QA makes6 policy-preview requests per pass, then compares every stored snapshot/summary and
active policy. The live smoke guard persistently records exactly1 total Flash-Lite generation across the
entire phase. **Every preview uses0 additional Gemini calls.** No stronger-model or metadata calls occurred.
Only the explicitly authorized new PRICE extraction creates a new actual run.

Authoritative-row fingerprint still matches the accepted runtime:
`7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398`.
All-five-run fingerprint during final core QA, equal before/after browsing:
`83b19fa7ce0fa3dadf5de1d0a244e6552c13453e5cf8bfb0b779838fca993881`.

## E. Decision trace

| Persisted stage | Working / completed language |
|---|---|
| received | Invoice received |
| extracting_invoice | Reading invoice / Invoice read |
| matching_records | Checking procurement / Procurement checked |
| evaluating_controls | Running AP controls / AP controls evaluated |
| finalizing | Preparing decision / Decision prepared |

Checking procurement means the operation executed, not that all identities resolved. Unresolved identity,
evidence or finance findings remain independent. Nodes render only returned stages/states; no fabricated
future stages. PASSED/QUEUED/RUNNING/WARNING/FAILED/SKIPPED map to Complete/Waiting/Running/Attention/
Failed/Skipped. Final recorded business outcome is a separate element: five completed stages can yield BLOCKED.
Technical failure/interruption shows no financial decision. Node details are native keyboard disclosures with
actual timestamps and concise explanations; no prompts, model reasoning or chain-of-thought.

Timings prefer recorded named measurements, then valid persisted start/finish duration, otherwise an em dash.
Sub-second measurements show milliseconds rather than rounding2ms to0s. A real recorded0ms remains0ms.
Horizontal connected cards on desktop/laptop become a vertical connected path below900px. Completed traces
stay visible after the primary recorded business decision and policy disclosure; processing makes the trace
its focal surface. Source/decision workspace and mobile decision-first hierarchy remain.

## F. Motion

Only a returned RUNNING stage has an ongoing connector animation (transform,1600ms loop). Complete/waiting/
failed/skipped connectors are static; no percentage, ETA or simulated progression. Reduced motion disables
connector and spinner movement while text/icon/border convey state. Native disclosures do not animate height.
The segmented tolerance indicator moves in220ms to the requested setting, never to an inferred outcome.
Only a real preview API response triggers the finite220ms opacity/transform result entrance. The static
stored-extraction/current-authority/policy/evaluation path never pretends Gemini ran. Focus is immediate.

## G. PRICE_3PCT — genuine live result

Exactly one real browser upload through the actual FastAPI/orchestration/document/finance path after offline
checks passed. Model:gemini-3.5-flash-lite; route:native_text; no runtime metadata dependency or escalation.
Run:`d2269cade6cb4dca94e6239e5658d25a`. All8 critical header fields match the unchanged manifest:
Northstar Supplies;PRICE_3PCT-2026;2026-11-14;PO-2010;INR;net10300;tax1854;total12154.
Line:NS-CHAIR-01,qty10,unit1030,line net10300. All13 returned field references independently NATIVE_VERIFIED.

| Evaluation | Actual outcome | Reason |
|---|---|---|
| Recorded2% | COMPLETED / REVIEW_REQUIRED | PRICE_VARIANCE |
| Preview5% | READY_FOR_AP | No price-variance or other review/block finding |
| Original after preview/reload | COMPLETED / REVIEW_REQUIRED | PRICE_VARIANCE retained |

Actual reported usage:1 model call,542 input tokens,681 output tokens. Measured extraction5807ms,
matching2ms,evaluation2ms,total processing5852ms. No cost or general accuracy claim. The unchanged PO has
25000 net and25 units remaining, so10300/10 fit existing hard controls. No manifest or financial workaround.

A real RUNNING extraction trace was captured during that single call before the later creative override;
`tmp/phase06a-qa/actual-live-trace-1440.png`. All later design captures reuse persisted history or explicitly
TEST_ONLY intercepted running states, never another model call. Sanitized oracle/usage/evidence result:
PHASE_06A_LIVE_RESULTS.json. The new native PRICE_3PCT.pdf uses the existing generator's explicit --case flag;
the default original four selections and all existing PDF bytes remain unchanged.

## H. Hard-gate examples

| Scenario |2% outcome |5% preview | Proof source |
|---|---|---|---|
| PRICE_3PCT | REVIEW_REQUIRED / PRICE_VARIANCE | READY_FOR_AP | Offline full pipeline + live browser/API |
| OVERBILLED_PARTIAL | BLOCKED | BLOCKED / PO_BALANCE_EXCEEDED + PO_QUANTITY_EXCEEDED | API tests + existing genuine live run/browser |
| DUPLICATE_REISSUED | BLOCKED / EXACT_DUPLICATE | BLOCKED / EXACT_DUPLICATE | Deterministic API tests using authoritative seed history; no new inference |

## I. Creative direction and actual browser QA

The supplementary user override explicitly expands the affected frontend scope to the overview and shared
visual system. Before coding it, preserved actual Chrome screenshots and wrote PHASE_06A_DESIGN.md. The
reference video tmp/ui-reference.mp4 was absent; only supplied descriptions were used. Baseline weaknesses:
equal-count admin strip, uniform typography, thin trace, flat policy columns, insufficient sectional identity.

Selected **Editorial Fintech × Interactive Control Room**: warm cream/white, deeper forest, mint/citrus accents,
native Georgia editorial headings with system-sans working data, crisp12px signature surfaces and8px utility
surfaces. The overview now groups actual review/blocked/flagged net in one dominant asymmetric bento, with
upload and supporting counts beside it, then distribution and the readable ledger. No new metric or meaning.
Policy retains recorded light/current versus forest/hypothetical regions, explicit preview labeling and locked
controls. Connected execution cards use distinct active/completed/technical states, with financial result separate.

Research:Aceternity bento/timeline composition, shadcn bounded single-selection patterns, Motion React layout/
accessibility options and Tailwind focus/state/reduced-motion guidance. Links/licence review in PHASE_06A_DESIGN.md.
All implementation is original CSS/React/native controls. No Aceternity Pro source/assets, Next.js assumptions,
Motion dependency, new design library, external fonts or runtime image requests. CSS suffices for fixed-choice
selection and finite response motion; no unnecessary presence/layout framework.

**Rendered iterations:**
1.Functional6A baseline and critique, actual5 persisted runs at all three widths preserved in
  tmp/phase06a-design-before (policy subdirectory includes the first plain functional comparison/trace).
2.Creative iteration1:asymmetric attention surface, editorial chrome/typography, dark execution cards and
  split policy comparison; built and captured core15 views + policy/trace states. Inspected actual screenshots.
3.Creative iteration2:stronger flagged-value typography, explicit Preview outcome label and settled finite
  animation captures. Rebuilt, inspected desktop/laptop/mobile, then repeated browser checks. Resolved a hidden
  decorative-indicator audit finding with a neutral visible base and explicit dark-processing contrast.

**Final actual Chrome results:**core15 actual-data views +7 test-only states. Focused policy/trace suite:
PRICE and OVERBILLED recorded/preview pairs at1440×1000/1024×900/390×844 (12 states), plus3 TEST_ONLY running
traces, with fold captures as well. No horizontal overflow, native node keyboard/focus, actual-only active nodes,
horizontal/vertical transformation, reduced connector/spinner/indicator/result motion, original main badge,
all persisted snapshots/active policy and no uncaught JS checked. Tables/long fields/source fallback remain usable.

**Audits:**Hallmark final rendered sweep over overview/PRICE/BLOCKED:0FAIL,0WARN,3ANSWERED,8files/3URLs/15shots.
Answers:verbatim required disclaimer; meaningful execution-node markers; clipped semantic mobile table header
with all visible data cells verified in viewport. Earlier refinements fixed connector-over-icon paint order,
2ms rounding, disclosure-geometry false positives, contrast and decorative hidden-base issues. No open failure.
Vercel review:semantic native controls, visible instant focus,44px label targets, async result announcements,
request-disabled controls, preserved URL worklist filters, readable numeric data, responsive layouts and reduced
motion. Taste critique:stronger composition and sectional contrast, less generic card repetition, distinctive
whole-heading typography; queue stays sober. Rejected marketing heroes/full-screen pacing, table tilt, particles,
scroll-as-progress beams, glass over numbers and looping decorations. No formal accessibility certification.

**Performance:**no dependency changes. Final build1751 modules,JS316.59kB/CSS61.08kB uncompressed,
gzip99.34/10.87kB,versus accepted5.1 gzip97.19/7.76kB. This is measured bundle size, not a runtime benchmark.
No extra requests for fonts/assets. No observed accessibility/layout regression in exercised workflows; mobile
attention intentionally leads with review/blocked/value and supporting counts follow. Native PDF embedding
remains browser-dependent with explicit working source-open fallback.

### Before / after screenshot gallery

Local ignored artifacts, not committed giant image assets. Before means functional6A before the creative
override; both sides use the same real persisted facts. Running images are clearly test-only response states.

| View |1440×1000 |1024×900 |390×844 |
|---|---|---|---|
| Overview | [Before](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-before/overview-1440.png) / [After](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-after/overview-1440.png) | [Before](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-before/overview-1024.png) / [After](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-after/overview-1024.png) | [Before](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-before/overview-390.png) / [After](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-after/overview-390.png) |
| Policy comparison | [Before](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-before/policy/price-preview-1440.png) / [After](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-after/policy/price-preview-1440.png) | [Before](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-before/policy/price-preview-1024.png) / [After](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-after/policy/price-preview-1024.png) | [Before](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-before/policy/price-preview-390.png) / [After](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-after/policy/price-preview-390.png) |
| Running trace (TEST ONLY) | [Before](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-before/policy/TEST_ONLY-running-1440.png) / [After](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-after/policy/TEST_ONLY-running-1440.png) | [Before](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-before/policy/TEST_ONLY-running-1024.png) / [After](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-after/policy/TEST_ONLY-running-1024.png) | [Before](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-before/policy/TEST_ONLY-running-390.png) / [After](C:/Users/Asus/Documents/ChatGPT/ap-compass/tmp/phase06a-design-after/policy/TEST_ONLY-running-390.png) |

## J. Full verification commands/results

```powershell
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest06a-final --tb=short
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
.venv/Scripts/python scripts/verify_manifests.py
.venv/Scripts/python scripts/verify_git_hygiene.py
.venv/Scripts/python -m pip check
npm --prefix frontend audit --audit-level=moderate
git diff --check
$env:AP_COMPASS_UI_URL='http://127.0.0.1:8006'
$env:AP_COMPASS_QA_DIR='tmp/phase06a-design-after'
node frontend/scripts/qa.mjs
$env:AP_COMPASS_POLICY_QA_DIR='tmp/phase06a-design-after/policy'
node frontend/scripts/policy-trace-qa.mjs
```

| Check | Result |
|---|---|
| Backend |299 passed (280 original +19 new),52.18s; zero failures,one existing Starlette/AnyIO warning |
| Frontend |47 passed (32 original +15 new),6.55s; zero failures |
| Typecheck/build |PASS; Vite7.3.8,1751modules,final build2.98s |
| Manifests |PASS:6vendors/7POs/3billed/10scenarios |
| Hygiene |PASS:11exclusions,6 fixture PDF byte checks; no credentials/runtime/screenshots tracked |
| Dependencies |pip check clean;npm audit0 vulnerabilities; no dependency/lockfile changes |
| Browser |Core15 real views +7 test states; focused12 recorded/preview states +3 running states PASS |
| Live budget |Exactly1 Flash-Lite generation for PRICE; all previews0 calls; no stronger/metadata requests |

Hallmark command:
```powershell
$env:HALLMARK_PUPPETEER=Join-Path (Get-Location) 'frontend'
node tmp/phase05-skills/hallmark/scripts/sloplint.mjs frontend/src/OperationsBento.tsx frontend/src/Overview.tsx frontend/src/DecisionTrace.tsx frontend/src/PolicyImpact.tsx frontend/src/Workspace.tsx frontend/src/styles.css frontend/src/control-room.css frontend/src/tokens.css --scope app --genre modern-minimal --render --url http://127.0.0.1:8006 --url http://127.0.0.1:8006/runs/d2269cade6cb4dca94e6239e5658d25a --url http://127.0.0.1:8006/runs/3af82d60d6624971b7aa48de920407d5
```

Development failures resolved:initial red policy test failed because the new module did not yet exist;
restricted-sandbox async API test stalled and was interrupted,then passed with normal Windows event-loop
support; one new frontend fixture initially lacked a required typed display field,corrected before acceptance;
Hallmark found initial disclosure/heading geometry,marker,contrast/hidden-base issues,corrected/meaningfully
answered and final sweep passed. A concurrent Chrome PDF network-idle navigation timed out; the unchanged core
suite passed when rerun alone. No test assertions were weakened; no extra inference was used to repair captures.

Local verified application:8006 using the existing Phase4 smoke DB/documents and a temporary one-generation
SDK guard. Guard/credentials/runtime/screenshots stay ignored. Recreating the app retained the PRICE run and
all prior history; previews still worked without extraction. Five persisted analyses now include the new
recorded PRICE review; preview-ready never changes its queue/dashboard classification.

## K. Architecture and changed files

No shared Pydantic contract, financial evaluator, matching, source grounding, AI/provider code, authoritative
DB model/schema, procurement/fixture manifest, original fixture PDF, or original backend/frontend test changed.
Existing orchestration service/repository, upload security, stage persistence and dashboard API definitions
remain unchanged. Only additive API routing/service and frontend display/API-local types were needed.

- **Backend**: api/policy_preview.py;orchestration/policy_preview.py;main.py router registration.
- **Tests/data**: backend/tests/test_policy_preview.py;frontend/src/policy-trace.test.tsx;
  tests/fixtures/PRICE_3PCT.pdf;generator explicit-case option;hygiene fixture-count wording corrected.
- **Frontend**: DecisionTrace,PolicyImpact,OperationsBento,control-room.css;Workspace integration;Overview layout;
  typed API/types,display-only price/tolerance formatting,token additions and stylesheet entry import.
- **QA**: frontend/scripts/policy-trace-qa.mjs;existing qa.mjs unchanged.
- **Docs**: POLICY_PREVIEW,PHASE_06A_DESIGN/REPORT/LIVE_RESULTS,ADR-019,OPERATIONS_UI/ORCHESTRATION_API addenda,
  PROJECT_STATUS and memory status/handoff.

Limits:read-only transient previews,2%/5% only,current authority rather than a historical authority snapshot;
no application of policy,no saved simulation/history,no human PO confirmation/approval/reevaluation/audit
actions,no6B creative fixtures,no deployment. Existing single-process/in-process queue/native-PDF limits remain.

## L. Git checkpoint

Work began from verified4e9665daac7dda661f19217ab9ba8630c640b839 on the requested branch. After passing gates:
commit `feat: add policy impact controls and decision trace`,annotated tag `phase-06a-policy-decision-trace`,
push branch/tag to the existing origin. Final handoff records the full SHA, independent remote branch/peeled-tag
match,clean working tree and prior tag/default-branch preservation. No force-push or history rewrite.

## M. Gate

**PHASE 6A PASS.** Real no-code policy previews and a truthful persisted decision trace are demonstrated;
creative direction assessed through two actual browser-feedback iterations, not audit scores alone. Stop for
architectural/visual review. Phase6B is not authorized and was not started.
