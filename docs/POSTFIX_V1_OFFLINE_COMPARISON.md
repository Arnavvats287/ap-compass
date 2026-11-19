# POST-REMEDIATION REGRESSION COMPARISON — NOT A NEW UNSEEN BASELINE

Layer B processed the same PDF bytes and controlled wire claims through the real upload, isolated parser, layout checks, evidence grounder, finance evaluator, SQLite and document storage. The existing scoring code and source annotations were held fixed. Controlled exact-match measurements confirm that the pipeline retained supplied values. They are separate from genuine model observations.

## Before and after

| Metric | Development before → after | Held-out before → after |
|---|---:|---:|
| Eligible / registered | 10/13 → 10/13 | 6/6 → 6/6 |
| Executed / eligible | 10/10 → 10/10 | 6/6 → 6/6 |
| Exact critical fields | 108/108 → 108/108 | 72/72 → 72/72 |
| Missing fields / labelled present fields | 0/128 → 0/128 | 2/88 → 2/88 |
| Hallucinated fields / labelled absent slots | 0/7 → 0/7 | 0/12 → 0/12 |
| Correct v1 evidence judgments | 122/135 → 123/135 | 37/100 → 54/100 |
| Exact decisions | 9/10 → 9/10 | 3/6 → 3/6 |
| Unnecessary Review / Ready targets | 1/3 → 1/3 | 3/3 → 3/3 |
| False Ready / non-Ready targets | 0/7 → 0/7 | 0/3 → 0/3 |
| Required finding recall | 12/12 → 12/12 | 3/3 → 3/3 |
| Owner matches | 0/1 → 1/1 | 2/3 → 2/3 |
| Next-action matches | 0/1 → 1/1 | 1/3 → 2/3 |
| Technical failure / executed | 0/10 → 0/10 | 0/6 → 0/6 |
| Real generations / observed submissions | 0/10 → 0/10 | 0/6 → 0/6 |
| Aggregate measured latency / measured submissions | 6,761.755 ms/10 → 5,159.273 ms/10 | 3,469.522 ms/6 → 3,412.389 ms/6 |

Latency is from the ASGI upload starting to retrieval of the terminal persisted run. The subsequent diagnostic inspection, original document readback and restart verification are outside that interval. These small same-input timing observations provide limited evidence about latency under other load or infrastructure.

## Development PDFs

`N`, `U` and `M` are native verified, source located but unverified, and missing evidence. Counts exclude slots for which no evidence ref was emitted. All ten eligible submissions completed and retained all labelled critical and optional fields. Facts-only `BANK_CHANGED`, `INJECTION` and `UNKNOWN_VENDOR` remain ineligible for Layer B. The historical F1–F3 specifications remain unexecuted.

| Case | Before → after decision | Post-fix evidence and control |
|---|---|---|
| HAPPY_CLEAN | Ready → Ready | 13 N. PO matched. |
| HAPPY_PARTIAL | Ready → Ready | 13 N. PO matched. |
| AMBIGUOUS_PO | Review → Review | 7 N / 1 U / 5 M. Missing reference and ambiguity. |
| OVERBILLED_PARTIAL | Blocked → Blocked | 13 N. PO balance, quantity, and line-balance checks. ₹30,000 net against ₹25,000 remaining, and 6 units against 5. |
| DUPLICATE_REISSUED | Blocked → Blocked | 13 N. `EXACT_DUPLICATE`. |
| SCAN_CONFLICT | Review → Review | 0 N / 12 U / 1 M. `TOTAL_RECONCILIATION_FAILED`, ₹3,600 discrepancy, plus unverified source. |
| PRICE_3PCT | Review → Review | 13 N. `PRICE_VARIANCE` at the frozen 2% policy. |
| MISSING_PO_VALID | Review → Review | 12 N / 1 M. PO reference missing. |
| SCOPE_UNAUTHORIZED_LINE | Review → Review | 10 N / 8 U. Both codes are verified. The independent `LINE_MAPPING_UNRESOLVED` finding routes to Procurement with authorization and an approved amendment or corrected supplier invoice. Primary source Review is still owned by AP. |
| STATEMENT_PRIOR_BALANCE | Unnecessary Review → Unnecessary Review | 9 N / 4 U → 10 N / 3 U. The ₹4,720 current gross upgraded to N. `lines[0].unit_price_net` and `lines[0].net` are still mandatory limiting evidence. Description is also unverified. The ₹15,220 account balance is separate. |

The original PO actions and preview were exercised in their own tracks. Confirming the valid benchmark PO left AMBIGUOUS_PO in Review and moved the reassessed MISSING_PO_VALID to Ready. The 5% PRICE_3PCT preview returned Ready without changing the stored 2% Review. Restart preserved stored action history, original decisions, evidence, documents and seeded authority.

## Independent PDFs

| Case | Before → after decision | Native verification change and exact remaining limitations |
|---|---|---|
| H01 | Unnecessary Review → Unnecessary Review | **0 → 7 N**. Invoice number/date, PO, currency, net, tax and gross independently verified. Seller label association and the item's code, quantity, unit price, net and description remain U. ₹14,160 gross retained. |
| H02 | Unnecessary Review → Unnecessary Review | **0 → 4 N**. Invoice number, currency, tax and gross verified. Seller/date claims and both five-field item spans are M in the application's reading order. PO reference and header net are U. Both printed item occurrences stay separate, with quantities 4 and 6 and net amounts ₹20,000 and ₹30,000. Neither row received verification or an unauthorized-item finding. |
| H03 | Unnecessary Review → Unnecessary Review | **1 → 4 N**. Seller, invoice number/date and PO verified. Currency, header net, tax and gross remain U. All five item slots remain M. Correct ₹9,440 current gross retained separately from ₹5,900 previous and ₹15,340 combined balance. No settlement status inferred. |
| H04 | Correct Review → Correct Review | **0 → 3 N**. Currency, net and tax verified. Seller and invoice-number locations and both native item spans remain M. Date, PO and gross remain U. ₹40,000 hosting and ₹17,500 extra migration each retained, ₹57,500 net. `LINE_MAPPING_UNRESOLVED` fired. Procurement routing remains unmet because `lines[1].item_code` is not source-verified. Its owner remains AP with source/item-code clarification. |
| H05 | Correct Review → Correct Review | **0 N → 0 N**. Scan route retained 13 U refs, including the withheld optional net claim. ₹30,000 net + ₹5,400 tax = ₹35,400 gross. `SOURCE_EVIDENCE_MISSING` remains, with improved AP scan/PO/billed-history and native-copy guidance. |
| H06 | Correct Review → Correct Review | **0 N → 0 N**. Mixed page retained 13 U refs and withheld optional net. ₹20,000 + ₹3,600 = ₹23,600. `RASTER_CONTENT_UNRESOLVED` and `DOCUMENT_CONTENT_UNVERIFIED` stayed present. No bank object or mismatch finding was produced. |

H05 and H06 account for the 2/88 missing optional fields after grounding. The adapter retained the amount claims in the source evidence but withheld the unverified line net from the authoritative extraction fields. No known-wrong, missing or hallucinated labelled field received `NATIVE_VERIFIED`, and no raster-page evidence received native verification. The per-field diagnostic artifacts separate a missing claim, a claim outside parser reading order, an unsupported label/cell relationship, an unsupported row and an intentionally conservative route. They leave the v1 exact-span score intact.
