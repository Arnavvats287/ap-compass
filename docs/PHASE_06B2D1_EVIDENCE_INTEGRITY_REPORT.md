# Phase 6B.2D.1 — Financial evidence integrity

## Baseline and actual red observation

Started at `bc674cac698a1c09ab94ff8b93592c50b5ebdad2`, annotated checkpoint `phase-06b2c4-postfix-validation`, on a clean tree. Branch `codex/phase-06b2d1-evidence-integrity`. The reproduction used original, visible native PDFs built in memory, the bounded parser, a controlled provider through the real wire schema, independent source grounding, and the deterministic evaluator with seeded authority. No live inference, held-out evaluation, or production history reprocessing occurred.

The legacy `local_support` verified which line contained the claim and compared both the printed amount and claimed raw value by Decimal magnitude. It ignored the printed denomination. The geometry path already checked a recognized printed prefix against a supplied invoice currency. The finance rule `currency_compatibility` compares the extracted **invoice** currency to the authoritative PO currency. It cannot infer a conflicting printed amount denomination from the normalized financial facts.

The pre-change run of the first 44 development tests showed **12 failures and 32 passes**. In ten legacy cases, recognized printed `USD` or `$` on one required amount with an extracted INR invoice produced `NATIVE_VERIFIED` and `READY_FOR_AP`. Each variant kept the numeric magnitude, valid arithmetic, and an INR PO unchanged. These were controlled synthetic end-to-end observations. The layout-geometry equivalents already withheld verification. A legacy net also verified when the controlled raw claim omitted the foreign prefix. The legacy path additionally accepted an explicitly currency-prefixed quantity. Matching INR/₹ and unprefixed controls were green, and the equal-magnitude revised total conflict continued to withhold verification.

## Repair and safety outcome

`documents/consistency.py` now parses the existing printed amount grammar into exact `Decimal` plus the existing normalized currency code or absence. It uses the same result for the existing document-wide conflict check. `documents/evidence.py` uses one monetary predicate for the legacy labelled line and layout-cell paths. It requires the same exact numeric value, a printed denomination compatible with the extracted invoice currency when explicitly present, and a raw claim whose matched text is actually present in the amount cell or labelled value. A raw claim can omit a compatible prefix but cannot supply, overwrite, or hide a contradictory printed prefix. A quantity must be unprefixed in both source and claim. No new currency spellings, layout heuristics, OCR, or inference were added.

| Scenario | Before | After |
|---|---|---|
| INR, ₹ and unprefixed amounts with independently supported INR invoice currency | Native verified, Ready | Native verified, Ready |
| Legacy printed USD or `$`, extracted INR, exact magnitude | Native verified, Ready in the controlled red run | Source located unverified, Review with `SOURCE_EVIDENCE_MISSING` |
| Geometry printed USD or `$`, extracted INR, exact magnitude | Source located unverified, Review | Source located unverified, Review |
| Legacy foreign denomination omitted from raw claim | Native verified | Unverified, Review |
| Raw denomination substituted or invented, or unknown printed prefix | Unverified | Unverified, Review |
| Same numeric total with competing source denominations | Unverified | Unverified, Review. Arithmetic retained. |
| Explicit denomination with missing extracted invoice currency | Not measured pre-change | Amounts unverified and invoice Review. No guessed currency. |
| Independently coherent USD source and extracted currency against an INR PO | Existing currency control preserved | Amounts verify; existing `CURRENCY_MISMATCH` Blocks. |
| Currency-prefixed quantity | Legacy native verified; geometry withheld | Both withhold verification and the invoice requires Review. |

The repair retains the printed text and extracted numerical values. Contradictory source currency uses the existing source evidence review, without creating a new Block reason. The seeded authority, financial engine, ReasonCode definitions, provider prompt/schema, public contracts, frontend, SQLite schema, and historical decisions are unchanged. The currently recognized amount prefixes and symbols are retained as before. Unsupported representations remain unverified. An unprefixed field can attest the number in the source, while Ready still independently requires invoice currency evidence and PO compatibility.

## Bounded diagnostics beyond denomination

- **Omitted printed row.** Both layouts require Review when the disclosed line net no longer reconciles to the printed invoice subtotal. `LINE_TOTAL_RECONCILIATION_FAILED` fires. Geometry also withholds row evidence when the extraction row count disagrees. Legacy can still verify the retained line in this example, so that line attestation does not establish that every printed line was extracted. This phase makes no completeness repair for layouts or omissions that arithmetic cannot detect.
- **Issuer role.** In the tested explicit Supplier, Bill To and Remit To blocks, the buyer and remittance quotes cannot verify the supplier field. Both stay source located unverified and require Review. These tests establish behavior for those labelled blocks. They do not establish issuer recognition across ambiguous or unlabelled layouts.
- **Equal magnitude across columns.** Both a labelled block and a table require Review when an invoice subtotal quote is used for the unit-price claim. The subtotal itself remains verified. No new layout association was added to produce these results.

The persisted upload test uses a disposable SQLite database and PDF directory. It records an audited historical PO confirmation, uploads a synthetic denomination conflict through the API, verifies the source Review and retained raw amount, then opens a fresh application instance. The current extraction and historical decision/history JSON reload exactly, the PDF is byte-identical, authority rows are unchanged, and reload makes zero extraction calls. Existing historical review, bank mismatch, duplicate, scope, mixed-raster, image-only, conflicting-header, and hard net/quantity regressions remain in the complete suite.

## Frozen files and verification

Compared 28 frozen paths with the starting Git objects. All ten historical and post-fix result SHA-256 digests match their published values in the [post-fix validation report](PHASE_06B2C4_POSTFIX_VALIDATION.md). All tracked PDFs and result files were compared byte-for-byte. Seed, oracle, scoring and fixture-source text comparisons accounted for repository newline normalization. The private archive, held-out PDFs and their annotations were left untouched. No benchmark was rerun.

| Command | Result |
|---|---|
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests/test_currency_evidence.py -q --basetemp tmp/pytest06b2d1-red --tb=short` | Pre-change 12 failed and 32 passed. |
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests/test_currency_evidence.py -q --basetemp tmp/pytest06b2d1-evidence --tb=short` | 49 passed including persisted upload and reload. Local asyncio loopback allowed. |
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q -rx --basetemp tmp/pytest06b2d1-full --tb=short` | 471 passed in 123.95 s. No failures, skips or XFAILs. One existing Starlette deprecation warning. |
| `npm --prefix frontend test` | 58 passed in 3 files. |
| `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` | Passed. Build transformed 1,754 modules. |
| `.venv/Scripts/python scripts/verify_manifests.py` and `.venv/Scripts/python scripts/verify_git_hygiene.py` | Passed. Six vendors, seven POs, three billed records, ten original scenarios, 11 exclusions and ten byte-identical tracked fixtures. |
| `.venv/Scripts/python -m pip check` and `npm --prefix frontend ls --depth=0` | Passed. |

The benchmark-runner clean-tree check passed **25 tests** using `.venv/Scripts/python -m pytest evaluation/test_benchmark_v1.py evaluation/test_postfix_v1.py -q --basetemp tmp/pytest06b2d1-runner`. It exercised temporary development-facts output only. No measured benchmark artifact was regenerated.

**EVIDENCE INTEGRITY PASS — READY FOR RELEASE HARDENING.** This phase stops at the evidence-integrity gate.
