# POST-REMEDIATION REGRESSION COMPARISON — NOT A NEW UNSEEN BASELINE

Phase 6B.2C.4 used production commit `9c2e795a3090f340696e6aaf9be65cde45d3d33f`, annotated checkpoint `phase-06b2c3-grounding-remediation`. The task branch is `codex/phase-06b2c4-postfix-validation`. This phase measures the shipped verifier and finance engine. It changes no production code, scoring rules, source annotations, or fixture expectations. The previously observed independent documents are a regression comparison.

The exact remediation commit and tag were confirmed on a clean tree before the complete backend, original runner, frontend and integrity checks. The additive invocation was sealed at `085b716e6084512c73f586353300920a1d632b88`. It reuses the original scorer, allows separate result storage, records allowlisted per-generation observations and checks a fresh app startup against each disposable database. A separate callback diagnoses source associations without retaining raw responses or changing evidence. The 16 offline submissions were sealed at `4a526ace7caed981917c57d1aafed280c25b7f95` before any genuine provider request.

## Source and history integrity

| Frozen input | SHA-256 |
|---|---|
| Golden development registry | `b8397f5f6b58fcc8f46b264ebd589e111555497b32b80e14e9936f01d8fbb353` |
| LF-normalized authority seed | `66be24c67f8869e05b997273659fd9ba59d23000ea08a0ed17afda520bffcbed` |
| Typed sorted authority fingerprint | `f6e95512f3e71d59bf512c1afc861e69587c3bbf40a9400c0f6c04739d02bf31` |
| Supplied ZIP | `f3467c2ab7cdf687b1a646d4ae21668d6f88808b1c5ee4911c4dc1f2329880b7` |
| Supplied held-out oracle | `30e8850f67dec06662d7fc1843ab0600e01ccebb4a4a704db8cbbbca2ae0ca73` |
| Private registered cases | `100534567bcecdacf2303fbe87b8db260fb6c9138aa693fc586b34c4540e5255` |
| Private source annotations | `358c92130fc959d4e6372758dfaf7aa87e0ec48c04bfe64514f788c15de1e369` |
| H01 PDF | `82262342ed0de702381412f87fcc3333f6099c0dac4cd3eb358b797fa104b330` |
| H02 PDF | `16fcc3764310043973c89a4c117d3b45e5650cb4552a93a847af8bbcb1cc51f5` |
| H03 PDF | `0ed5a8835288020e0234e62a05b7108238925b5f1c9d4546bcfbbfd198e61865` |
| H04 PDF | `2bb35df19fd389e57ed70349024a751af914f43d4021dc999d758bdd0fc20999` |
| H05 PDF | `09c8869740b33d578174da706354f2932ee7b509de37066ada876a615fa031ff` |
| H06 PDF | `2111f612c15cca25e84c0e3308d216556a1ca769cb809782b0542f2f39b1f2e7` |
| Original development A | `d88367a59def4dac27b2cf850ff4898b67bc3e701f5468b19726dbf4fb474e1c` |
| Original development B | `0c6ca257a51a5300b49154976e2398b88053f0cd85f9268fcf6db7b4d449476f` |
| Original held-out B | `323e77d7d49ab7b22c61f04dbd9a34abd669a1883b80ce5548b270fe8e50470d` |
| Original held-out C | `da27bddd54ba6109373853b766e41aee4e36e2b7adb328bfe43c02cace28c8ac` |

The invocation revalidated the original archive against all nine imported members in the ignored local directory, then verified the six registered PDF hashes, case paths, input sizes, and expected authority reconciliation. It reused the original import bytes. Procurement policy was v1 at 2%. Only the separate PRICE_3PCT preview used 5%. The benchmark runs each submission with a new SQLite database and document directory. A second app startup checked exact result and review-history JSON, PDF bytes, and the authority fingerprint. An extractor sentinel verified zero extraction on restart. No original operational run, audited decision, PO or billed record was opened for modification.

## Controlled Layer B

All **10/10 eligible development** and **6/6 held-out** PDFs executed. The [offline comparison](POSTFIX_V1_OFFLINE_COMPARISON.md) provides per-case before/after outcomes, precise evidence gaps, authorities, and all score denominators. The development case `STATEMENT_PRIOR_BALANCE` still needs Review. Its ₹4,720 gross now verifies, but unit price and line net remain unsupported. The development unauthorized-line finding now independently routes to Procurement. H04 detects the same scope issue but still routes the finding to AP because its extra item-code claim has no independent source verification. H05 and H06 remain conservative Review with zero native attestations.

The benign security suite exercised competing totals and identities, wrong-row values, repeated item claims, customer-account versus current totals, non-native page restrictions, mixed integrity flags, and hard-block precedence. No bypass document was prepared. The validation used the unchanged application and actual source-supported controlled replies. See the compared results for where conservative source insufficiency still delays an otherwise financially valid invoice.

## Genuine Layer C

The configured `gemini-3.5-flash-lite` ran alone, sequentially, through the production provider, application upload/persistence path and ordinary two-attempt limit. The validator would start an invoice only if the shared budget could accommodate both attempts. There were **8 generations, including 4 retries, across 4 of the 6 preselected submissions**. No model discovery calls, escalation, reruns, or additional provider configuration were used.

| Order | Case and target | Attempts in order | Observed result | ASGI upload to terminal GET |
|---:|---|---|---|---:|
| 1 | H04, Review and scope finding | `INVALID_RESPONSE`, HTTP 503 | Terminal `PROCESSING_FAILED` / `PROVIDER_UNAVAILABLE`. No persisted extraction, financial finding, owner or decision. | 23,222.544 ms |
| 2 | OVERBILLED_PARTIAL, Block and both hard findings | HTTP 504, HTTP 503 | Terminal `PROCESSING_FAILED` / `PROVIDER_UNAVAILABLE`. No live evidence of financial outcome or hard-control execution. | 30,255.531 ms |
| 3 | H01, Ready if supported | HTTP 504, valid reply | `COMPLETED / REVIEW_REQUIRED`, unnecessary Review against Ready target. `PO_MATCH_CONFIRMED` and `SOURCE_EVIDENCE_MISSING`, AP with source verification and vendor clarification. | 57,731.669 ms |
| 4 | H05, conservative source Review | HTTP 503, HTTP 503 | Terminal `PROCESSING_FAILED` / `PROVIDER_UNAVAILABLE`. No live evidence refs or business decision. | 29,207.501 ms |
| 5 | H03, statement | 0 | Not Executed, budget exhausted. | — |
| 6 | H06, mixed | 0 | Not Executed, budget exhausted. | — |

H01 retained **11/11 critical fields**, with ₹12,000 net, ₹2,160 tax and ₹14,160 gross. Its quantity 12, ₹1,000 unit price and ₹12,000 line net matched. All **13/13 labelled present fields** including optional fields matched. No wrong, missing or hallucinated field was observed in its persisted extraction. Net, tax and gross are native verified. Seller, invoice number/date, PO and currency and the item's code, description, quantity, unit price and line net are source-located unverified. In particular, invoice number/date, PO and currency quotes differ from the frozen source-span formatting and fail independent label/value support in the actual verifier. The seller and row relationships remain unsupported even with correctly transcribed values. The strict v1 score was **5/15**, including two correct absence judgments. This describes the one completed invoice with actual field comparisons.

Six gateway errors occurred across the eight generations. H04's schema or adapter rejection is captured as the sanitized `INVALID_RESPONSE` category. No more specific content-level cause was persisted. Per-generation usage was present for 2/8 attempts, including H04's rejected response (613 input, 1,507 output, 2,120 total) and H01's valid response (562 input, 1,112 output, 1,674 total). **Reported subtotal: 1,175 input and 2,619 output tokens across 2/8 generations**. Remaining usage was unavailable, not zero. Persisted invoice aggregate usage is unavailable for all four submissions because each had at least one generation with unknown token counts. No billed cost or price observation was available. Total measured latency was 140,417.245 ms across four submissions.

| Live metric | Development post-fix | Held-out historical → post-fix |
|---|---:|---:|
| Executed / eligible | 1/1 | 2/4 → 3/5 |
| Terminal technical failures / executed | 1/1 | 0/2 → 2/3 |
| Exact critical fields | 0/0 | 22/22 → 11/11 |
| Missing fields / labelled present | 0/0 | 0/26 → 0/13 |
| Hallucinated fields / labelled absent | 0/0 | 0/4 → 0/2 |
| Correct v1 evidence judgments | 0/0 | 5/30 → 5/15 |
| Exact decisions | 0/1 | 0/2 → 0/3 |
| False Ready / non-Ready targets, v1 executed denominator | 0/1 | 0/0 → 0/2 |
| Unnecessary Review / Ready targets | 0/0 | 2/2 → 1/1 |
| Required finding recall | 0/2 | 0/0 → 0/2 |
| Owner match | 0/0 | 0/0 → 0/2 |
| Next-action match | 0/0 | 0/0 → 0/2 |
| Live generations / executed | 2/1 | 4/2 → 6/3 |
| Aggregate ASGI latency / measured submissions | 30,255.531 ms/1 | 57,855.304 ms/2 → 110,161.714 ms/3 |

The live cohorts differ. H01 is the only completed common case. It remained in Review, with 0 → 3 native refs and 11/11 exact critical fields in both phases. H03 was previously unnecessarily reviewed and was not re-executed here. The historical development benchmark included no genuine Layer C submission.

**There were zero completed live non-Ready-target submissions.** The frozen v1 denominators include the three failed non-Ready targets as executed. The corresponding completed-only false-ready denominator is 0/0 and offers no live assurance. No unearned native attestation or false Ready was observed in the controlled submissions, the sole live completion, or the benign regressions. H04 scope and overbilling precedence each have controlled evidence, including actual overbilling authority and the 6-versus-5 quantity check. Their genuine live financial outcomes remain unverified. The report records provider and adapter reliability as a release-review concern. It does not recommend treating failure as a successful Review or Block.

## Verification and result seal

| Command | Observed result |
|---|---|
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q -rx --basetemp tmp/pytest06b2c4-backend --tb=short` | 422 passed in 98.33 s. Includes 26 benign source layout tests. No failures, skips or XFAILs. One existing Starlette deprecation warning. Local asyncio loopback allowed. |
| `.venv/Scripts/python -m pytest evaluation/test_benchmark_v1.py -q --basetemp tmp/pytest06b2c4-runner` | Original 19 passed on the exact clean remediation checkpoint. The clean-worktree guard remained in force. |
| `.venv/Scripts/python -m pytest evaluation/test_benchmark_v1.py evaluation/test_postfix_v1.py -q --basetemp tmp/pytest06b2c4-harness` | 25 passed, including 6 new harness cases. |
| `npm --prefix frontend test` | 58 passed in 3 files. |
| `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` | Passed. Build transformed 1,754 modules. |
| `.venv/Scripts/python scripts/verify_manifests.py` and `.venv/Scripts/python scripts/verify_git_hygiene.py` | Passed. Six vendors, seven POs, three billed records, ten original scenarios, 11 exclusions and ten byte-identical tracked fixture PDFs. |
| `.venv/Scripts/python -m pip check` and `npm --prefix frontend ls --depth=0` | Passed. |
| `.venv/Scripts/python evaluation/postfix_v1.py --archive C:/Users/Asus/Downloads/AP_COMPASS_HELDOUT_V1.zip --output tmp/phase06b2c4-postfix` | 16 offline submissions and 3 separate workflow rows. Fresh startup and authority checks passed. |
| Same invocation with `--allow-live`, on the same sealed output root | 4 submissions, 8 actual generations. Reports recorded all exclusions and provider errors. Restarts made zero additional calls. |
| Final Draft 2020-12 schema validation, frozen metric recomputation and independent generation reconciliation | All four report files validated. Verified 16 offline and 4 live diagnostic observations, the exact live case order, 8 counted generations, no trust flags, and all original private and historical hashes. |
| Protected paths Git diff against `9c2e795a3090f340696e6aaf9be65cde45d3d33f` | Backend, frontend, all tracked fixtures, all data and the scorer unchanged. |

| New artifact in `evaluation/results/postfix-v1/` | SHA-256 |
|---|---|
| `development-b.json` | `abff41ff7fded28ad445d41bf23fc4d6e937295ca487ecdc2162db63d32d66d2` |
| `heldout-b.json` | `092f73cc7a9cef06c38ded348a44e3a391c7b21f4798a1b98a82f34ffce9596b` |
| `offline-diagnostics.json` | `afbc8f4e906540fe43ee6ebaf3acb2d845669843a478bc7c8f8fa2c9e05f747c` |
| `development-c.json` | `174780376548ad9ac571de636c6fa585939e19a1e5bb2484cffda0468bd7438f` |
| `heldout-c.json` | `6f98e110d6097d567f307edbd2451d417351d874588408f614484f4e60331c4b` |
| `live-diagnostics.json` | `c6e36ce48e0dfc532e1601e2b43323c920d889410ace4817e26247d5ac332bf4` |

## Gate

**POST-FIX VALIDATION COMPLETE — READY FOR RELEASE REVIEW.** The offline sweep and authorized live sample ran in order, artifacts and oracles are frozen, and known measured weaknesses remain explicit. Provider reliability, unresolved native row grounding and live hard-control coverage still need release review. This validation phase ends here.
