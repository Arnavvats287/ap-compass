# Final independent review reconciliation

**Recommendation:** Use the verified local checkpoint for a controlled demo deployment. The evidence and financial safety gates passed offline, and the previous live Orion/Aster decisions replay exactly. Keep unfamiliar native and scan behavior qualified until the separate three-case live check. This review made zero Gemini calls, did not deploy, and did not record a video.

## Checkpoint and sources

Comparison started at 9adfb92, which records the pair of genuine live runs produced at backend checkpoint e1ce3fe4e13ac5ef825fa408a8bf4d738cb5419f. The live extraction, prompt, source association, strict compatibility checks and diagnostics were already tracked. Six previously verified frontend files were still local edits and would have been missing from a clean deployment checkout. The final commit includes those existing files unchanged from the starting worktree. It also includes the two narrow backend changes described below. The review did not edit the UI.

I reviewed the two attached architecture PDFs and the attached script as recommendations and experimental evidence. The attached hybrid and wire Markdown reports matched the workspace reports byte for byte. The reviews predate the latest Orion and Aster live results. Their observations about the historical schema failures remain historical, and their suggested call budgets did not authorize provider access for this task.

## Recommendation-by-recommendation disposition

| Recommendation | Classification and decision | Current source |
|---|---|---|
| Keep model interpretation separate from financial controls and use the existing pipeline | Already implemented and working. Gemini proposes facts, native grounding verifies what the document supports, and the evaluator resolves vendor authority, duplicate, and PO controls. | backend/app/ai/gemini.py, GeminiProvider.generate and extract_runtime_pdf. backend/app/documents/pipeline.py, extract_pdf. backend/app/domain/decisions.py, evaluate. |
| Normalize copied monetary presentation without float conversion | Demonstrably missing at baseline. The old decoder rejected correctly grouped printed strings. Fixed locally, bounded to parseable formatting with a compatible denomination, retaining the strict canonical width and scale checks. | backend/app/documents/schema.py, normalize_wire_amount, WireInvoice.normalize_money_presentation, and parse_response. backend/app/documents/consistency.py, AMOUNT and CURRENCIES. |
| Change model evidence-key shape, add indexed line hints, accept noncanonical leaf aliases, or discard invalid evidence claims | Already has strict wire-key validation, schema descriptions and safe rejection diagnostics. A rejected evidence-key family was not demonstrated in the historical payloads. Replacing the schema, guessing line aliases, or silently dropping provenance is unnecessary or unsafe for this checkpoint. | backend/app/documents/schema.py, SourceClaim, provider_schema, pattern_diagnostic, and log_wire_rejection. backend/app/ai/provider.py, SYSTEM_INSTRUCTION. |
| Make the verifier own source anchors, including split header fields and stacked rows | Already implemented and working for the demonstrated layouts. The current proof uses labelled, uniquely associated native cells and complete row mapping, even when a quote is a bare exact cell value. Keep the quote as a scoped input. Unsupported layouts still require Review. | backend/app/documents/evidence.py, ground_evidence, source_cell_proof, and stacked_row_proofs. backend/app/documents/source_layout.py, split_headers and table_rows. backend/app/documents/stacked_layout.py, invoice_metadata, stacked_charges, and currency_summary. |
| Repair unfamiliar layouts by ignoring quotes and approving presence, arithmetic, and PO role agreement | Unnecessary or unsafe. The attached comparison still accepted a wrong identity after its arithmetic and role gates. The real verifier refused all tested substitutions by retaining role and row binding. Keep arithmetic and procurement consistency in their existing checks. Declined the oldest-date shortcut, weaker field tiers, inferred or backfilled values, and bank checks based on seed equality alone. | backend/app/documents/consistency.py, disputed_headers. backend/app/documents/evidence.py, ground_evidence. backend/app/domain/evidence.py, source_evidence. |
| Add reason codes to explain why an individual source reference was rejected | Partially implemented. Review records the unresolved fields, and wire diagnostics name safe paths and constraint shapes. There is no per-reference NO_HIT or MULTI_HIT public contract. The current test showed no unsafe promotion that requires introducing that extra contract. | backend/app/domain/evidence.py, source_evidence. backend/app/documents/evidence.py, ground_evidence. backend/app/documents/schema.py, log_wire_rejection. |
| Distinguish provider status, timeout, and transport failures | Partially implemented. Provider mapping and per-attempt duration/HTTP status already exist in memory, but the normal worker previously omitted the status and timing from its failure log. Fixed the demonstrated gap by logging the safe status when available and total elapsed milliseconds. Run snapshots and provider behavior are unchanged. No raw response capture. A past PROVIDER_UNAVAILABLE run with missing HTTP telemetry cannot be retrospectively labelled 503, 504, or a timeout. | backend/app/ai/gemini.py, provider_error and GeminiProvider.generate. backend/app/documents/pipeline.py, extract_pdf. backend/app/orchestration/service.py, RunService.process. |
| Retry transient failure, increase timeout, change the model, or expand OCR/decode contracts | Unnecessary for the demonstrated defects. Retain one attempt on the production path and existing SDK settings. No model change, prompt revision, new OCR, schema expansion, extra date field, or removal of evidence claims. The published pricing and retry assumptions in the reviews were not used as measurements. | backend/app/ai/gemini.py, make_client and extract_runtime_pdf. backend/app/documents/inspection.py, inspect_pdf. |
| Aggregate Top 10 by canonical supplier alias | Demonstrably missing, already documented. The current run list and ranking group by extracted display name. This checkpoint preserves the metric and verifies it on actual records. Canonical alias aggregation would require projection and queue-filter changes outside this repair. | backend/app/api/runs.py, list_runs. frontend/src/worklist.ts, rankVendors. |
| Keep financial, policy, dashboard, and Excel reconciliation unchanged | Already implemented and working. Verified recorded and preview policy controls, projections and workbook on the offline gate. | backend/app/orchestration/policies.py, with_price_tolerance. backend/app/orchestration/policy_preview.py, preview. backend/app/api/runs.py, dashboard. backend/app/api/workbook.py, build_invoice_workbook. |

## Demonstrated changes

1. Both saved executions were replayed with only the wire amount formatting changed. The former strict regex rejected all five grouped money fields in each case. The fix accepts valid Western and Indian comma grouping, retains sign and fractional digits, and accepts a known denomination only when it matches the invoice's declared currency. It does not infer currency or accept a denomination on a quantity. The original precision, missing-value, numeric-type, and evidence validators still run. Invalid grouping, currency conflicts, unsupported textual and numeric inputs, and overprecision remain schema failures. The old live rejected bodies are unavailable. These reproductions demonstrate the defect, not the precise contents of the lost replies.
2. A simulated 503 proved that the normal failure path now records the safe HTTP status and elapsed processing time without changing persisted run fields, adding retries, or retaining invoice content. The public wire, SQLite, and API schemas stayed unchanged.
3. Added focused tests for the new accepted and rejected amount formats and actual role substitution. The Kaveri-style surcharge-code-to-invoice-number swap and an invoice-number-to-PO swap remain unverified. Existing cross-row, due-date, balance, currency and duplicate/overrun tests remain in place.

## Blind 7 mutation and replay results

All seven PDF hashes and the external oracle were verified against the original pack manifest. The unchanged attached script reproduced 156 mutations across six native documents, all 156 accepted by presence, 32 by presence plus closure, and one after its role check. It identified 32 printed amount occurrences that violate the old wire regex if copied. The image-only invoice had no native corpus for this test.

The mutation generator supplied candidates for a separate, offline adapter that fed each wrong field value and its genuine printed text through production parse_response and ground_evidence. Exact bare tokens and containing native lines yielded 203 distinct claim variants across the 156 unique changes. Before and after the patch, there were **0/203 wrong native-verified references**. A second pass ran production evaluate with the unchanged seed and the other baseline claims retained. It returned **0/203 false Ready**. Clean Orion and Northstar both reached Ready in that pass. The other four clean baselines in this particular challenge harness did not clear, so their final decisions alone are less discriminating than the zero wrong-reference result. Neither the attached reference verifier nor its date rule is in application code.

| Saved facts replay | Before | After |
|---|---|---|
| Orion canonical reply | Ready, 13/13 native | Ready, 13/13 native |
| Aster canonical reply | Blocked, 1/13 native | Blocked, 1/13 native |
| Orion with grouped wire amounts | MODEL_OUTPUT_SCHEMA | Ready, 13/13 native |
| Aster with grouped wire amounts | MODEL_OUTPUT_SCHEMA | Blocked, 1/13 native |

All three Aster Blocks remained. Its INR 30,000 net exceeded the INR 25,000 remaining PO and line balances by INR 5,000, and six units exceeded the five remaining. The separate source-evidence finding remained. No historical snapshot was updated. The sealed 26-case replay used the previous per-case provider replies and expected decisions, and matched the baseline's Ready, Review, and Blocked counts, findings, source states, extracted facts and authority fingerprint.

The dashboard and workbook were verified on a disposable copy of the successful live pair. The dashboard reported INR 55,460 gross submitted, INR 20,060 Ready and INR 35,400 Blocked. It reported INR 30,000 flagged net. All three workbook sheets opened, with both register rows reconciling. The actual Top 10 function returned just Aster Systems, one attention run. The current ranking's separate-alias behavior is unchanged. The policy and projection tests ran with temporary data.

## Verification and artifacts

| Check | Observed |
|---|---|
| python -m pytest -q backend/tests | 615 passed, one existing Starlette deprecation warning |
| npm --prefix frontend test | 71 passed |
| npm --prefix frontend run build | TypeScript and Vite production build passed |
| 26 sealed controlled cases | 6 Ready, 16 Review, 4 Blocked; 0/14 false Ready on non-Ready targets, 207/363 native-verified; every decision, finding, field score, and evidence state matched the baseline |
| Native mutation sweep | 156 unique field swaps, 203 printed quote variants, 0 wrong native verifications before or after; 0 false Ready in the post-patch evaluation sweep |
| Authority fingerprint | f6e95512f3e71d59bf512c1afc861e69587c3bbf40a9400c0f6c04739d02bf31 before and after |
| Manifest and Git whitespace | Passed |

Ignored local artifacts are under tmp/reconciliation. The identical mutation-count files before and after hash to 7f363d42c9c5264b770d53d9fa9b5e08f6118fc72629da86cf3d30570e9129c1. The full-claim evaluator result hashes to 7b8627fbe459119951ee513bc8ac46855579d3e9be41f24032986ea4a9c3e0d4. The sealed-case comparison output hashes to 798d2c40d148deb5c8da592f6e6b596e1c469142b14e1da9a7e5aa8546d1b261. No original fixture, oracle, seed, history database or prior results file was altered.

## Remaining uncertainty and next approved check

The original string-pattern rejections cannot be attributed to decimal formatting with certainty, even though feeding the printed amounts reproduced the same count pattern. The normalization patch was verified offline. The previous live Orion/Aster validation was real but small. Aster-like narrative row layouts can still leave evidence unresolved, and the image-only scan has no successful latest live result. An unseen layout can still take the conservative Review path.

Proposed future check, requiring separate approval before any generation: **Northstar** should reach Ready with independently anchored printed values, **Kaveri** should retain Review for the unauthorized surcharge, and **Meridian image-only** should complete as a safe Review with zero native-verified references. Use the normal provider, isolated storage, one call per invoice and zero retries. A technical failure stays separate and should not be counted as Review. No gates from either review supersede the user's requested three-case limit or the requirement for separate authorization.
