# Final automation quality report

Retain the patch. It recovers four Ready decisions in the controlled comparison, preserves every outcome among the 14 non-Ready targets, and passes the regression checks below.

## Root causes and changes

- **Gross payable.** The shared invoice-header patterns omitted `Current invoice amount due` and `Invoice amount due`. The same registry now recognizes those labels and `Gross payable`. Generic `Amount payable`, `Total payable` and `Total amount payable` need a preceding printed subtotal and tax in the same source region. The existing `Grand total` and `Invoice total` paths remain supported. The verifier still requires the claimed page, unique full source or cell association, exact Decimal amount and compatible printed denomination. Additional account and statement headings fence off generic payment terms. An explicit invoice payable restated in a summary can contribute to the contradiction check. Repeated identical amounts do not conflict across those sections.
- **DEMO-02 tax.** PyMuPDF found `Tax (18%)` with a right edge of 552.7 pt and `7,200.00` starting at 741.4 pt on the same row. The 188.7 pt gap exceeded the 185 pt limit. A wider tax gap now requires three consecutive two-cell summary rows with a labelled subtotal, tax and payable, matching left label and right amount alignment, and similar spacing. The tax amount is printed, with no computation or inferred provenance. An absent label, a misaligned amount or a competing source stays unverified.
- **DEMO-05 routing.** The INR 2,750 charge and unmatched item claim still yield `LINE_MAPPING_UNRESOLVED`. The line evidence does not independently establish the item code, so the owner remains AP. The mapping finding now asks AP to check the item code and charge description against the rendered invoice, request itemized details if unclear, and compare the charge with the intended PO. Independently verified out-of-scope items still route to Procurement for authorization, amendment or correction. Only the AP finding text changed.

## Controlled comparison

The pre-edit run used F.3 at `181c4eba2f06e4d1016edea9be52e583ab104436`. Both runs used the same 12 sealed Blind V2 replies, six replies reconstructed from the original held-out source annotations, and eight sealed demo replies. The local `tmp/quality/replay.py` harness used the existing Layer B upload, bounded parser, evidence grounder, evaluator, persistence and restart checks. It passed each original wire payload through the production schema. Each case used a disposable database and document directory. Every case completed on both sides, and the saved snapshot and PDF were checked on reopen. This comparison measures controlled extraction and downstream decisions. It provides no live Gemini accuracy measurement.

| Set | Executed each side | Expected decisions matched | Ready targets cleared | Unnecessary Review | False Ready on non-Ready targets | Native-verified references |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Blind V2 | 12/12 | 6/12 → 9/12 | 0/6 → 3/6 | 6/6 → 3/6 | 0/6 → 0/6 | 95/166 → 105/166 |
| Original H01–H06 | 6/6 | 3/6 → 3/6 | 0/3 → 0/3 | 3/3 → 3/3 | 0/3 → 0/3 | 23/88 → 23/88 |
| Demo pack | 8/8 | 7/8 → 8/8 | 2/3 → 3/3 | 1/3 → 0/3 | 0/5 → 0/5 | 78/109 → 79/109 |
| Total | 26/26 | 16/26 → 20/26 | 2/12 → 6/12 | 10/12 → 6/12 | 0/14 → 0/14 | 196/363 → 207/363 |

Both sides had 0/26 technical failures. Critical field comparison results were identical for all 26 cases. The evidence counts use all persisted references, including missing references. Expected decisions are the frozen decision categories, with evidence Review acceptable for the raster targets.

| Case | Expected | Before → after | Evidence or control after |
| --- | --- | --- | --- |
| V2-01 | Ready | Review → Ready | Gross verified |
| V2-02 | Ready | Review → Ready | Gross verified |
| V2-03 | Ready | Review → Review | Gross verified. Line identity and amounts remain unverified |
| V2-04 | Ready | Review → Review | Gross verified. Line identity and amounts remain unverified |
| V2-05 | Ready | Review → Review | Gross verified. Both lines remain unverified |
| V2-06 | Ready | Review → Ready | Gross verified |
| V2-07 | Review | Review → Review | Gross verified. Unmapped charge and unverified line evidence retain AP ownership |
| V2-08 | Blocked | Blocked → Blocked | Tax and gross verified. PO balance, quantity and line balance controls still Block |
| V2-09 | Blocked | Blocked → Blocked | Gross verified. Exact duplicate still Blocks |
| V2-10 | Review | Review → Review | The sealed reply supplies no gross because the document contradicts itself. Synthetic tests also check a reply that selects one printed value |
| V2-11 | Review | Review → Review | Image-only. Zero native-verified references |
| V2-12 | Review | Review → Review | Mixed PDF. `DOCUMENT_CONTENT_UNVERIFIED` retained |
| H01 | Ready | Review → Review | Supplier association still unverified |
| H02 | Ready | Review → Review | PO, net and line support still insufficient |
| H03 | Ready | Review → Review | Currency and invoice amounts still unverified |
| H04 | Review | Review → Review | Unmapped charge and source Review retained, AP |
| H05 | Review | Review → Review | Image-only. Zero native-verified references |
| H06 | Review | Review → Review | Mixed PDF. `DOCUMENT_CONTENT_UNVERIFIED` retained |
| DEMO-01 | Ready | Ready → Ready | All 13 references native-verified |
| DEMO-02 | Ready | Review → Ready | Printed INR 7,200.00 tax verified. All 13 references native-verified |
| DEMO-03 | Ready | Ready → Ready | All 13 references native-verified |
| DEMO-04 | Review | Review → Review | Missing printed PO and incomplete evidence |
| DEMO-05 | Review | Review → Review | `SOURCE_EVIDENCE_MISSING` and `LINE_MAPPING_UNRESOLVED`, AP |
| DEMO-06 | Review | Review → Review | Scan source Review retained |
| DEMO-07 | Blocked | Blocked → Blocked | PO balance, quantity and line balance controls retained, Procurement |
| DEMO-08 | Blocked | Blocked → Blocked | `EXACT_DUPLICATE` retained, AP |

The compared PDF and wire response hashes matched per case. Trusted persisted authority matched `f6e95512f3e71d59bf512c1afc861e69587c3bbf40a9400c0f6c04739d02bf31` before and after. The seed file SHA-256 is `66be24c67f8869e05b997273659fd9ba59d23000ea08a0ed17afda520bffcbed`. Local result artifacts are `tmp/quality/before.json` (SHA-256 `bfc8d8cb50c48184dda656439cab3270c2d4261c7acacd114ab2425b5131398a`) and `tmp/quality/confirmed-after.json` (SHA-256 `94c7a24105fed8f2423e2c8ab8e0057dec44d4772019c0dda2208c921bada3fa`). These outputs are separate from all frozen results.

## Ordinary upload path and limits

The ordinary upload route validates capacity, multipart size, type and PDF signature. By default the app uses `extract_runtime_pdf`, which sends accepted input through bounded inspection and the configured Gemini provider. This path has no eight-file hash allowlist. The rehearsal provider selects a sealed reply by hash as a TEST_ONLY restriction. In a separate disposable smoke test, an independent PDF outside that allowlist reached the default Gemini adapter, returned upload HTTP 202 and completed Ready using one local SDK substitute call. No external Gemini requests were made.

This patch does not cover ambiguous tables, unsupported supplier and PO associations, unlabelled tax or arbitrary account-summary layouts. It did not recover the remaining six Ready targets in the compared sets. Raster routes still require conservative source review. The existing rehearsal databases and F.3 UI were left intact.

## Regression

- Full backend suite via `python -m pytest backend/tests -q` (557 passed, one Starlette deprecation warning). This includes 45 synthetic payable and tax tests, exact Decimal and currency checks, contradiction rejection, omitted-line checks, raster provenance, human review, policy preview and private-demo regressions.
- Against F.3, the original focused pre-fix payable test sweep had 15 failures and 26 passes. A separate run of the finalized wide-tax tests against F.3 had one failure for aligned printed tax and passed both negative controls.
- Frontend via `npm --prefix frontend test` (69/69), `npm --prefix frontend run typecheck` and `npm --prefix frontend run build`.
- `python scripts/verify_manifests.py`, `python -m pip check` and `git diff --check` passed.
- Git comparison against F.3 showed no changes under frontend, data, evaluation results, original fixtures, AI provider, API or public contracts.
