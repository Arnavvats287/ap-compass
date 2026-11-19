# Phase 6B.2C.1 — Golden dataset preparation

## Scope and provenance

Verified base `64bf8695b34e2125a8a240f8e1f233dbd745ce88`, tag `phase-06b2b1-mixed-review`. Branch `codex/phase-06b2c1-golden-dataset`. Production backend and frontend, shared contracts, original PDFs, seed, workflow and historical target manifests are byte-unchanged. No live calls or held-out access. The registry, generator, tests and evaluation artifacts are preparation for a separately authorized evaluation.

| Group | Entries | Submission scope | Frozen PDFs |
|---|---:|---|---:|
| A — Baseline | 10 | All original business targets, unchanged | 7 |
| B — Human workflow | 2 | `MISSING_PO_VALID` plus the original `AMBIGUOUS_PO` reused from A | 2, of which one is shared with A |
| C — Business scenarios | 2 | `SCOPE_UNAUTHORIZED_LINE` and `STATEMENT_PRIOR_BALANCE` | 2 |
| Deduplicated total | 14 registry entries | 13 unique invoice submissions and two separate human actions | 10 |

`BANK_CHANGED`, `INJECTION`, and `UNKNOWN_VENDOR` lack frozen PDFs and are eligible for trusted facts only. F1–F3 remain three separately referenced specification-only targets outside the submission denominator. No new results are claimed for the exact historical probes. The existing guard tests in the complete backend suite continue to cover ordinary supplementary cases.

## New business cases and document evidence

| Case | Independent authority and arithmetic | PDF evidence |
|---|---|---|
| `SCOPE_UNAUTHORIZED_LINE` | Meridian, `PO-1042`. INR 200,000 authorized less 120,000 billed leaves 80,000. Authorized `MC-CLOUD-01`: 8 × 5,000 = 40,000. Unmatched `MC-MIGRATION-99`: 1 × 17,500 = 17,500. Net 57,500 + GST 10,350 = gross 67,850. | 1 page, 2,333 bytes, native text, SHA-256 `ed66508191fd0b9cea3f49e82647c107953531e18e7b98ea8d302764f3f5d29e` |
| `STATEMENT_PRIOR_BALANCE` | Orion, `PO-6001`, `OR-SUPPLY-01`: 4 × 1,000 = 4,000. Net 4,000 + GST 720 = current gross 4,720. Prior 10,500 + current 4,720 = account balance 15,220. | 1 page, 2,395 bytes, native text, SHA-256 `c4ad939cfd4ab32fbef2520254f5109ada7c116e9a721927fbcb8009633903e7` |

ReportLab 4.4.5 generated both PDFs with invariant serialization. Regeneration into a temporary folder yielded identical bytes. PyMuPDF 1.26.6 returned selectable text for the date, vendor, item details, invoice totals and distinct account summary. The actual bounded parser routed both PDFs as `native_text`. Both Poppler PNG renders were visually inspected at 110 DPI. Line items are separated in the Meridian PDF and current charges are visibly separate from the Orion account summary. No clipping, overlap or unreadable glyphs were observed. Poppler printed fallback configuration messages for Symbol and ArialUnicode and returned success for both pages. Local render outputs are under `tmp/pdfs/phase06b2c1/`.

The data registry SHA-256 is `b8397f5f6b58fcc8f46b264ebd589e111555497b32b80e14e9936f01d8fbb353`. Tests verify ten PDF hashes, page counts, routes and all four source-manifest hash references. Dates, authority, exact Decimal line arithmetic, invoice totals and separate account balances are validated without model output. The evaluated version pins policy v1 at 2%, and the baseline price case retains its separate 5% variant.

## Trusted-facts observations

Every one of the 13 unique submitted fact sets matched the expected deterministic outcome and required findings. These are typed-fact results. They carry no claim of extraction or measured PDF grounding.

| Case or track | Actual deterministic result |
|---|---|
| `HAPPY_CLEAN`, `HAPPY_PARTIAL` | Ready, `PO_MATCH_CONFIRMED` |
| `AMBIGUOUS_PO` | Review, `PO_AMBIGUOUS` and `PO_REFERENCE_MISSING` |
| `OVERBILLED_PARTIAL` | Blocked, balance and quantity ceilings |
| `DUPLICATE_REISSUED` | Blocked, `EXACT_DUPLICATE` |
| `SCAN_CONFLICT` | Review, `TOTAL_RECONCILIATION_FAILED` |
| `BANK_CHANGED` | Blocked, `BANK_DETAILS_MISMATCH` |
| `INJECTION` | Blocked, `PO_BALANCE_EXCEEDED` from typed financial facts. PDF behavior remains unmeasured. |
| `UNKNOWN_VENDOR` | Review, `VENDOR_UNVERIFIED` |
| `PRICE_3PCT` | Review, `PRICE_VARIANCE` at 2%. Ready under the separate 5% variant. |
| `MISSING_PO_VALID` | Review, `PO_REFERENCE_MISSING` |
| `SCOPE_UNAUTHORIZED_LINE` | Review, `LINE_MAPPING_UNRESOLVED` points only to line 2. No balance, quantity or header reconciliation findings. |
| `STATEMENT_PRIOR_BALANCE` | Ready on independently specified trusted current-invoice facts. The supplied gross for this check was INR 4,720. |
| `MISSING_PO_VALID` / confirm `PO-1042` | Ready. Source context unchanged. |
| `AMBIGUOUS_PO` / confirm `PO-1042` | Review, missing facts and mapping unresolved. PO ambiguity and missing-reference findings clear. Source context unchanged. |

**Two known oracle mismatches.** The current `LINE_MAPPING_UNRESOLVED` finding uses default owner `AP` and requests item codes or itemized scope and PO verification. The frozen business oracle requires Procurement and an authorization check with an appropriate amendment or corrected invoice. The two assertions are strict expected failures, so the gap remains visible in the suite. The decision, line identification and required finding match. The preparation gate permits documenting this gap for architectural review and does not certify it as fixed. The typed-facts Ready result for the statement does not establish that the split layout will ground correctly through a provider pipeline. A live Review on otherwise correct facts will be reported against the frozen Ready target.

## Evaluation handoff

Layer A trusted-facts preparation ran. Dedicated Layer B PDF integration scoring and Layer C live inference remain unexecuted. The existing parser and integration regression tests ran as part of verification. `GOLDEN_BENCHMARK_DESIGN.md` defines eligibility, evidence semantics, first-attempt counting, technical-failure scoring, metrics and exclusions. `evaluation/result_v1.schema.json` and `evaluation/REPORT_TEMPLATE.md` preserve numerators and denominators and separate submission, confirmation and policy tracks. `evaluation/heldout/` reserves a future namespace. Codex did not generate, import or inspect independent data.

## Actual verification

| Command | Result |
|---|---|
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests/test_golden_dataset.py -q -rx --basetemp tmp/pytest06b2c1-prep --tb=short` | 40 passed, 2 expected failures for scope routing and action |
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q -rx --basetemp tmp/pytest06b2c1-verified --tb=short` | 394 passed, 2 expected failures, 0 unexpected failures, one existing Starlette deprecation warning. 88.83 s. |
| `npm --prefix frontend test` | 58 passed across three files |
| `npm --prefix frontend run typecheck` | Passed |
| `npm --prefix frontend run build` | Passed, 1,754 modules |
| `.venv/Scripts/python scripts/verify_manifests.py` | 6 vendors, 7 POs, 3 billed records, 10 original cases |
| `.venv/Scripts/python scripts/generate_golden_fixtures.py --output tmp/pdfs/phase06b2c1/replica` | Regenerated both Group C assets with identical SHA-256 values |
| `pdftoppm -r 110 -png -singlefile <PDF> <output-prefix>` | Rendered and visually inspected both Group C PDFs. Actual bounded parser and PyMuPDF checks passed within the dataset suite. |
| `.venv/Scripts/python scripts/verify_git_hygiene.py` | 11 exclusions and ten byte-identical indexed PDFs |
| `.venv/Scripts/python -m pip check` | No broken requirements |
| `npm --prefix frontend ls --depth=0` | Passed with no missing top-level packages |
| `git diff --cached --check` | Passed |

The initial sandboxed backend run stalled before any assertion in the first existing dashboard test. The isolated test's 15-second faulthandler trace showed Windows asyncio waiting in local socket-pair initialization. The authorized rerun outside the loopback restriction completed the same offline suite with controlled providers and no live inference.

**Preparation gate: PASS.** The freeze retains both known scope-finding gaps for architectural review. Measurements for the dedicated controlled PDF layer and the live layer remain pending separate authorization. Stop at this checkpoint.
