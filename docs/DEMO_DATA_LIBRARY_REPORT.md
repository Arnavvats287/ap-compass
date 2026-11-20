# AP Compass demo data library

**The curated library passed local verification for private HTTPS deployment.** Seven original, byte-identical synthetic invoice PDFs are downloadable from the launch page. The full historical packs remain private. No remote deployment or push occurred.

Implementation commit **`96c4608a32a755f2d682c067999628fac7f52f2a`** includes approved dashboard and workspace changes through its parent `59faa36a20b9020a0abace7a6c4acf1b2d9c1e72`. The extraction and finance baseline `3a836ae3fb53a25ae1f72099e4b666374d00a09b` remains in history. The application uses the ordinary Gemini adapter for all submitted samples. Opening the library or downloading a file makes no generation request.

## Inventory and publication checks

Opened the four supplied ZIPs from local downloads, checked their CRCs and original manifest hashes, and rendered all **35 pages across 33 PDFs**. The first three archive manifests pinned each member's size and hash. The held-out oracle pinned its six PDF hashes. The current seed matched the sealed seed SHA-256 `66be24c67f8869e05b997273659fd9ba59d23000ea08a0ed17afda520bffcbed` where the archives specified it. Each oracle vendor/PO relationship matched current authority. The review explicitly retained the demo's missing PO, the deliberately degraded scan reference, and the seeded duplicate rather than treating them as corrupt files.

All files were within the 8 MiB and 10-page limits. There were **33 distinct PDF byte hashes**. The original demo's `08-northstar-supplies.pdf` and Blind V2's `northstar-archive-copy-0318.pdf` intentionally share the same invoice identity `NS-2026-0318` with different bytes. Visual review and PDF inspection found no credentials, bank details, embedded files, links, actions or forms in the seven selected PDFs. Brightpath's Final Blind 7 invoice prints a synthetic remittance block and was withheld. Nothing was edited inside a PDF.

| Source pack | Inventory | Published | Original ZIP SHA-256 |
|---|---:|---:|---|
| Final Blind 7 | 7 | 6 | `a28b125dc34e4749c30a91d873c1ad7d7e69b71fdd1efffa0d71eb07c91de81e` |
| Original workflow | 8 | 1 | `84682d8913463b93e7881e4ac8c21b827a0ce870d822735a12e45b4dfe4b3af6` |
| Blind V2 | 12 | 0 | `557efb36cc28d4e5e5503f40cdd0c30160aee4e55f4d738c18fe464f6493e2dd` |
| Original held-out | 6 | 0 | `f3467c2ab7cdf687b1a646d4ae21668d6f88808b1c5ee4911c4dc1f2329880b7` |

## Published assets

Open [Explore demo data on localhost](http://127.0.0.1:8077/) or [download the collection ZIP](http://127.0.0.1:8077/demo-data/ap-compass-demo-invoices.zip) using the local demo login. The ZIP SHA-256 is `1f5b09e382db609f5e5636410b3cba4970301776bfce2385174e3a8749717232`. It contains exactly the seven PDFs below. The UI gives educational scenario labels and labels verification by release class. A prior result is a recorded observation, and the next upload is evaluated with its own generated facts, policy and stored context.

Class **A** means genuine Gemini completion on the release extraction backend. **B** means genuine completion on an older checkpoint. **C** means controlled execution only, including any separately reported failed live attempts. **D** is reserved for untested files or a reproducible unresolved technical failure. Completion and agreement with the expected business decision are scored separately.

| PDF | Class and exact observation | SHA-256 |
|---|---|---|
| [NS-26-5942.pdf](http://127.0.0.1:8077/demo-data/NS-26-5942.pdf) | A · Northstar clean invoice. Ready, 13/13 native references at `3a836ae`. | `8103e41c05d939beb18467a82fd99d87d50d306579134ba252b9a248ba3c7186` |
| [KLG-2611-876.pdf](http://127.0.0.1:8077/demo-data/KLG-2611-876.pdf) | A · Kaveri unauthorized surcharge. Review with the verified unmapped item finding at `3a836ae`. | `2aa415f106cdbe6216bd8bb59126650a38d8f8c492a2933125c346e152fa3746` |
| [AS-2611-632.pdf](http://127.0.0.1:8077/demo-data/AS-2611-632.pdf) | B · Aster overrun. Blocked for PO net, line net and quantity at `e1ce3fe`. | `230016e9c6a655f754eb5b990a7204a64470dced3c14b5c22bd51efdfd2e992f` |
| [MCL-26-4681.pdf](http://127.0.0.1:8077/demo-data/MCL-26-4681.pdf) | A · Meridian image-only scan. Source Review at `3a836ae`, with zero native references. | `c9e8fb3a416124a7ca93586a01291bd05dc28b7609cf4c4c4ba94b7c61c64452` |
| [MCL-26-4573.pdf](http://127.0.0.1:8077/demo-data/MCL-26-4573.pdf) | B · Meridian 3% unit-rate variance. At `86c087e`, the recorded 2% run returned Review with `PRICE_VARIANCE`. A 5% preview removed that finding while source uncertainty still required Review. | `881163cc762412625f15f956d276d1f2559fba84c590172e036fed80a8656963` |
| [08-northstar-supplies.pdf](http://127.0.0.1:8077/demo-data/08-northstar-supplies.pdf) | A · Previously billed invoice. Blocked with `EXACT_DUPLICATE` at `0051044`. | `7b35c99758e70703dc23c80fc1b3eb4683c1ae3499e83cc9ea333258586a8005` |
| [OOP-2611-617.pdf](http://127.0.0.1:8077/demo-data/OOP-2611-617.pdf) | B · Orion clean invoice. Ready, 13/13 native references at `e1ce3fe`. | `6355af5604fa1d4d2b2a0099b86e5ec9fb77817359d012aaa8e846b268c9aaee` |

## Newly authorized live checks

Used exactly **three genuine `gemini-3.5-flash-lite` generations**. Each original PDF was hashed, submitted to the real upload API, processed at a persisted 2% policy through the default adapter and evaluator, and reopened with its original bytes and snapshot after restart. Each had a fresh isolated SQLite/PDF store. All three uploads returned HTTP 202 and all three Gemini replies completed. No retries or escalation. The oracle never entered the application or provider request. The code for extraction, verification, authority, and financial decisions matched the release baseline.

| Source and file | Actual vs. intended | Critical facts | Native evidence | Time | Review or Block finding and action |
|---|---|---:|---:|---:|---|
| Original demo · `08-northstar-supplies.pdf` | Blocked vs. Blocked | 13/13 | 1/13 | 3,776 ms | `EXACT_DUPLICATE` plus `SOURCE_EVIDENCE_MISSING`. AP to hold and reconcile the reissued invoice with the billed record. Published. |
| Blind V2 · `northstar-dispatch-071.pdf` | Review vs. Ready | 13/13 | 1/13 | 3,588 ms | `SOURCE_EVIDENCE_MISSING`. AP to verify the source and clarify with the supplier. Withheld. |
| Original held-out · `H02_REPEATED_ITEM_CODE.pdf` | Review vs. Ready | 16/18 strict | 2/18 | 5,031 ms | `SOURCE_EVIDENCE_MISSING`. AP to verify the source. Both rows and all monetary facts matched. Both descriptions included the correct printed service period and item code in addition to the expected description. Withheld. |

The initial local receipt comparator used oracle field names for quantity and line net. A separate offline comparison against the original saved snapshots corrected the mapping to canonical `qty` and `net`. The corrected counts above leave the original observations intact and required zero additional model calls.

## Remaining 26 files

| Files | Class | Publication decision |
|---|---|---|
| Final Blind 7 · `BP-26-7845.pdf` | B | Earlier completed Review with source and scope issues against a Ready target; contains a synthetic remittance block. |
| Original demo · `01-meridian-cloud.pdf`, `02-kaveri-freight.pdf`, `03-orion-office.pdf`, `04-meridian-support.pdf`, `05-brightpath-advisory.pdf`, `06-kaveri-scan.pdf`, `07-aster-managed-services.pdf` | C | Controlled rehearsal only. Needs live validation before publication. |
| Blind V2 · `northstar-dispatch-071.pdf` | A | Completed but missed the Ready target in the live check above. |
| Blind V2 · `meridian-hosting-146.pdf`, `kaveri-freight-228.pdf`, `brightpath-advisory-034.pdf`, `meridian-service-periods-151.pdf`, `northstar-invoice-statement-082.pdf`, `orion-supplies-055.pdf`, `aster-service-097.pdf`, `northstar-archive-copy-0318.pdf`, `brightpath-advisory-049.pdf`, `orion-scanned-061.pdf`, `kaveri-freight-241.pdf` | C | Controlled-only evidence. Needs live validation before publication. |
| Original held-out · `H01_CLEAN_INDEPENDENT.pdf`, `H03_STATEMENT_BALANCE.pdf` | B | Older genuine completions both required unnecessary Review. Needs fresh live validation before publication. |
| Original held-out · `H02_REPEATED_ITEM_CODE.pdf` | A | Completed but missed the Ready target in the live check above. |
| Original held-out · `H04_UNAUTHORIZED_SCOPE.pdf`, `H05_IMAGE_ONLY_SCAN.pdf` | C | Older controlled completions; older live attempts ended in provider errors with no financial decision. Needs successful live validation. |
| Original held-out · `H06_MIXED_RASTER_TERMS.pdf` | C | Controlled-only evidence. Needs live validation before publication. |

## Build and release checks

- Frontend test suite 69 passed, typecheck and production build passed. The focused backend intake, private demo, finance projection, dashboard and Excel suite passed 33 tests. Intake tests persist both recorded policies and verify that changing the intake choice does not rewrite older runs.
- Desktop and mobile Chrome clicked all seven PDF links and the ZIP and matched downloaded bytes. The Escape and close controls returned focus. Reduced motion, nested-route delivery and selecting downloaded PDFs at 5% in the existing composer passed. That browser check stopped before submission.
- A fresh Docker build served all eight files byte-for-byte over authenticated loopback HTTPS. Unauthenticated requests returned 401. Oracle, manifest and withheld sample requests returned 404. The runtime preserved a separately accepted PDF and its technical failure snapshot across restart with the Gemini key deliberately absent.
- The only build-context exception is the curated ZIP. Vite serves the explicit static catalogue on the app's existing authenticated origin. The published directory contains no evaluation artifacts, credentials or uploaded documents. Run `python scripts/verify_demo_library.py` to pin all hashes and enforce exact archive membership. Git hygiene and manifest checks passed.

The hosted HTTPS URL is pending deployment authorization and confirmation of the deployment SHA. Use the private-demo configuration and then repeat the download and intake smoke against the actual host.
