# Phase 6B.2A document verification review

**REPRODUCTION INCOMPLETE — INVESTIGATION REQUIRED**

Reviewed checkpoint `96a0a2952d7454bd33b71073d9012554df17b3a9` on branch `codex/phase-06b2a-adversarial-repro`. The locally available 17-page independent repository audit was consulted for its findings. Its earlier probe claims are attributed to that audit, with no independent confirmation at this checkpoint.

The security scope permits source review, future safety criteria, and benign regression checks. Tailored adversarial PDFs, selective provider replies, and bypass execution were outside that scope. There are no adversarial fixture hashes, rendered captures, route observations, provider outputs, API decisions, or strict XFAILs for F1–F3. All three cases are **INCONCLUSIVE** for runtime reproduction on this checkpoint. This differs from **NOT REPRODUCED**, which requires an executed probe with a negative result.

| Case | Observed route | Observed grounding | Actual outcome | Safe target | Classification |
|---|---|---|---|---|---|
| F1, contradictory totals | Unmeasured | Unmeasured | Unmeasured | Review pending resolution | INCONCLUSIVE |
| F2, payment instructions in raster content | Unmeasured | Unmeasured | Unmeasured | Review pending independent verification | INCONCLUSIVE |
| F3, invisible source text | Unmeasured | Unmeasured | Unmeasured | Sanitized technical failure or conservative review | INCONCLUSIVE |
| Visible original HAPPY_CLEAN | native_text, one page | 13 NATIVE_VERIFIED | COMPLETED / READY_FOR_AP | Ready | SAFE POSITIVE CONTROL |
| Same totals repeated in a continuation summary | native_text, two pages | 13 NATIVE_VERIFIED | COMPLETED / READY_FOR_AP | Ready | SAFE POSITIVE CONTROL |
| Decorative raster image | native_text, one page | 13 NATIVE_VERIFIED | COMPLETED / READY_FOR_AP | Ready | SAFE POSITIVE CONTROL |

The positive controls use fresh temporary SQLite/document storage and a test-only provider. The actual API, parser subprocess, evidence grounder and finance evaluator executed. The existing clean Orion case is the basis of all three controls. The decorative raster is a solid-color swatch with no payment content and is not a Brightpath-specific result. No additional PDFs are checked in. The two variants regenerate in memory and are compared byte for byte during each test. Rendered nonblank content and raster object inventory were checked programmatically. No visual adversarial artifacts were produced.

| Control | Bytes | SHA-256 |
|---|---:|---|
| Existing HAPPY_CLEAN.pdf | 2238 | `9c27b5a97993716d72616a3b9565cf6fc3ee9f9c406646ad8f2e08972f308b3e` |
| Repeated summary | 2760 | `9371b9b8480352efb4baf230a4fc1d8e1da07384b0837a9bf134a1af99081975` |
| Decorative raster | 5647 | `2c16d5feb1a33c15dfc3302bad45faccbf178bf1623e3db70047462004bd3aba` |

## Source review

- **F1.** `ground_evidence()` resolves a claim to one cited page. `local_support()` validates field labels, quote uniqueness, and value coherence within that page. Neither performs a document-wide reconciliation of header totals. Thus claim verification alone cannot establish that totals represent the entire invoice. Identical continuation summaries should preserve eligibility.
- **F2.** `_parse_process.inspect()` uses a page-relative image size heuristic for routing readable pages. That measures geometry rather than whether an image contains payment instructions. Native routing provides text and no rendered page image to the provider. `ground_evidence()` checks native text and claims for omitted bank fields. The evaluator's `bank_instructions()` interprets a missing object as `BANK_DETAILS_NOT_PROVIDED`. These boundaries allow a material-content uncertainty to go unrepresented in the evaluation input. The benign swatch control establishes that an ordinary decorative image should remain eligible for Ready.
- **F3.** Native inspection accepts readable extracted text and does not render that route. `local_support()` establishes textual support and does not establish rendered visibility. A bounded rendering guard could reject fully unreadable pages, with more complex visibility cases requiring separate analysis. The genuinely visible native fixture should remain independently verifiable.

The production orchestration supplies grounded extraction and trusted authority to the deterministic evaluator. The provider schema has no independent evidence-state or business-outcome fields. No production modules, rules, human confirmation logic, shared contracts, frozen fixture expectations, or seed records were changed. The control tests verify authority and policy equality before and after each run. Existing demo history was untouched. Gemini generations and metadata requests were both zero.

## Verification

| Command | Result |
|---|---|
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest06b2a-baseline --tb=short` | 328 passed in 66.03s, 1 existing Starlette deprecation warning |
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests/test_document_positive_controls.py -q --basetemp tmp/pytest06b2a-controls --tb=short` | 3 passed in 3.63s |
| `npm --prefix frontend test` | 58 passed |
| `npm --prefix frontend run typecheck` | Passed |
| `npm --prefix frontend run build` | Passed |
| `.venv/Scripts/python scripts/verify_manifests.py` | 6 vendors, 7 POs, 3 billed records, 10 existing cases |
| `.venv/Scripts/python scripts/verify_git_hygiene.py` | 11 exclusions, 8 PDFs byte-safe |
| `.venv/Scripts/python -m pip check` | No broken requirements |
| `npm --prefix frontend audit` | 0 vulnerabilities reported |

Zero unexpected test failures or unexpected parser execution errors in the benign controls. The baseline suite includes intentional parser error cases. There were zero adversarial tests executed, zero confirmed runtime reproductions, zero expected failures, and three inconclusive findings. The JSON oracle stores only future safety criteria and explicitly leaves fixture identity and runtime results empty. Its outcomes are based on the requested safeguards independent of the benign results.
