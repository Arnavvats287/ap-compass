# Phase 6B.2C.2 — Frozen baseline and independent PDF benchmark

## Provenance and execution order

Production behavior throughout the benchmark is from the verified base `0e7c421573023ce0c3da2433aed0409d5bedfa7a`, tag `phase-06b2c1-golden-dataset`. The runner was sealed at `c37296aa61c36fa6d255c710a2152d37be642be6`. Development A and B first observations were committed at `eecc189` before opening the archive. The held-out importer validates identity, authority, arithmetic, filenames, byte limits and hashes before running. Its evaluation-only source sidecar supports actual printed dates such as `07 Nov 2026` while the wire value is ISO. That input adaptation was committed at `0c3838610f36769aec1c28af0fd2756c7be7ebcc`, before any held-out inference. The scoring logic and frozen development records stayed fixed. The first held-out offline results were sealed at `4c2c342` before any live generation.

| Input | SHA-256 |
|---|---|
| Development registry | `b8397f5f6b58fcc8f46b264ebd589e111555497b32b80e14e9936f01d8fbb353` |
| Authority seed, LF-normalized | `66be24c67f8869e05b997273659fd9ba59d23000ea08a0ed17afda520bffcbed` |
| Typed sorted authority fingerprint | `f6e95512f3e71d59bf512c1afc861e69587c3bbf40a9400c0f6c04739d02bf31` |
| Original held-out archive | `f3467c2ab7cdf687b1a646d4ae21668d6f88808b1c5ee4911c4dc1f2329880b7` |
| Original held-out oracle | `30e8850f67dec06662d7fc1843ab0600e01ccebb4a4a704db8cbbbca2ae0ca73` |
| Private derived registry | `100534567bcecdacf2303fbe87b8db260fb6c9138aa693fc586b34c4540e5255` |
| Private source annotations | `358c92130fc959d4e6372758dfaf7aa87e0ec48c04bfe64514f788c15de1e369` |

| Held-out input | Bytes | Printed route | PDF SHA-256 |
|---|---:|---|---|
| H01 | 63,405 | Native | `82262342ed0de702381412f87fcc3333f6099c0dac4cd3eb358b797fa104b330` |
| H02 | 45,279 | Native | `16fcc3764310043973c89a4c117d3b45e5650cb4552a93a847af8bbcb1cc51f5` |
| H03 | 91,791 | Native | `0ed5a8835288020e0234e62a05b7108238925b5f1c9d4546bcfbbfd198e61865` |
| H04 | 63,596 | Native | `2bb35df19fd389e57ed70349024a751af914f43d4021dc999d758bdd0fc20999` |
| H05 | 349,176 | Image only | `09c8869740b33d578174da706354f2932ee7b509de37066ada876a615fa031ff` |
| H06 | 102,604 | Native and raster | `2111f612c15cca25e84c0e3308d216556a1ca769cb809782b0542f2f39b1f2e7` |

The six independent originals and supplied oracle stay in the ignored `tmp/evaluation-heldout-v1/original/` directory. All six PDF digests matched the supplied oracle. All were one page under the 8 MiB limit. Poppler renders were inspected for all six, and PyMuPDF confirmed an empty text layer for H05 and both text and an embedded image for H06. The annotations use native source spans in PDF content-stream order for H01–H04 and H06, and a visual transcription for H05. Header/column cell adjacency and individual line identity were checked before creating the controlled wire replies. H02's two rows and service periods were kept separate. No evidence states or financial decisions appear in controlled replies.

All recorded runs used policy v1 at 2% except the separate 5% preview. Each submitted PDF used its own disposable SQLite database and document store. The runner compared persisted snapshots, re-served PDF hashes and typed authority hashes, including after human actions. The existing demo databases, audited histories and billable records were untouched. Result JSON contains sanitized comparisons, states, allowed error codes, application-generated actions and decimal observations. It excludes original archive members, raw provider responses, quotes, credentials and bank values.

## Method and scoring boundaries

- Development A scores 13 distinct submissions and separately records two confirmation actions and one policy variant. Development B scores all 10 eligible PDFs over the same 13 registered submissions. `BANK_CHANGED`, `INJECTION`, and `UNKNOWN_VENDOR` are facts-only and ineligible for PDF scoring. Historical F1–F3 remain specification-only and are excluded.
- Held-out B scores six first attempts. H01–H03 are Ready targets when independently supported, so conservative Review counts as unnecessary review against the target. H02's external oracle explicitly permits a safe fallback if its repeated evidence is unresolved. H05 and H06 are financially eligible but have source-review targets under the current evidence policy. The original distinction remains in the external oracle. No PDF changes or target changes were made after observing results.
- Controlled field comparisons score the persisted adapter output. Printed but unverified optional line net is counted missing when the application clears it, independently of critical-field scoring. Service periods and payment terms have no wire slot. Statements and settlement status have no supported field and are not fabricated. Scoring uses exact Decimal values and respects printed row order, including repeated item codes. Bank fields are scored for labelled absence or correctness without serializing values.
- Evidence scoring requires the expected state, matching fact, page and annotated span for present fields. Labelled absence is included. A quote that does not contain the full annotated span gets no credit, even if shorter true text may exist elsewhere. This conservative criterion affects live evidence judgments. Controlled span order and the parser's sorted text can also differ. These observations measure the defined source pipeline, not exhaustive source verifiability across every possible quote. For mixed single-page H06, a located unverified claim is the expected current-policy state, while the independently printed financial text remains distinguishable from the raster terms.
- Latency is wall-clock time from in-process ASGI POST start to receipt of terminal persisted GET. SQLite setup, preflight, source re-download and review actions are outside that interval. Layer B reports zero live generations and separately records calls to the controlled provider. Unknown token usage and zero-denominator metrics are unavailable. The small synthetic sample does not estimate population accuracy.

## Metrics

| Metric | Development A | Development B | Held-out B | Held-out C |
|---|---:|---:|---:|---:|
| Eligible unique submissions / registered | 13/13 | 10/13 | 6/6 | 4/6 |
| Executed submissions / eligible | 13/13 | 10/10 | 6/6 | 2/4 |
| Technical failures / executed PDF submissions | — | 0/10 | 0/6 | 0/2 |
| Exact critical fields / labelled present critical fields | — | 108/108 | 72/72 | 22/22 |
| Missing fields / labelled present fields, including optional labelled fields | — | 0/128 | 2/88 | 0/26 |
| Hallucinated fields / labelled absent slots | — | 0/7 | 0/12 | 0/4 |
| Correct evidence judgments / tagged judgments | — | 122/135 | 37/100 | 5/30 |
| Exact decisions / executed | 13/13 | 9/10 | 3/6 | 0/2 |
| False Ready / executed non-Ready targets | 0/10 | 0/7 | 0/3 | 0/0, unavailable |
| Unnecessary Review / executed Ready targets | 0/3 | 1/3 | 3/3 | 2/2 |
| Required findings observed / labelled requirements | 15/15 | 12/12 | 3/3 | 0/0, unavailable |
| Owner match / labelled cases | 0/1 | 0/1 | 2/3 | 0/0, unavailable |
| Next-action match / labelled cases | 0/1 | 0/1 | 1/3 | 0/0, unavailable |
| Live generations / executed submissions with recorded counts | 0/13 | 0/10 | 0/6 | 4/2 |
| Input tokens / submissions reporting aggregate input usage | — | — | — | 0/0, unavailable |
| Output tokens / submissions reporting aggregate output usage | — | — | — | 0/0, unavailable |
| Total latency ms / measured submissions | — | 6,761.755/10 | 3,469.522/6 | 57,855.304/2 |

No unexpected extra lines were seen. All controlled PDFs had an actual extracted record. For C, field and evidence coverage is the two executed PDFs only. `0/0` provides no evidence about live false-ready risk on a non-Ready target. Workflow actions and the alternate policy did not add invoice submissions. The labelled owner/action checks use the intended finding when present, even when source Review is the application's primary finding.

## Development first observations

`N` means `NATIVE_VERIFIED`, `U` means `SOURCE_LOCATED_UNVERIFIED`, and `M` means `MISSING`. The counts below include present and empty fields when the application supplied an evidence ref. All eligible B runs completed and retained all labelled facts.

| Submission | Layer A | Layer B classification and evidence | Key reason / observed owner and action |
|---|---|---|---|
| HAPPY_CLEAN | Correct Ready | Correct Ready, 13 N | `PO_MATCH_CONFIRMED`. Continue to AP review. |
| HAPPY_PARTIAL | Correct Ready | Correct Ready, 13 N | `PO_MATCH_CONFIRMED`. Continue to AP review. |
| AMBIGUOUS_PO | Correct Review | Correct Review, 7 N / 1 U / 5 M | `PO_REFERENCE_MISSING`, `PO_AMBIGUOUS`. AP to ask the vendor for and verify the PO. |
| OVERBILLED_PARTIAL | Correct Block | Correct Block, 13 N | `PO_BALANCE_EXCEEDED`, `PO_QUANTITY_EXCEEDED`, `PO_LINE_BALANCE_EXCEEDED`. Procurement to get a correction or authorized amendment. |
| DUPLICATE_REISSUED | Correct Block | Correct Block, 13 N | `EXACT_DUPLICATE`. AP to hold and reconcile against the original. |
| SCAN_CONFLICT | Correct Review | Correct Review, 12 U / 1 M | `SOURCE_EVIDENCE_MISSING`, `TOTAL_RECONCILIATION_FAILED`. AP to verify source and seek clarification. |
| BANK_CHANGED | Correct Block | Ineligible | Typed facts trigger `BANK_DETAILS_MISMATCH`. AP to hold and verify via known contact. |
| INJECTION | Correct Block | Ineligible | Typed facts trigger PO overbilling. PDF handling of the injection scenario was not measured. |
| UNKNOWN_VENDOR | Correct Review | Ineligible | Typed facts trigger `VENDOR_UNVERIFIED`. Procurement to verify the approved supplier record. |
| PRICE_3PCT | Correct Review | Correct Review, 13 N | `PRICE_VARIANCE`. Procurement to confirm agreed unit price or request a correction. |
| MISSING_PO_VALID | Correct Review | Correct Review, 12 N / 1 M | `PO_REFERENCE_MISSING`. AP to ask for and verify the PO. |
| SCOPE_UNAUTHORIZED_LINE | Correct Review | Correct Review, 10 N / 8 U | `SOURCE_EVIDENCE_MISSING`, plus `LINE_MAPPING_UNRESOLVED`. AP routes source clarification. The scope finding itself is also AP with generic item clarification, against Procurement and authorization/amendment/correction targets. |
| STATEMENT_PRIOR_BALANCE | Correct Ready | Unnecessary Review, 9 N / 4 U | `SOURCE_EVIDENCE_MISSING`. Correct ₹4,720 gross was retained. The current total quote overlaps the repeated summary text and some line refs also remain unverified. AP to verify source. |

Separate actions passed in A and B. `AMBIGUOUS_PO` confirmation produced Correct Review with missing line facts and no PO ambiguity. `MISSING_PO_VALID` confirmation produced Correct Ready. The 5% `PRICE_3PCT` preview produced Correct Ready and left its 2% record untouched. Layer B verified stored history for both confirmation actions and original snapshot immutability for all three actions.

## Independent Layer B first observations

Every case completed and matched the expected route. H01–H04 had all labelled facts present. H05 and H06 retained all critical facts and cleared one printed but unverified optional line net each. There were no bank mismatch findings for H06.

| Case | Decision classification | Evidence and critical fact coverage | Primary reason / observed owner and action |
|---|---|---|---|
| H01 | Unnecessary Review | 11/11 critical. 0 N / 9 U / 4 M. | `SOURCE_EVIDENCE_MISSING`. AP to verify source and request clarification. |
| H02 | Unnecessary Review | 14/14 critical. The two `MC-CLOUD-01` rows retained quantities 4 and 6 and separate line nets. 0 N / 4 U / 14 M. | `SOURCE_EVIDENCE_MISSING`. AP to verify source. No scope finding. Repeated anchors and table layout limit localization. |
| H03 | Unnecessary Review | 11/11 critical. ₹9,440 current gross retained separately from ₹15,340 combined balance. 1 N / 7 U / 5 M. | `SOURCE_EVIDENCE_MISSING`. AP to verify source. The prior settlement status was never established. |
| H04 | Correct Review | 14/14 critical. ₹40,000 hosting and ₹17,500 migration retained separately; ₹57,500 net fits aggregate headroom. 0 N / 6 U / 12 M. | Primary `SOURCE_EVIDENCE_MISSING` with required `LINE_MAPPING_UNRESOLVED`. Scope finding owner is AP and action is generic, against the Procurement target. |
| H05 | Correct Review | 11/11 critical. ₹30,000 net, ₹5,400 tax, ₹35,400 gross. 0 N / 13 U. Printed ₹30,000 line net withheld. | `SOURCE_EVIDENCE_MISSING`. AP matches the role target. Generic source/vendor clarification falls short of scan-to-PO reconciliation or a supplier-issued native copy. |
| H06 | Correct Review | 11/11 critical. ₹20,000 net, ₹3,600 tax, ₹23,600 gross. 0 N / 13 U. Printed ₹20,000 line net withheld. | `DOCUMENT_CONTENT_UNVERIFIED` with `SOURCE_EVIDENCE_MISSING`. Accounts Payable to inspect the complete rendered invoice and confirm relevant charges or instructions. The raster card contains ordinary Net 30 terms. |

## Independent Layer C first observations

`gemini-3.5-flash-lite` was the only model used, via the fixed-endpoint production provider and the real upload, parser, grounding, persistence and finance path. Stronger-model escalation was disabled. The live report names `4c2c342`'s code state. Both executed native PDFs used their first invoice submission. Each had one allowed automatic provider retry, for a total of four generations. No cases were resubmitted.

| Case | Generations and technical outcome | Extraction and evidence | Classification / owner and action | Latency |
|---|---|---|---|---:|
| H01 | 2. HTTP 503 `PROVIDER_UNAVAILABLE`, then valid reply. Final `COMPLETED`. | 11/11 critical fields. ₹14,160 gross. 0 N / 13 U. | Unnecessary Review, `SOURCE_EVIDENCE_MISSING`. AP to verify the source and request clarification. | 18,331.342 ms |
| H03 | 2. HTTP 504 `PROVIDER_UNAVAILABLE`, then valid reply. Final `COMPLETED`. | 11/11 critical fields. ₹9,440 gross. 1 N / 12 U. | Unnecessary Review, `SOURCE_EVIDENCE_MISSING`. AP to verify the source and request clarification. | 39,523.962 ms |
| H04 | 0. Budget consumed. | — | Not Executed | — |
| H05 | 0. Budget consumed. | — | Not Executed | — |
| H02 | 0. Offline-only by design. | — | Ineligible | — |
| H06 | 0. Offline-only by design. | — | Ineligible | — |

The persisted API aggregate token fields were null on both runs. Production aggregates usage only when every generation attempt provides a count for that field. This benchmark did not retain separate token metadata for the successful retries, so partial token usage is unavailable. Neither transient gateway error was counted as a terminal technical failure. No stronger-model, metadata, or further generation requests were made.

## Ranked remediation proposals for review

1. **Localize native label/value pairs and table cells.** H01 and H03 matched all 22 live critical fields, but the application verified only one present field across both invoices. Controlled H01–H04 also reproduced layout-related misses. The current verifier relies on a unique normalized quote in sorted page text and flattened standalone labelled lines. Preserve source ordering and introduce narrow geometry-aware source localization for adjacent labels and row cells. Use new development cases and require exact value, page, scope and row support before granting verification. This is the largest observed clean-invoice review burden.
2. **Disambiguate repeated row and summary occurrences.** H02 retained both authorized lines but localized neither reliably. The current verifier requires one item-code anchor per page. Separately, the development Statement case retains ₹4,720 but cannot verify a quote whose text also occurs inside a repeated summary label. Use page/row occurrence and section context to attribute each invoice fact, with explicit controls for identical repetition and truly conflicting totals. Preserve caution when a layout has multiple equally plausible sources.
3. **Route proven unauthorized scope to Procurement.** Both scope fixtures emitted the required mapping finding, with AP ownership and generic clarification. Use a narrow distinction between a present item code outside a matched PO and an invoice missing item identity. Give the former Procurement ownership and the authorization/amendment/correction action while keeping current source findings and decision severity. Review primary-finding ordering separately so source risk remains visible.
4. **Improve AP guidance for scanned and mixed evidence.** H05 safely reviewed but provided generic AP follow-up. Direct it toward comparison with PO and prior billing or obtaining a native supplier copy. H05 and H06 cleared printed optional line nets when unverified. If displaying those becomes a requirement, preserve them as explicitly untrusted source observations outside binding amount fields. Keep image-only evidence below native verification.
5. **Preserve per-generation benchmark telemetry.** The two gateway errors consumed half the live budget, and both persisted aggregate token fields are unavailable. For future independently authorized runs, persist allowlisted per-generation usage and status as observed. Preserve the first baseline and continue to count provider calls across retries.

## Demonstration candidates

1. `HAPPY_CLEAN` for the complete Ready path with verified evidence.
2. `OVERBILLED_PARTIAL` for the remaining PO balance and quantity checks with Procurement routing.
3. `MISSING_PO_VALID` for Review to audited PO confirmation and Ready without changing source history.
4. `PRICE_3PCT` for a 2% Review and a separate 5% Ready preview with the original decision intact.

The four paths passed the controlled benchmark. No video, deployment, production fixes or new scenarios were created.

## Verification and reproducibility

Run from the repository root with the existing development environment. Install the runner-only schema validator with `.venv/Scripts/python -m pip install -r evaluation/requirements.txt`. Native annotation claims use the attached layout and page order. Keep local normalized registry and annotations under the ignored evaluation directory, and keep origin hashes with each result. The runner refuses an existing output directory and journals each row with exclusive creation before accumulating its schema-validated report. Fresh reruns require new output directories and separate results. The default command is offline unless Layer C and `--allow-live` are explicitly selected together.

| Verification command or action | Actual result |
|---|---|
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q -rx --basetemp tmp/pytest06b2c2-full --tb=short` | 394 passed, 2 known expected failures, one existing Starlette warning, 85.22 s. Local asyncio loopback allowed. |
| `.venv/Scripts/python -m pytest evaluation/test_benchmark_v1.py -q --basetemp tmp/pytest-bench-final` | 19 passed. Paths, ZIP boundary, duplicate IDs, hash checks, unsupported inputs, source normalization, first-row preservation and JSON Schema validation. |
| `npm --prefix frontend test` | 58 passed across 3 files. |
| `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` | Both passed. Build transformed 1,754 modules. |
| `.venv/Scripts/python scripts/verify_manifests.py` and `.venv/Scripts/python scripts/verify_git_hygiene.py` | Passed, including ten original indexed fixture PDFs and 11 runtime/secret exclusions. |
| `.venv/Scripts/python -m pip check` and `npm --prefix frontend ls --depth=0` | Both passed. |
| Draft 2020-12 validation and metric recomputation over all four frozen reports | Passed. 16/16/6/6 rows, unique case/track/attempt tuples, all stored counters recomputed and all four actual live calls reconciled. |
| SHA-256 and byte comparison of all local originals to the same archive after benchmark | All nine members, including six PDF files and the original oracle, matched byte-for-byte. Archive hash matched unchanged. |
| `git diff --exit-code phase-06b2c1-golden-dataset -- backend/app frontend tests/fixtures data` | Passed. No production or frozen input changes. |

Layer A and B development commands used `.venv/Scripts/python evaluation/benchmark_v1.py --layer A --output tmp/benchmark-dev/first-a` and the corresponding `--layer B --output tmp/benchmark-dev/first-b`. Held-out registration used `.venv/Scripts/python evaluation/import_heldout_v1.py --private-dir tmp/evaluation-heldout-v1` after a validated copy of the ZIP members. Held-out B and C used the following argument pattern. For C, use `--layer C --allow-live --output tmp/evaluation-heldout-v1/first-c` only with a new approved generation budget.

```powershell
.venv/Scripts/python evaluation/benchmark_v1.py --layer B --split heldout `
  --manifest tmp/evaluation-heldout-v1/registry.json `
  --asset-root tmp/evaluation-heldout-v1/original `
  --annotations tmp/evaluation-heldout-v1/annotations.json `
  --oracle-sha 30e8850f67dec06662d7fc1843ab0600e01ccebb4a4a704db8cbbbca2ae0ca73 `
  --output tmp/evaluation-heldout-v1/first-b
```

| Frozen report in `evaluation/results/v1/` | SHA-256 |
|---|---|
| `development-a.json` | `d88367a59def4dac27b2cf850ff4898b67bc3e701f5468b19726dbf4fb474e1c` |
| `development-b.json` | `0c6ca257a51a5300b49154976e2398b88053f0cd85f9268fcf6db7b4d449476f` |
| `heldout-b.json` | `323e77d7d49ab7b22c61f04dbd9a34abd669a1883b80ce5548b270fe8e50470d` |
| `heldout-c.json` | `da27bddd54ba6109373853b766e41aee4e36e2b7adb328bfe43c02cace28c8ac` |

**Gate: BENCHMARK COMPLETE — READY FOR REMEDIATION REVIEW.** Both offline sweeps ran, the authorized live budget was fully used, and exclusions and observed weaknesses remain explicit. Stop at evaluation review.
