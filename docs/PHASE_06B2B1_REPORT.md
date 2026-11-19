# Phase 6B.2B.1 verification report

**PASS.** Usable mixed-content invoices with unresolved raster content now complete with review or retain an independent hard block. This phase follows the scoped Phase 6B.2B checkpoint. It makes no new claim about reproducing the historical third-party probes.

## Contract, architecture and evidence

The sole shared field addition is the optional typed document_integrity_flags tuple on ExtractedInvoiceV1. Missing is represented as None internally and omitted by serialization. Newly grounded results carry an explicit tuple, with RASTER_CONTENT_UNRESOLVED for mixed routing. This preserves old JSON output and historical source-fingerprint inputs. The wire schema rejects attempts to supply, clear or null the field. The grounder derives it from the inspection route. The provider does not decide integrity.

The pure document_content rule adds one DOCUMENT_CONTENT_UNVERIFIED Review finding per flagged invoice. It names Accounts Payable and asks the analyst to inspect the full rendered invoice and independently confirm relevant charges or payment instructions. It precedes generic source-evidence review in rule order. BLOCK precedence and the aggregator are intact. PO confirmation and 2%/5% policy previews reuse the stored extracted invoice.

BANK_DETAILS_NOT_PROVIDED is still informational and now reads “No payment instructions extracted.” The explanation separates missing extracted data from visual absence. A bank object is never fabricated. Same-page mixed and image claims remain SOURCE_LOCATED_UNVERIFIED, and unlocated native claims remain MISSING. An independently supported native-page bank contradiction can still block a document with raster content elsewhere. No recovery path changed for unusable or malformed replies, omitted known printed native bank instructions, parser errors or invalid PDFs.

## Observed outcomes

All model-shaped replies were supplied by a test-only provider. The primary upload cases used actual PDF bytes, the resource-bounded parser subprocess, schema validation, evidence grounding, real API persistence and the deterministic evaluator.

| Case | Execution and decision | Evidence and finding |
|---|---|---|
| HAPPY_CLEAN native | COMPLETED / READY_FOR_AP | All 13 references independently verified |
| Native with uniform decorative swatch | COMPLETED / READY_FOR_AP | All 13 references independently verified |
| Identical repeated summary | COMPLETED / READY_FOR_AP | All 13 references independently verified |
| Otherwise clean invoice with fictional two-color logo | COMPLETED / REVIEW_REQUIRED | No mixed-page NATIVE_VERIFIED evidence. One DOCUMENT_CONTENT_UNVERIFIED finding. Known benign logo is one unnecessary review in the test set. |
| Ordinary raster payment-terms notice with no extracted credentials | COMPLETED / REVIEW_REQUIRED | Same document finding, bank object null, informational extraction wording. Zero technical failures for these two usable mixed samples. |
| Mixed invoice with bank claims | REVIEW_REQUIRED | Bank references SOURCE_LOCATED_UNVERIFIED and BANK_DETAILS_UNVERIFIED. No BANK_DETAILS_MISMATCH. |
| Native verified matching bank details | READY_FOR_AP | Account and IFSC independently verified against native evidence and matched to the authoritative vendor master |
| Mixed document with independent native-page mismatch | BLOCKED | BANK_DETAILS_MISMATCH and DOCUMENT_CONTENT_UNVERIFIED. Native-page quotations independently supported. |
| Mixed overbilling | COMPLETED / BLOCKED | PO_BALANCE_EXCEEDED and document-content review both retained |
| Mixed exact duplicate | COMPLETED / BLOCKED | EXACT_DUPLICATE and document-content review both retained |
| SCAN_CONFLICT | COMPLETED / REVIEW_REQUIRED | Image source remains unverified and existing arithmetic discrepancy is retained |
| Missing PO with unresolved logo | COMPLETED / REVIEW_REQUIRED | Confirming PO-1042 resolves PO identity. Reassessment retains DOCUMENT_CONTENT_UNVERIFIED as primary instead of becoming Ready. |
| Corrupt PDF | PROCESSING_FAILED / INVALID_PDF | Sanitized failure with no decision and zero provider replies |
| Invalid JSON and entirely unusable reply | PROCESSING_FAILED / INVALID_RESPONSE | Sanitized failure with no financial decision |
| Uniform render with extractable prose | EMPTY_PDF | Existing before-extraction render rejection preserved |

The two mixed hard blocks retained the same outcomes under both previews. All valid mixed cases retained their document finding under both previews, including the PO-confirmed case's original context. Policy, source run JSON, stages, and authority rows were compared before and after, and restart uses a failing extractor sentinel. The separate pure test establishes that the integrity flag independently prevents Ready even when every field has native support.

## Historical database and browser

A regression test copies a populated SQLite database containing a legacy-shaped run and review action and verifies exact stored payloads, schema definitions and API history after reopening the copy. A separate localhost FastAPI process used a SQLite backup of the actual pre-phase demo database. All seven historical runs and two review histories loaded. Original JSON, billable authority, policy and populated schema rows remained identical in the copy. A new mixed notice persisted its flag, completed review, PDF and decision. A process restart loaded the identical new snapshot, PDF and historical actions with zero extractor invocations. The initial upload used one controlled extraction. The original runtime was opened read-only for the copy and comparison.

Chrome inspected the actual mixed record at 1440 and 390 px. Needs review, the document-content finding, owner, next action and PDF link were visible with no technical-failure or blocked banner and no horizontal overflow or JS errors. The existing QA suite passed 15 actual-data views and seven controlled states. Screenshots are in ignored tmp/phase06b2b1-mixed-1440.png and tmp/phase06b2b1-mixed-390.png.

## Runtime

The parser, routing, rendered limits, model selection, timeout and concurrency are byte-identical to the baseline. The rule reads one small tuple and contributes one finding. In a local microbenchmark on the same already inspected ordinary mixed payment notice, median elapsed per operation over seven batches of 1000 calls measured grounding at 72.16 µs before and 60.10 µs after, and deterministic evaluation at 301.75 µs before and 267.25 µs after. These comparisons are below 0.04 ms and do not establish a speedup. They measure comparable functions, excluding parser subprocess startup, inference, database and the former technical gate. No extra inference or dependency was introduced.

## Exact verification

| Command | Result |
|---|---|
| .venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests/test_mixed_document_review.py -q --basetemp tmp/pytest06b2b1-mixed --tb=short | 15 passed |
| .venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest06b2b1-full --tb=short | 354 passed in 80.87s, one existing Starlette deprecation warning |
| npm --prefix frontend test | 58 passed |
| npm --prefix frontend run typecheck | Passed |
| npm --prefix frontend run build | Passed |
| .venv/Scripts/python scripts/verify_manifests.py | 6 vendors, 7 POs, 3 billed invoices, 10 frozen cases |
| .venv/Scripts/python scripts/verify_git_hygiene.py | 11 exclusions, 8 unchanged fixture PDFs |
| .venv/Scripts/python -m pip check | No broken requirements |
| npm --prefix frontend audit | 0 reported vulnerabilities |
| .venv/Scripts/python tmp/phase06b2b1-runtime.py | Local API port 8009, real upload followed by process restart and immutable historical record check |
| node tmp/phase06b2b1-browser.mjs | Actual mixed Review at 1440 and 390 px, PDF and health HTTP 200 |
| node frontend/scripts/qa.mjs with AP_COMPASS_UI_URL=http://127.0.0.1:8009 | 15 views, 7 controlled states, no mutations or uncaught errors |
| .venv/Scripts/python tmp/phase06b2b1-bench.py | Archived base and current backend compared via PYTHONPATH, no provider |
| git diff --check | Passed |

Test-first run reproduced the product-level classification issue with the ordinary payment-terms notice. Three provider-schema assertions passed and the expected completed-state assertion failed on the base. Final runs have zero failures, skips or expected failures. **Zero live Gemini generations or metadata requests.**

## Review and checkpoint

The remaining false-positive behavior is conservative review of legitimate images whose significance cannot be established. The system does not claim a normal logo is material. Historical absence continues to indicate that this check was not recorded. The change uses the existing evidence states, decision engine, authority data, policy and human review paths. No schema migration or frontend redesign.

Branch codex/phase-06b2b1-mixed-review from 51b1a7fe07f85b2b32d4ec8c3753cf521b44bda9. Annotated checkpoint phase-06b2b1-mixed-review. Publication and clean-tree proof accompany the handoff. Stop at the Phase 6B.2B.1 gate.
