# Phase 6B.2B review report

**DEFENSIVE HARDENING PASS**

This is defensive hardening of source-identified trust-boundary limitations. Phase 6B.2A did not independently reproduce the three audit probes. Their exact input sequences were not run in this phase. The results below apply to the specific ordinary or controlled defensive cases tested.

Base f7f669821464183bcad6d8802177d2e170187285. Branch codex/phase-06b2b-document-hardening. See DOCUMENT_TRUST_HARDENING.md for architecture, tradeoffs and limits. The provider supplies facts and claims, the parser and grounder constrain evidence, and the existing deterministic evaluator owns financial outcomes.

| Case | Observation and outcome |
|---|---|
| Disputed native headers | Actual grounder with controlled inspected-page observations downgraded invoice number, net, tax and total to SOURCE_LOCATED_UNVERIFIED. Currency remained NATIVE_VERIFIED. Existing evaluator returned REVIEW_REQUIRED with SOURCE_EVIDENCE_MISSING and a next action. The exact audit PDF path was not tested. |
| Equivalent repeated totals and non-invoice balances | All 13 references remained NATIVE_VERIFIED in the controlled observation test. The real two-page repeated-summary control reached READY_FOR_AP with all 13 verified. |
| Ordinary payment-terms raster notice | Real parser classified it mixed and made the page image available to the test provider. Missing bank details produced PROCESSING_FAILED / UNSUPPORTED_PDF with no persisted extraction, decision or finance stages. One controlled provider reply was counted. |
| Mixed document with bank claims | The native net reference stayed NATIVE_VERIFIED. Bank references were SOURCE_LOCATED_UNVERIFIED and outcome was REVIEW_REQUIRED / BANK_DETAILS_UNVERIFIED. No BANK_DETAILS_MISMATCH. |
| Uniform render with extractable non-invoice prose | The subprocess returned EMPTY_PDF. Real blank PDF and direct uniform pixmap checks also passed. No evidence was granted. The historical occluded-invoice sample was not tested. |
| Visible HAPPY_CLEAN and harmless uniform swatch | Full offline API paths retained 13 NATIVE_VERIFIED references and READY_FOR_AP. |
| Existing financial cases | HAPPY_PARTIAL Ready, OVERBILLED_PARTIAL and DUPLICATE_REISSUED Blocked, PRICE_3PCT Review at recorded 2%, SCAN_CONFLICT Review. Scan values stay unverified. Audited human PO and read-only policy preview regressions passed. |

The subtle false-positive tradeoff is intentional. A nonuniform company logo can trigger mixed routing and the technical gate even if a person identifies it as decorative. The narrow swatch control passed. The original F2 completed-review target is preserved in the golden file. The explicitly permitted adapter-local technical gate is the implemented decision and is recorded separately from that target. It avoids synthetic bank data and needs no shared-contract, DB schema, persistence, API shape, or frontend adjustment. The grayscale check is limited to uniform rendered pages. No general authenticity, occlusion or mixed-layout protection is claimed.

## Inspection cost

Median wall milliseconds for the actual bounded subprocess, including launch, on this local Windows machine. Each version has nine measured iterations per sample after one warmup, with baseline and updated ordering alternated. The baseline parser package was extracted from the base commit into ignored temporary storage.

| Sample | Baseline ms | Hardened ms | Change ms |
|---|---:|---:|---:|
| Native one page | 399.47 | 400.72 | +1.25 |
| Native two pages | 397.07 | 420.88 | +23.81 |
| Native with decorative swatch | 390.12 | 397.58 | +7.46 |
| Native with small payment notice, now mixed | 398.83 | 436.89 | +38.06 |
| Existing image-only scan | 520.13 | 519.57 | −0.56 |

The image-only difference is within ordinary local timing variation. This sample is not a throughput or live-provider benchmark.

## Regression and invariants

- `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest06b2b-final --tb=short` passed 340 tests in 69.82 seconds, including 9 hardening cases and the 3 existing benign controls. One existing Starlette deprecation warning. Zero failures, skips and XFAILs in the final run. Three expected test-first failures preceded implementation. A subsequent test caught incorrect classification of an unmatched native bank citation. The final grounder preserves MISSING for that case.
- `npm --prefix frontend test` passed 58. `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` passed.
- `.venv/Scripts/python scripts/verify_manifests.py`, `.venv/Scripts/python scripts/verify_git_hygiene.py` and `.venv/Scripts/python -m pip check` passed. npm audit reported zero vulnerabilities.
- `.venv/Scripts/python tmp/phase06b2b-bench-compare.py` measured actual parser subprocesses. Ignored raw timings are in tmp/phase06b2b-benchmark.json.
- `.venv/Scripts/python tmp/phase06b2b-runtime.py` used a temporary SQLite backup and document copy with an injected offline extractor. Two historical run snapshots and review histories remained byte-equivalent at the JSON response level. Copied authority records remained equal. The new native and mixed cases persisted the expected Ready and technical outcomes.
- `node frontend/scripts/qa.mjs` against localhost:8008 passed 15 views and 7 controlled states.
- `node tmp/phase06b2b-browser.mjs` checked local HTTP health, the new persisted technical-failure workspace, a new persisted Ready workspace and the existing scan Review next action. The unchanged browser suite also passed 15 views and 7 controlled states with no mutations or uncaught errors.

Immutable financial control, authority, human review, policy preview and shared-contract code stayed at the base revision. Tests use synthetic input and test-only replies. The local failure log contained only run ID, stage and sanitized code. There were zero Gemini generations and zero metadata requests. No credential was needed.

The checkpoint marks the scoped defensive checks above. Exact historic audit reproductions remain outside the observed evidence.
