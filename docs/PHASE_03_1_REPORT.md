# Phase 3.1 — Document engine stabilization report

**Date:** 2026-11-19 (IST). **Revised Phase 3 required gate: PASS. Architectural review pending.**
Scope is this stabilization pass only. Stronger escalation remains optional, disabled and live-unverified.
No Phase 4, upload API, run orchestration, UI, paid service or new model was added.

## Repository and checkpoint

- Worked on codex/phase-03-document-engine from exactly f8ce2026fb18b52fbd1d358d92c4b904311174e1.
- Existing repository: https://github.com/Arnavvats287/ap-compass.git.
- Required checkpoint: phase-03-document-engine, created only after required acceptance passed.
- This report is prepared before its own commit. Final commit SHA/tag/remote push verification is recorded in
  the final chat handoff; resolve the checkpoint with `git rev-parse phase-03-document-engine^{commit}`.
- Existing Phase 1/2 tags are preserved. No force push or default-branch replacement.

## Implemented stabilization

### Primary-only mode

GEMINI_ESCALATION_ENABLED defaults to false in code, .env.example and the ignored local .env.
Only the primary model is validated, metadata-checked and constructed. Native and image-only inputs use
configured primary gemini-3.5-flash-lite; stale optional model/thinking/scan overrides do not create a dependency.
The smoke utility also respects the active-model set, so a disabled optional model is never benchmarked accidentally.
Invalid boolean spellings fail configuration rather than accidentally enabling requests.

Enabled mode preserves two total attempts and at most one stronger attempt. Optional metadata is lazy, checked
only when the stronger provider is actually needed. Both providers retain the same schema and independent grounding.
No registry or third model. Operators must keep escalation disabled until stronger inference genuinely succeeds.

### Usable primary retention versus technical failure

A strict-schema-valid, grounded extraction with meaningful facts may still be incomplete or source-uncertain.
If optional escalation then fails with PROVIDER_UNAVAILABLE, PROVIDER_TIMEOUT or RATE_LIMIT, retain that exact
primary snapshot. Its evidence and missing values are not upgraded. selected_model_id identifies the primary,
retained_primary=true and the failed optional attempt/error/status/timing/unknown usage remain visible.

Malformed JSON, invalid schema, an entirely empty structured reply or primary unavailability without usable
facts still raises a typed technical extraction error. No fictitious review/approval or completed stronger call.
Fallback is limited to the requested availability/timeout/quota cases; other invalid/refused responses fail closed.
The subsequent existing deterministic evaluator—not the adapter—owns REVIEW_REQUIRED/BLOCKED.

Metadata-only failures have inference_called=false and do not inflate model_calls. Request-local ContextVar
tracking preserves this distinction even if an outer short deadline cancels metadata work before generation starts.
This is adapter-local telemetry, not a shared-contract or database change. SDK automatic retries remain disabled.

### Unstated scanned line net

For image-only/mixed input, optional line.net is retained only when the existing independent native verification
establishes an explicit statement. Otherwise it becomes None, and the evidence normalized_value becomes None.
Any raw model claim remains explicitly unverified for audit; no evidence state is promoted. Independently verified
native line net on a native page within a mixed document is preserved.

No OCR, inferred document-stated value, zero filling, corrected gross or fixture change. SCAN_CONFLICT's header
net/tax/gross stay 70000 / 12600 / 86200. The finance engine can separately calculate qty×price without pretending
that result was printed. Its INR 3600 arithmetic discrepancy remains visible.

## Exact checks and observed results

Executed from repository root:

```powershell
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest-phase031-acceptance --tb=short
.venv/Scripts/python -m pip check
npm --prefix frontend run build
.venv/Scripts/python scripts/verify_manifests.py
.venv/Scripts/python scripts/verify_git_hygiene.py
git diff --exit-code f8ce2026fb18b52fbd1d358d92c4b904311174e1 -- backend/app/domain backend/app/contracts backend/app/db backend/app/api backend/app/main.py backend/tests/test_foundation.py backend/tests/test_finance_engine.py data frontend tests/fixtures Dockerfile .dockerignore scripts
```

| Check | Actual result |
|---|---|
| Final backend acceptance | **229 passed**, zero failures, **1 existing warning**, 35.85s |
| Original regression suites | All 129 Phase 1/2 tests unchanged and passing |
| Document suite | 100 tests: original 76 plus 24 stabilization regressions |
| Frontend build | TypeScript/Vite PASS; 1682 modules, unchanged source/assets |
| Dependency consistency | No broken requirements; no dependency changes in this pass |
| Manifest validator | PASS: 6 vendors / 7 POs / 3 billed invoices / 10 unchanged cases |
| Git hygiene | PASS: 11 exclusions and indexed fixture bytes; .env remains ignored |
| Protected implementation/data diff | Empty, exit 0; includes all five fixture PDFs |
| Sensitive logging | Existing and new tests pass; failed provider payloads are not logged |

Regressions cover disabled optional construction/metadata for native and scan; invalid unused optional settings;
retention across three failure classes and both incomplete/uncertain primary states; deterministic REVIEW or BLOCK
from retained facts; unusable/empty primary failure; optional metadata failure with no generation count;
short-deadline accounting; unchanged verified native evidence; scan optional net/gross/discrepancy; and no secrets in logs.
Enabled two-model schema-compatible success remains tested with deterministic fakes, not live Flash calls.

Failures observed during development are preserved here: nine new focused regressions initially failed against
the old behavior. After implementation 228 tests passed. An added short-deadline regression then exposed a count
race (1 failed / 228 passed); request-local tracking fixed it. Five focused counter/metadata tests passed, followed
by the final **229/229** run. No failed test remains. The warning is the existing Starlette/AnyIO BlockingPortal alias.

## One genuine Flash-Lite smoke test

Performed exactly one additional generation, through `extract_configured_pdf(scan_bytes, max_attempts=1)` with
GEMINI_ESCALATION_ENABLED=false and the user's local key. A one-off Python here-string loaded .env, wrapped the
SDK metadata/generation methods only to record model IDs, extracted SCAN_CONFLICT, compared to the unchanged
manifest and ran the existing pure evaluator on trusted seed snapshots. No production orchestration was built.
Sanitized record: PHASE_03_1_LIVE_RESULTS.json. No raw PDF, provider response, bank value or key was logged/persisted.

| Measurement | Actual result |
|---|---|
| Requested/reported model | gemini-3.5-flash-lite |
| API method | client.aio.models.generate_content, Gemini Developer API v1beta |
| Outbound model requests | One primary metadata lookup, one primary generation; **zero Flash requests** |
| Route | image_only; original scan fixture unchanged |
| Grounded comparison | 13/13 expected adapter fields match; no general model-accuracy claim |
| Optional line net | None |
| Header gross | INR 86200 preserved |
| Evidence | All scan evidence remains unverified; zero NATIVE_VERIFIED promotions |
| Existing evaluator | REVIEW_REQUIRED; SOURCE_EVIDENCE_MISSING and TOTAL_RECONCILIATION_FAILED |
| Arithmetic discrepancy | INR 3600 |
| Model-attempt elapsed | 2686ms |
| Adapter elapsed | 3241ms (setup metadata lookup is outside adapter timing) |
| Tokens | 1399 input / 914 output / 2313 total; thinking not reported |

The 13/13 comparison describes post-grounding adapter output. It does not claim the raw model stopped inferring
optional line amounts. The prior Phase 3 raw line-net error remains historical evidence; the new conservative policy
prevents that unverified optional claim from becoming a document-stated fact.
Prior genuine native HAPPY_CLEAN/OVERBILLED_PARTIAL successes remain recorded in PHASE_03_LIVE_RESULTS.json.
No Gemini 3.6 Flash metadata lookup or generation occurred in this stabilization pass. Fake-enabled tests are not live evidence.

## Files changed

- backend/app/ai/gemini.py: disabled-by-default optional configuration, primary-only runtime, lazy optional checks.
- backend/app/ai/provider.py: request-local inference telemetry; extraction instruction text unchanged.
- backend/app/ai/smoke.py: active-model filtering, respecting disabled escalation.
- backend/app/documents/pipeline.py: usable-primary retention, empty-response handling, honest attempt metadata.
- backend/app/documents/types.py: adapter-local retained_primary/inference_called flags; no shared v1 shapes changed.
- backend/app/documents/evidence.py: conservative scanned optional line-net handling, original uncertainty retained.
- backend/tests/test_document_engine.py: 24 new regressions; enabled-mode expectations made explicit.
- .env.example: safe disabled default; local .env updated without exposing/committing the key.
- README, DOCUMENT_ENGINE, PROJECT_STATUS, memory and ADR-016: revised release decision and current evidence.
- PHASE_03_REPORT: historical report preserved with a superseding stabilization notice.
- This report and PHASE_03_1_LIVE_RESULTS.json: current acceptance evidence.

**Unchanged:** financial contracts/rules/matching, database schema, procurement/billed manifests, fixture expectations,
all fixture files, frontend, API endpoints, Docker and dependencies. No source evidence fabricated or upgraded.

## Limitations and stop condition

Stronger inference remains unverified and disabled. Conservative labelled-layout verification and scan uncertainty
remain; no OCR or generalized extraction accuracy is claimed. Truly unusable primary output still fails technically.
No optional fallback is interpreted as approval. Future callers must inspect technical metadata and apply the
unchanged deterministic evaluator. Previous resource limits and no-tool/no-authority boundaries remain intact.

**Revised Phase 3 gate: PASS; ready for architectural review.** The deliberate single-required-provider adjustment
is documented in ADR-016, not represented as successful two-model inference. Phase 4 remains unauthorized.

## Completed segment-template checklist

- [x] All required stabilization cases and existing regressions pass.
- [x] One genuine primary-only scan extraction and existing native proof documented honestly.
- [x] Failed optional attempts and missing/unverified facts remain visible; no false approval or usage.
- [x] Financial contracts, policies, ledger, manifests and business outcomes preserved.
- [x] Status/memory updated from actual evidence; checkpoint created only after passing required checks.
- Stop after this stabilization pass; no automatic next phase.
