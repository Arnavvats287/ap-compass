# Phase 6B.1 — Audited human PO resolution

2026-11-19 IST. **PASS — stop for architectural review.**
Base b8e5ced6e7dcb3774364cfef44f1a0be0f06a5d0 / phase-06a1-signature-ui.
Branch codex/phase-06b1-human-resolution. Checkpoint phase-06b1-human-resolution.
Full commit SHA,remote branch/tag verification and clean-tree evidence accompany the final chat handoff.
No previous checkpoint/default-branch change. No additional6B creative case,hosting or approval work.

## A. Domain evaluation extension

New app/domain/human_resolution.py defines immutable internal POConfirmation and pure
 evaluate_with_confirmed_po(context,policy,confirmation). It rederives canonical trusted identity,validates
missing explicit PO,approved supplier,same-vendor canonical candidate and explicit rationale. It changes
only the po_identity evaluator for this path,returning PO_MATCH_CONFIRMED with human_review provenance.
All other DEFAULT_RULES,the original aggregator and the input-derived Decimal precision context execute.

Ordinary evaluate,decisions.py,matching.py,rules.py,validation.py,reconciliation.py,controls.py,evidence.py
are unchanged. No selected_po injection or provenance-string loophole in normal evaluation. No invoice
po_reference rewrite,global identity-disable,policy-threshold change,model authority or evidence promotion.
The app additionally requires a completed original analysis and intersection of recorded candidate IDs with
current deterministic same-vendor candidates. Client supplies only the PO ID,never a trusted PO object.
Financial eligibility is not a selection prerequisite: selected closed/overbilled POs remain identified and blocked.

## B. API and audit record

- POST /api/runs/{id}/po-confirmations: strict bounded JSON with po_id,reviewer_label,rationale,client_action_id.
  Labels1–80,rationale10–2000 characters,PO ID1–80,canonical UUID key,extra fields forbidden.8192byte envelope.
  Server IDs/UTC timestamps.201new,200identical replay,404unknown,409ineligible/conflict,422bad input/candidate,
  413too large,415wrong MIME,503trusted evaluation/storage unavailable. No raw validation/provider exception echo.
- GET /api/runs/{id}/review-history: typed actions,current reviewed assessment,availability/current candidates,
  canonical vendor and authority-basis disclosure. Original GET run remains the unchanged RunSnapshotV1.
- GET run summaries add nullable reviewed_outcome,reviewed_at,review_action_id via one outer-joined SELECT.
  Existing one-query regression passes. Original outcome/owner/timestamps,filters and dashboard basis unchanged.

ReviewAction table: server id,unique source run FK,client action key,request fingerprint,validated JSON payload.
Payload contains action type,selected authoritative PO ID,DEMO actor label/disclaimer,rationale,UTC time,
original DecisionV1,full reassessed DecisionV1/findings,exact source PolicyV1/version,authority SHA256,
source-snapshot SHA256,canonical vendor name and candidate selection provenance. No free-form decision text.

BEGIN IMMEDIATE starts one short read/evaluate/insert transaction. No network work. One row atomically stores
both action and complete result. Unique source run means first-confirmation-wins; same key+normalized body
returns the saved result,changed content or competing key returns conflict. Failed evaluation commits nothing.
Append-only triggers reject UPDATE,DELETE and replacement INSERT. No edit/delete/undo endpoint exists.
See HUMAN_PO_RESOLUTION.md and ADR-020. No shared v1 schema extension was needed.

## C. Migration verification

Migration002-human-po-review adds review_action,schema_migration and three triggers only. No populated table
is dropped,recreated or altered. Baseline initialize remains idempotent and explicitly invokes the migration.
Automated test starts an old-schema populated database,seeds it,adds run history,migrates twice,and compares
all old rows. Separate real-runtime verification used SQLite backup of the existing Phase4–6A.1 database:

| Original table | Preserved rows |
|---|---:|
| vendor |6|
| purchase_order |7|
| po_line |7|
| prior_billed_invoice |3|
| invoice_run |5|
| run_stage |25|
| policy_snapshot |1|

All54old rows compare value/byte-identically on the copy. Migration repeated safely. Old-row capture SHA256
 dac31fbc854b4f3d2e57e63a5ddc8948817ecda1eff2e9dcef08d4c0f037e143.
Actual original runtime8006 was untouched. New local8007 uses runtime/phase6b1-demo with copied documents.
Evidence:tmp/phase6b1-migration.json,phase6b1-runtime-verification.json,phase6b1-invariants.json.

## D. Two persisted end-to-end cases

Both went through actual browser PDF upload,real native parsing/source grounding and deterministic financial
analysis using an explicitly TEST_ONLY provider reply; then actual human-review API/database transactions.
This is genuine review persistence/reevaluation,not live Gemini inference. No fake provider output is cited
as model accuracy. UI labels synthetic test extraction. Rationale is demo text,not an authenticated staff assertion.

| Case | Original | Confirmed PO | Reassessment | Outstanding reasons |
|---|---|---|---|---|
| MISSING_PO_VALID |REVIEW_REQUIRED / PO_REFERENCE_MISSING|PO-1042|READY_FOR_AP|None requiring review/block|
| AMBIGUOUS_PO |REVIEW_REQUIRED / PO_AMBIGUOUS + PO_REFERENCE_MISSING|PO-1042|REVIEW_REQUIRED|CRITICAL_FIELD_MISSING,LINE_MAPPING_UNRESOLVED|

MISSING_PO_VALID: approved Meridian alias; invoiceMISSING_PO_VALID-2026,date2026-11-18,itemMC-CLOUD-01,
qty2/unit5000/net10000/tax1800/gross11800. PO1042 authorized200000,prior billed120000,remaining80000;
remaining qty16. Suggested values have no ledger/duplicate conflict; no alternative/seed change needed.
Eleven non-null references independently NATIVE_VERIFIED by real PDF text. Extracted PO remainsNone/MISSING;
optional extracted line.net remainsNone/MISSING. Neither is fabricated by human confirmation. Existing engine
allows unknown optional line net while checking known qty×price; mandatory identity is explicitly confirmed.
Action54411285e8874a2d9e4f4b5aeb22564f,run099a7620a724409bbe03cbc58b63cd6c,
UTC2026-11-19T10:21:18.621496Z. Reassessment codesPO_MATCH_CONFIRMED,BANK_DETAILS_NOT_PROVIDED.

AMBIGUOUS_PO remains the frozen manifest case: net58000/tax10440/gross68440; item,qty,unit price and optional
line net remainNone. Header evidence remains verified; description source uncertainty remains unchanged.
Action814571fb44904c019e6af52b0eebce12,runf81ab36476594ee8b12d77d595f88330,
UTC2026-11-19T10:21:24.361629Z. Identity findings are resolved; missing facts prevent ready. OwnerAP and
source clarification/line-mapping actions remain visible. Confirmation is not a false approval success.

## E. Negative and boundary tests

Confirmed missing-reference variants of OVERBILLED_PARTIAL retain BLOCKED/PO_BALANCE_EXCEEDED+
PO_QUANTITY_EXCEEDED. DUPLICATE_REISSUED retains BLOCKED/EXACT_DUPLICATE. Existing frozen scenarios are
unchanged; variants are explicitly synthetic unit facts. Closed current PO yields BLOCKED/PO_CLOSED.
Unverified critical evidence retains REVIEW/SOURCE_EVIDENCE_MISSING,with input snapshots unchanged.
Reject cross-vendor/nonexistent/unrecorded candidate,explicit reference (including same-PO override),unapproved
vendor,missing rationale,invalid label/key,extra fields,incomplete/failed run,oversize/malformed/wrong-MIME input.
Repeated pure evaluation is deterministic. Concurrent API confirmations produce exactly one201 and one409.
Same-key replay returns200identical action; changed rationale/key cannot replace it. Triggers reject mutation.
Failure-before-insert leaves no partial audit row; sensitive errors/inputs are absent from responses/logs.

## F. Immutability, source policy and persistence proof

Integration tests capture original InvoiceRun JSON,RunStage rows,PolicySnapshot rows and all authoritative
Vendor/PO/POLine/PriorBilledInvoice rows before/after confirmation,replay and policy preview: identical.
SQL tracing during reassessment sees only an INSERT into review_action,no other write. Tests replace extractor/
PDF-reader/parser with failing sentinels during reassessment. Current authority is reloaded (closed-status
regression); source policy is retained even when the configured active policy differs.

Actual runtime verifier compares all old rows against the original DB,then validates each new action's
source fingerprint,original decision and source policy against its still-unchanged original run payload.
Both stored authority fingerprints match current unchanged typed masters:
 f6e95512f3e71d59bf512c1afc861e69587c3bbf40a9400c0f6c04739d02bf31.
This uses canonical sorted typed-master JSON,distinct from the earlier raw-SQL authority hash basis.

After both actions,actual FastAPI process was stopped/recreated on the same DB/documents. Full run JSON,
review history/assessment and document SHA256 values match the pre-restart capture for both cases.
No extraction on history reload. Current runtime:7uploaded runs,35stages,2review actions. Review actions are
not uploaded invoices. Dashboard remains7completed,ready1/review4/blocked2 on original automated basis;
human-reviewed-ready is separately labelled,not silently recounted as an automated ready invoice.
Evidence:tmp/phase6b1-restart-before.json,phase6b1-restart-results.json and read-only runtime verifier output.

## G. No Gemini and no document reprocessing

**0new Gemini calls.** No optional live call used. Normal tests and both browser regression uploads use an
injected TEST_ONLY-review-provider; two fake extraction calls for two actual PDF uploads. Human confirmation,
read/restart and policy preview use zero extraction/provider/PDF calls. Prior6A generation guard stays1.
Production default Gemini adapter/configuration is unchanged; local demo runtime intentionally injects the
fake extractor and loads no new credential/provider client. Stored fake usage/tokens are test data,not live usage.

## H. UI and browser evidence

Existing visual system retained. Eligible cases offer Review PO candidates with current authoritative
candidate comparison,required rationale/demo label,native modal and deliberate Confirm PO & re-evaluate.
No preselected PO; disabled pending controls plus synchronous lock prevent accidental repeat submission.
Stable key permits safe uncertain retry. Original automated outcome/current reassessment are separate;
stored time/rationale,changed identity,remaining findings/owner/action and provenance are visible.
Explicit payment/posting disclaimer and unauthenticated actor label remain. Policy preview discloses original
context; it does not reuse saved human selection. Historical candidate copy no longer suggests no review
workflow exists. Overview/queue explicitly disclose original automated counting/filter basis.

Actual screens under tmp/phase6b1-qa: MISSING_PO_VALID/AMBIGUOUS_PO-original-1440.png,
*-candidate-dialog-1440.png,*-reassessed-{1440,1024,390}.png,reviewed-queue-1440.png.
Initial browser interaction saved the two real actions; final reruns deliberately reuse them and perform no
new POST. TEST_ONLY-dialog[-actions]-{1440,1024,390}.png are visibly labelled intercepted pre-confirmation
layout checks only; never submitted. Native modal prevents background application focus; Chrome may visit
browser chrome at its Tab boundary,then returns to dialog controls. Escape/cancel restores focus; actual
submission focuses result. No horizontal overflow,uncaught JS errors or unsupported approval claim.
Core QA:15actual-data views +7controlled states; policy QA:12recorded/preview states +3labelled running states.
Keyboard/filter/search/disclosure/PDF/reduced-motion and stored snapshot/policy comparisons pass.

## I. Exact commands and results

Repository root,PowerShell. No live provider flag used.

| Command | Actual result |
|---|---|
| .venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest6b1-final-safe --tb=short |328passed,58.00s;1existing Starlette/AnyIO deprecation warning |
| npm --prefix frontend test |58passed,3files; original48+10new; final6.29s |
| .venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests/test_review_api.py -q --basetemp tmp/pytest6b1-proof --tb=short |19passed,4.48s after strengthening parser/SDK sentinels |
| npm --prefix frontend run typecheck |PASS |
| npm --prefix frontend run build |PASS,Vite7.3.8,1754modules |
| .venv/Scripts/python scripts/verify_manifests.py |PASS6vendors/7POs/3billed/10frozen cases |
| .venv/Scripts/python scripts/verify_git_hygiene.py |PASS11exclusions/8binary-safe PDFs; no ignored tracked files |
| .venv/Scripts/python -m pip check |No broken requirements |
| npm --prefix frontend audit --audit-level=moderate |0vulnerabilities |
| .venv/Scripts/python scripts/generate_review_fixtures.py |2native PDFs generated from separate fixture/reused frozenAMBIG case |
| node frontend/scripts/qa.mjs |15views+7controlled states PASS,no mutations/JS errors |
| node frontend/scripts/policy-trace-qa.mjs |12recorded/preview+3controlled traces PASS;6read-only previews,no uploads |
| node frontend/scripts/review-qa.mjs |2actual persisted review cases;6responsive reassessment views;3unsaved modal layouts;keyboard/focus/no-overflow PASS |
| .venv/Scripts/python scripts/verify_review_runtime.py --db runtime/phase6b1-demo/runs.db --baseline runtime/phase04-smoke-0221866e9e214f3a84149d1f79098bd9/runs.db --output tmp/phase6b1-runtime-verification.json |PASS old54rows/source fingerprints/policies/actions |
| git diff --check |PASS |

Browser env AP_COMPASS_UI_URL=http://127.0.0.1:8007;
AP_COMPASS_QA_DIR=tmp/phase6b1-core-qa;AP_COMPASS_POLICY_QA_DIR=tmp/phase6b1-policy-qa;
AP_COMPASS_TEST_EXTRACTOR=true only for the explicitly fake-extractor review runtime.
Local startup/restart command:.venv/Scripts/python tmp/phase6b1-runtime.py (hidden process,localhost8007).
It creates the actual app with copied runtime DB/documents and injected backend test ReviewExtractor.
Migration copy used sqlite3.connect(read-only source).backup(new_connection); never overwrote existing data.

Encountered resolved checks: initial domain test failed because the new module did not yet exist (test-first).
A native-evidence assertion initially included null optional fields; corrected to require verification of non-null
facts while preserving null/MISSING refs. jsdom lacks native dialog methods; unit tests provide a local shim,
actual Chrome tests use real dialog. Browser Tab initially assumed no browser-chrome boundary; inspection
proved native modal remains active and background app controls inaccessible,then test was corrected accurately.
Final review also reproduced an unexpected RuntimeError escaping the new route; it now returns a sanitized503 with rollback,covered alongside expected failures. No outstanding failed acceptance test or business-oracle workaround.

Final assets: JS329.58kB/gzip102.60,CSS74.61kB/gzip12.85; compared with6A.1 JS319.50/gzip100.13 and CSS70.59/gzip12.23: +10.08/+2.47kB JS and +4.02/+0.62kB CSS. Build3.08s. Publication SHA accompanies the final handoff. No package
or lockfile change,new framework/auth/queue/deployment dependency or broad design rewrite.

## J. Known limitations and authorization honesty

**Demo reviewer — identity not authenticated.** A label is not verified employee identity. No production
maker-checker or tamper-proof audit guarantee. SQLite triggers protect app-level append-only storage,not a
privileged DB administrator. Authority fingerprint identifies used records but does not archive the entire
master snapshot. No correction/supersession/undo or second confirmation; first action wins. A future correction
workflow requires separate authorization. Existing single-process runtime/worker/history bounds persist.

Public-facing write access needs a basic access safeguard and suitable request protections before release;
recorded in ADR-020/HUMAN_PO_RESOLUTION,not implemented/deployed here. New fixtures use fake extraction,
not an additional live-model accuracy claim. Native mobile PDF embedding still varies; source-open fallback.

## K. Files and Git

Backend:new domain/human_resolution.py,orchestration/reviews.py,api/reviews.py,db/migrations.py;
small additions in db/models.py,db/session.py,main.py,api/runs.py,orchestration/repository.py.
Tests:new test_human_resolution.py,test_review_api.py,review_fixtures.py; existing backend tests unchanged.
Frontend:new HumanPOReview.tsx,human-review.css,human-review.test.tsx,scripts/review-qa.mjs; scoped workspace/
queue/overview/table/API/types/main integration; PolicyImpact copy clarifies separate confirmation semantics;
operations.test copy/basis assertions. No frontend finance rules.
Data:separate human_resolution_manifest.json,two tests/fixtures/human_resolution PDFs.
Scripts:nullable-case generator support,new generate_review_fixtures.py,read-only verify_review_runtime.py,
recursive PDF Git hygiene. Docs:this report,HUMAN_PO_RESOLUTION,ADR-020,contract/finance/API/UI/preview notes,
PROJECT_STATUS,memory. Frozen seed/fixture manifests,original6PDF,shared contracts,financial rule modules,
extraction/provider/upload/stage orchestration semantics and dependency lockfiles unchanged.

Commit message feat: add audited human PO resolution. Annotated tag phase-06b1-human-resolution,branch
codex/phase-06b1-human-resolution. Push only after verified acceptance; exact SHA/remote proof in final chat.

## L. Gate

**PASS.** Both required human-resolution stories are demonstrated with persisted action+reassessment,strict
identity validation,unchanged original runs/stages/ledger,no document reprocessing,and explicit demo identity.
Stop for review. No extra creative edge cases,model benchmarking,release hosting or visual redesign.
