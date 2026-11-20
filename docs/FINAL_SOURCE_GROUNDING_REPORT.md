# Final native source-grounding verification

Orion and Northstar moved from Review to Ready on an offline replay of the same saved Gemini facts and claims. Each improved from 1/13 to 13/13 independently verified references. The original Aster extraction remained Blocked. The offline pass made zero Gemini generations. The separately approved live validation then used exactly two attempts and passed both decision checks. The previous Aster PROVIDER_UNAVAILABLE is a separate live-provider observation.

## Diagnosis from the saved live claims and PDFs

I compared the persisted page, raw value, and quote with parser-owned native cells for each field. Both PDFs contained all 13 reported critical facts on page 1. Neither saved reply claimed a different quantity or another item's row. The observed failures were missing semantic associations, not missing printed facts or failed extraction arithmetic. Whitespace was incidental in both saved replies because most quotes were already exact bare values. The prior verifier expected particular labels, a labelled quote, or a complete table row.

| Field | Orion | Northstar |
|---|---|---|
| Supplier | Exact issuer heading already verified. | Exact issuer heading already verified. |
| Invoice number | The bare ID appears below a right-aligned INVOICE title. The existing No./Number alias did not recognize that placement. | The bare ID is below INVOICE in the metadata band. The old verifier expected Invoice No. or a labelled quote. |
| Invoice date | The correct date is under INVOICE DATE, separate from DUE DATE. The bare quote lacked the label expected by the verifier. | The correct date is under ISSUED, separate from DUE. ISSUED was not a recognized date label in that band. |
| PO reference | The correct value is under PURCHASE ORDER. Its quote contained the value alone. | PO reference and PO-2010 are adjacent cells. Its quote contained the value alone. |
| Currency | The quoted INR is printed below CURRENCY. The quote did not include the label. | The quoted SUBTOTAL (INR) really exists, and the payable also prints INR. There is no separate Currency field. The old verifier did not link the currency-qualified summary to the gross denomination. |
| Net | The model correctly quoted 17,000.00. That figure is printed both in the invoice subtotal and in the line net. Only the Subtotal cell pair establishes the header. | The correct 12,000.00 also occurs twice. The invoice subtotal is beneath SUBTOTAL (INR), in a three-column summary the old parser did not recognize. |
| Tax | The correct 3,060.00 is adjacent to GST (18%). The short quote omitted the GST label. | The correct 2,160.00 is below GST 18% (INR). Neither the label with its currency qualifier nor the three-column summary was recognized. |
| Gross | The correct INR 20,060.00 is paired with Amount due. The quote contained the amount and code without its label. | The correct INR 14,160.00 is below BALANCE DUE in the same net/tax/payable band. A generic Balance due label alone remains insufficient. |
| Description | Office supplies is the first charge cell. The old table reader required a dedicated item-code column. | Office chairs is the first cell under Item / stock code. The old reader did not recognize the combined description/code column. |
| Item code | The correct SKU is printed immediately below the description. The old reader did not associate the continuation cell with the charge. | The correct SKU is also immediately below its charge description. The saved bare quote is exact. |
| Quantity | Qty is explicit and 17 sits in that charge row. The missing table association prevented verification from the bare quote. | Chairs is the quantity column, identified by the adjacent Net / chair rate header. The old generic table did not recognize the column pair. |
| Unit price | The correct rate sits under Unit net (INR). The prior table did not recognize this charge shape or key the bare rate to the item. | The correct rate sits under Net / chair. The rate and quantity-column pair establishes the semantic role. |
| Line net | Line net (INR) belongs to the same charge row. The repeated subtotal magnitude is insufficient alone. | Extended net belongs to the charge row. Its repeated header subtotal magnitude is insufficient alone. |

No source quote, physical cell, or model value was edited in the replay inputs.

## Source-verification changes

- Added a bounded layout extension to the existing single-page native PyMuPDF path. It recognizes a combined description/item-code column with a closely aligned continuation SKU, explicit quantity and unit-rate columns, and an explicit line net. It requires a uniquely identified complete table with one-to-one matching for every extracted charge field. Invalid or extra printed rows, competing tables and indistinguishable duplicate rows fail closed.
- Added the adjacent metadata and qualified invoice summary associations shown above. A three-column summary needs explicit net and tax labels, coherent printed denominations, a matching code on gross and a supported preceding charge table. A standalone account balance cannot establish invoice gross. Supplementary pairs participate in the original inline, split and document-wide conflicts.
- An exact bare-cell quote is usable only with a uniquely associated source cell and matching extracted and raw facts. A quote aimed at a different role or field fails. Once independently established, the saved evidence text comes from the actual native cells. Numeric equality uses Decimal and source denomination checks. The code never fills missing model values, treats procurement amounts as document evidence, or promotes OCR or raster reads.
- Only backend/app/documents/stacked_layout.py, source_layout.py and evidence.py changed in this pass. Backend tests gained test_stacked_invoice_evidence.py. Gemini, wire schema, policies, duplicate and spending controls, UI, dashboard, export, and invoice history behavior stayed as they were.

## Offline results

| PDF and source | Native refs before → after | Decision before → after |
|---|---:|---|
| Orion, saved wire-verification run | 1/13 → 13/13 | Review → Ready |
| Northstar, saved wire-verification run | 1/13 → 13/13 | Review → Ready |
| Aster, original successful live extraction | 5/13 → 5/13 | Blocked → Blocked |

Aster had 2/13 native references when historically recorded. The already-present hybrid verifier produced 5/13 before this change on the same old claims. This change kept that evidence count and the original hard findings, PO_BALANCE_EXCEEDED, PO_QUANTITY_EXCEEDED and PO_LINE_BALANCE_EXCEEDED. The INR 30,000 net request was INR 5,000 above the remaining commitment. Six units were requested against five remaining. No saved decision was overwritten.

The 26 sealed controlled cases used unchanged input hashes and preserved their authority fingerprint. They retained six Ready, 16 Review and four Blocked, with 207/363 native references and **0/14 false Ready** on non-Ready targets. The eight-case demo remained 3 Ready / 3 Review / 2 Blocked. New synthetic checks include wrong row, wrong field and due-date quotes, same-value account quotes, competing gross and issue dates, duplicate summaries, wrong currency, omitted charge and missing SKU. An independently verified unauthorized charge stays Review and routes to Procurement. Older negative cases cover scans, duplicate invoice detection and unsupported or mixed evidence.

## Reproducibility and checks

- Backend pytest for stacked invoice evidence, source layout, source generalization, payable semantics, currency evidence, hybrid extraction, wire compatibility and finance engine: **274 passed**, including 12 new stacked-layout tests.
- Static seed and fixture manifest validation and Git whitespace check passed. No finance, API, database, authority or frozen benchmark files changed.
- Disposable outputs under tmp/hybrid: source-final-before.json SHA-256 52d173d19bb526a5b3e5dab92bca5609af83435b27e74b131ac86a3839e94e85, source-final-verified.json SHA-256 0dbe71f9ef7cedc5196978286d08f7826149bf329a0cdfeb48885e65fea82329, source-final-controlled-verified.json SHA-256 a915fccdc5faa92da99800312e7c0d0ba0a57b1b186b56607b45834b1073a021. The before replay disabled only the added layout extension, matching the saved Orion and Northstar counts and the pre-existing hybrid Aster count.
- The local backend checkpoint includes the earlier pending hybrid and wire-diagnostic backend changes already present at the start. It leaves the existing frontend edits in the worktree.

## Approved live validation

The test used backend checkpoint e1ce3fe4e13ac5ef825fa408a8bf4d738cb5419f, the frozen Orion and Aster PDFs, the normal production gemini-3.5-flash-lite adapter, and a new isolated SQLite and PDF store. Orion ran first. Both received HTTP 202, passed the wire schema and completed at the recorded 2% tolerance. Exactly two generations were attempted, with zero retries, provider errors, or escalation. Both uploaded PDFs matched their manifest hashes after reopening. Each decision was based on its own extraction. The historical Aster provider outage was not repeated.

| Invoice | Decision | Critical facts | Native evidence | Total processing |
|---|---|---:|---:|---:|
| Orion OOP-2611-617 | Ready | 13/13 | 13/13 | 3,692 ms |
| Aster AS-2611-632 | Blocked | 13/13 | 1/13 | 3,669 ms |

Orion independently grounded every reported critical field. Aster had 12 source-located but unverified references. Its separate hard findings still recorded PO_BALANCE_EXCEEDED, PO_QUANTITY_EXCEEDED and PO_LINE_BALANCE_EXCEEDED. Against the unchanged PO records, its INR 30,000.00 net exceeded INR 25,000.00 remaining by INR 5,000.00. Six units exceeded the five remaining by one. The run also retained SOURCE_EVIDENCE_MISSING. Two runs and zero review actions were stored in the isolated database.

The private observation hashes under tmp/source-grounding-live were 433a9187d7caca909b05019207dbbdf779cdf3edab97e7033474d1f2aa83a8e6 for Orion and 5a47ec304d6271e9e3bffd3f802926bd5c43ff41c73aa3d27739a41cf3454dcd for Aster.

## Scope

Both targeted live decision checks passed. This two-case sample does not establish general provider reliability or complete native evidence support for Aster-style invoice layouts. Unsupported native layouts, ambiguous documents, absent claims and raster evidence may still require Review. No production code, prior results, or existing data changed during this live validation. No deployment or push was made.
