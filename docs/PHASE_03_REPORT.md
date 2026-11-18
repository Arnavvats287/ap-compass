# Phase 3 — Real document extraction review report

> Historical report. The user revised acceptance in Phase 3.1: one working provider is required and escalation is optional/disabled. See PHASE_03_1_REPORT.md and ADR-016 for the stabilization results; earlier failures below are preserved.

**Date:** 2026-11-19 (IST). **Scope:** Phase 3 only. **Gate:** PARTIAL — offline/regression and primary live checks pass;
configured stronger-model inference remains unavailable. No passing phase-03-document-engine tag is created.

## A. Repository

- Branch: `codex/phase-03-document-engine`, created directly from `phase-02-finance-engine`.
- Verified Phase 2 base: `6d9963a6a8883ea87c6a4457e0ce0353c28491a8`, matching local/remote peeled tag.
- Existing remote: `https://github.com/Arnavvats287/ap-compass.git`; no default-branch checkout or repository creation.
- Review commit/branch publication: recorded in final chat after this pre-commit document is written.
- Complete checkpoint: **NOT CREATED** because the full two-model live gate is unresolved. Previous tags preserved.
- Review commit may be pushed as incomplete work; it must not be described as a passing Phase 3 checkpoint.

## B. Extraction architecture

PDF bytes → header/EOF/size validation → short-lived PyMuPDF parser subprocess → per-page text/image inspection →
route selection → bounded official SDK inference → strict local schema validation → independent source grounding →
unchanged ExtractedInvoiceV1 plus immutable adapter-local technical metadata.

No Gemini access to procurement, billed history, policies, tools, filesystem commands or business-decision authority.
No API upload endpoint, runtime document persistence, orchestration, database/schema/finance/UI/Docker changes.

Bounds: 8 MiB, 10 pages, 12s parser wall time, 512 MiB parser memory cap, 30k text characters/page and 150k total;
render <=120 DPI, <=1600 pixels/edge, <=2M pixels/page, <=12 MiB base64 image aggregate. Reject encryption, repair/
corruption, empty input/pages, attachments/XFA and unsupported dimensions. Page numbers and bounded native text retained.
Native pages supply text; image-only and mixed raster pages supply actual PNGs. Mixed pages retain conservative evidence.

Model claims never establish verification. Native grounding independently finds the quote on its stated page, checks
raw and normalized values under field-specific labels and binds line fields to their own item code. Buyer headings,
incidental/repeated amounts, wrong pages, contradictory claims and unsupported contexts cannot become verified.
Scan claims remain SOURCE_LOCATED_UNVERIFIED; no OCR confidence, highlights or bounding boxes invented.
See DOCUMENT_ENGINE.md for detailed limitations and code boundaries.

## C. Provider access, model routing and exact API

- Official installed/pinned `google-genai==3.5.0`; actual method `client.aio.models.generate_content`.
- Gemini Developer API `v1beta`, fixed Google endpoint; text Parts plus actual `image/png` byte Parts;
  `response_mime_type=application/json` and `response_json_schema`; tools empty, automatic function calling disabled.
- `client.aio.models.get(model=...)` succeeded for both configured IDs and advertised generateContent support:

| Model | Resource version returned | Metadata access | Actual inference |
|---|---|---|---|
| gemini-3.5-flash-lite | 3.5-flash-lite-07-2026 | Successful | Successful native and image inputs |
| gemini-3.6-flash | 3.6-flash-07-2026 | Successful | No successful output in tested native/scan attempts |

The user's local `.env.txt` was renamed to ignored `.env` without exposing its contents. Backend configuration:
GEMINI_PRIMARY_MODEL, GEMINI_ESCALATION_MODEL, GEMINI_SCAN_MODEL and GEMINI_ESCALATION_THINKING_LEVEL.
Primary/default scan: Flash-Lite. Escalation: Flash, with documented MINIMAL thinking attempted after gateway timeouts.
This is a provisional scan choice based on actual availability, not a claim of superior comparative accuracy.

At most two explicit inference attempts/invoice and one stronger attempt. SDK retries disabled. Quality escalation
only for malformed/invalid output, missing critical/line facts or unsupported native critical evidence. Primary
transient failures can retry once; quota failures remain technical. No financial outcome/rule triggers model selection.

The supplied account limits (Lite 15 RPM/500 RPD and Flash 5 RPM/20 RPD, each 250K TPM) are user-provided constraints,
not independently measured quota availability. No third model, paid service or unbounded retry loop was used.

## D. Genuine extraction results

These are actual SDK responses, not fake-provider outputs. Every cell is **expected → extracted**.

| Field | HAPPY_CLEAN | OVERBILLED_PARTIAL | SCAN_CONFLICT |
|---|---|---|---|
| vendor_name_raw | Orion Office Products → Orion Office Products | Aster Systems → Aster Systems | Kaveri Logistics → Kaveri Logistics |
| invoice_number | HAPPY_CLEAN-2026 → HAPPY_CLEAN-2026 | OVERBILLED_PARTIAL-2026 → OVERBILLED_PARTIAL-2026 | SCAN_CONFLICT-2026 → SCAN_CONFLICT-2026 |
| invoice_date | 2026-11-14 → 2026-11-14 | 2026-11-14 → 2026-11-14 | 2026-11-14 → 2026-11-14 |
| po_reference | PO-6001 → PO-6001 | PO-3015 → PO-3015 | PO-4002 → PO-4002 |
| currency | INR → INR | INR → INR | INR → INR |
| net | 48000 → 48000 | 30000 → 30000 | 70000 → 70000 |
| tax | 8640 → 8640 | 5400 → 5400 | 12600 → 12600 |
| total | 56640 → 56640 | 35400 → 35400 | 86200 → 86200 |
| lines[0].description | Office supplies → Office supplies | Managed IT services → Managed IT services | Freight services → Freight services |
| lines[0].item_code | OR-SUPPLY-01 → OR-SUPPLY-01 | AS-SERVICE-01 → AS-SERVICE-01 | KL-FREIGHT-01 → KL-FREIGHT-01 |
| lines[0].qty | 48 → 48 | 6 → 6 | 7 → 7 |
| lines[0].unit_price_net | 1000 → 1000 | 5000 → 5000 | 10000 → 10000 |
| lines[0].net | 48000 → 48000 | 30000 → 30000 | None → 70000 |

- HAPPY_CLEAN: **13/13 matches**, no missing/incorrect checked fields; all 13 evidence references NATIVE_VERIFIED.
- OVERBILLED_PARTIAL: **13/13 matches**, no missing/incorrect checked fields; all 13 evidence references NATIVE_VERIFIED.
- SCAN_CONFLICT: **12/13 matches**, no missing required fields; optional line net incorrectly supplied as 70000 although
  absent from the image. This remains an observed model error; no oracle or fixture was changed. All returned scan
  field evidence remains SOURCE_LOCATED_UNVERIFIED. Stated gross **86200** is retained; it is not repaired to 82600.
- Real/native and scan samples are too few for any general accuracy conclusion. No live downstream business decision
  or orchestrated run is claimed. Separate offline tests prove compatibility with the unchanged financial evaluator.

| Successful call | Total adapter elapsed ms | Model-attempt elapsed ms | Input tokens | Output tokens | Thinking | Total tokens |
|---|---:|---:|---:|---:|---|---:|
| HAPPY_CLEAN / Flash-Lite | 3866 | 3403 | 543 | 913 | Not reported | 1456 |
| OVERBILLED_PARTIAL / Flash-Lite | 2742 | 2337 | 542 | 681 | Not reported | 1223 |
| SCAN_CONFLICT / Flash-Lite | 4023 | 3509 | 1399 | 914 | Not reported | 2313 |

Actual reported model ID on these calls: gemini-3.5-flash-lite. Each successful document used one inference.
Unknown tokens are null, never assumed zero. No token costs are invented.

### Failed live attempts preserved

**14 explicit generation attempts total:** six Flash-Lite (three early schema/diagnostic failures, three successes)
and eight Flash attempts (no successful output). No SDK automatic retries. Model metadata lookups are separate from
this inference count. Sanitized per-run records are in PHASE_03_LIVE_RESULTS.json.

- Initial rich grammar failed on Lite; a diagnostic captured HTTP 400 with the allowlisted schema flag.
  Reducing provider-generation constraints while retaining strict local validation resolved Lite generation.
- Flash returned PROVIDER_UNAVAILABLE in the initial and reduced-schema benchmark.
- Bounded later Flash native call returned HTTP **504**; scan timed out at the 30-second client limit.
- MINIMAL-thinking Flash benchmark still returned HTTP **504** for native and scan (29961/30473ms total elapsed).
  No successful model ID or token usage was returned for these failures. None is fabricated.
- No further Flash calls were made after these bounded attempts. Metadata visibility is not treated as verified inference.

## E. Commands and actual test results

From project root:

```powershell
$env:PYTHONPATH = 'backend'
.venv/Scripts/python -m app.documents.fixtures
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests/test_document_engine.py -q --basetemp tmp/pytest-phase03-source-final
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest-phase03-final
.venv/Scripts/python -m pip check
npm --prefix frontend run build
.venv/Scripts/python scripts/verify_manifests.py
.venv/Scripts/python scripts/verify_git_hygiene.py
pdftoppm -scale-to 1000 -png tests/fixtures/SCAN_CONFLICT.pdf tmp/SCAN_CONFLICT
```

| Check | Observed result |
|---|---|
| Final entire suite | **205 passed**, zero failures, 1 existing Starlette/AnyIO deprecation warning, 25.12s |
| Regression coverage | All **129 original tests**, unchanged, plus **76 new document tests** |
| Previous document-only run | 75 passed, 22.88s; final full run also includes the added bank-omission guard test |
| Frontend production build | TypeScript/Vite PASS, 1682 modules; no frontend source changes |
| Dependency consistency | No broken requirements |
| Static manifest oracle | PASS: 6 vendors / 7 POs / 3 billed / 10 unchanged scenario expectations |
| Git hygiene | 11 exclusion probes pass; .env ignored and not tracked; original script validates every PDF byte |
| Extra fixture-byte check | **5 fixture PDFs** match Git index bytes (legacy script's printed four-file count is hardcoded) |
| New scan | Real image-only PDF; no usable native text; values visually inspected; no changes to original four PDFs |
| Protected-file diff against Phase 2 | Empty for finance/contracts/DB/API/frontend/manifests/old tests/original fixtures/Docker/scripts |

Live commands actually run, with separate output files to retain failures:

```powershell
.venv/Scripts/python -m app.ai.smoke --benchmark --report tmp/phase03-benchmark.json
# One sanitized schema-diagnostic request on Flash-Lite (HTTP 400/schema flag).
.venv/Scripts/python -m app.ai.smoke --benchmark --report tmp/phase03-benchmark-minimal.json
.venv/Scripts/python -m app.ai.smoke --benchmark --model gemini-3.6-flash --report tmp/phase03-flash-final.json
# After adding officially supported MINIMAL thinking configuration:
.venv/Scripts/python -m app.ai.smoke --benchmark --model gemini-3.6-flash --report tmp/phase03-flash-minimal-thinking.json
.venv/Scripts/python -m app.ai.smoke --case OVERBILLED_PARTIAL --report tmp/phase03-overbilled-live.json
```

Earlier offline failures were not hidden: sandbox asyncio execution stalled and was stopped; approved execution
resolved the environment restriction. Oversized raw-byte pytest IDs caused Windows temporary-path setup errors;
explicit safe IDs fixed this. A new buyer-heading adversarial test initially failed, then drove the context guard
fix. All final tests pass. No raw provider payloads were logged to diagnose these problems.

## F. Security, scope and limitations

- Fake provider replies are explicitly TEST DATA. Offline tests cover all four native PDFs, strict schema,
  wrong page/quote/value, missing/duplicate evidence, cross-item context, buyer headings, scans/mixed pages,
  encryption/corruption/empty/oversize/page/resource limits, actual hard memory-cap enforcement, timeouts,
  quota/error mapping, retry/escalation bounds, prompt-injection content, tool-call rejection and log redaction.
- Real bank-master comparisons, PO selection and readiness decisions remain solely in the unchanged finance engine.
- No keys, bank values, full model replies or raw PDFs logged. No persistent runtime upload/document store.
  Local key stays in ignored .env; reports contain only synthetic comparisons, statuses and measured metadata.
- The parser subprocess has resource caps and no inherited key; it is not described as a full OS security sandbox.
- Source verification supports conservative labelled layouts/top supplier headings, exact item-code blocks,
  ISO/English month-name dates and supported decimal formatting. Unsupported context remains reviewable.
- No independent OCR/source verification for scans; images never become NATIVE_VERIFIED.
- Private response limits reject unusually large outputs. Partial bank subfields cannot be represented in the
  frozen public bank contract and fail technically instead of being filled or silently discarded.
- No general duplicate/accuracy/security effectiveness claim from these three successful documents.
- No project-wide quota scheduler or persistent workers. No third model, downstream decision model or paid deployment.
- The configured stronger model has **not** completed a genuine inference. Live escalation is therefore unverified.
- **Contract deviations:** none. Private wire schema and technical metadata are adapter-local, not shared-contract changes.
- Necessary dependency deviation: SDK-compatible Pydantic pin 2.14.3; all original contract/domain tests pass unchanged.

Files: backend/app/documents and backend/app/ai implementations; backend/tests/test_document_engine.py;
backend requirements; .env.example; tests/fixtures/SCAN_CONFLICT.pdf; README/status/memory; DOCUMENT_ENGINE,
this report, sanitized live-results JSON and ADR-015 recording the explicit user model-routing update.

## G. Acceptance and handoff

**PARTIAL — full two-model Phase 3 gate is not claimed.** Real native parsing, image handling, source grounding,
Flash-Lite inference and all regression/security tests are verified. External blocker: no successful Flash
native/scan response under the bounded tested configurations, so no comparative Flash quality or live escalation proof.

The implementation is prepared as an explicitly incomplete review commit/branch. **Do not create a passing
phase-03-document-engine tag, mark the full gate passed, or start Phase 4.** A bounded Phase 3 repair should recheck
Flash availability with the same contract, or obtain explicit review authorization for revised routing acceptance.
No new model, paid service, financial rule or schema change is inferred from this blocker.

## Completed segment-template checklist

- [x] Existing 129 tests and 76 new tests pass; frontend/build/seed/protected-file checks pass.
- [x] Genuine primary inference and native evidence, plus honest scan uncertainty, recorded.
- [x] No authority writes, financial-rule changes, fake live claims, fake model usage or fake verified evidence.
- [x] Status/memory updated with the unresolved full-gate blocker.
- [ ] Stronger-model genuine native and scan inference succeeds; full two-model acceptance is pending.
- Actual persisted execution stages/dashboard/upload workflow: NOT IMPLEMENTED / NOT RUN (later phases).
- Stop here for Phase 3 architectural review or repair only.
