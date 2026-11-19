# Phase 6B.2C.3 — Source grounding and workflow remediation

## Baseline and scope

Base `fb2a4535cc3e32a15c139fdfc59250b85e84a936` and tag `phase-06b2c2-benchmark` verified. Branch `codex/phase-06b2c3-grounding-remediation`. The tests use original synthetic development fixtures generated in memory, existing tracked development controls, and controlled wire replies. Zero Gemini requests. The independent PDFs and local archive were never opened or rerun during this phase. No benchmark evaluator, source annotation, production prompt, API, UI, database or shared contract change. See [the evidence and layout design](SOURCE_GROUNDING_REMEDIATION.md).

## Verification behavior and test-first evidence

The first red check reported 6 failures and 10 passes before remediation. It exercised unexpected rejection of split headers/tables and a legitimate repeated statement reference, and the incorrect scope owner. Follow-up red checks covered the scan action, repeated rows separated by printed service periods and the competing purchase-reference boundary. Review of the new layout path uncovered two further unsafe draft associations: a vertical label could use an adjacent buyer's value and a table column could impersonate the invoice subtotal. Both now have passing standalone negative tests. The same frozen scope owner/action tests now run as ordinary assertions, including the explicit authorization, PO amendment and corrected supplier invoice language.

`N` is `NATIVE_VERIFIED`, `U` is `SOURCE_LOCATED_UNVERIFIED` and `M` is `MISSING`. The cases below used actual PDF bytes, isolated parsing, Pydantic wire parsing and independent grounding.

| Development case | Actual refs and outcome |
|---|---|
| Split adjacent seller/invoice/date cells, vertical PO/currency cells and labelled table | 18 N. `READY_FOR_AP`. Two authorized occurrences of the same item have quantities 3 and 2 with separate descriptions and printed nets. |
| Distinct service periods with otherwise identical rows | 18 N. Original Aug and Sep period text remains in the respective row quotes. |
| Separate account summary repeats the current gross | 18 N. Current gross independently grounded; the previous and combined balances have no authority for that field. |
| Existing tracked `STATEMENT_PRIOR_BALANCE` | Its ₹4,720 current gross quote is N in a targeted test. This test establishes total support. It does not claim all other fields in the frozen PDF verify. |
| Conflicting revised gross, same page inline or next page split | 17 N, total U for each document. Original extracted gross retained. |
| Competing PO reference on an appendix | 17 N, PO reference U. Extracted reference retained; matching rules unchanged. |
| Plausible right and below total cells | 17 N, total U. |
| Same invoice number printed once inline and once as split labels | 17 N, invoice number U. |
| Missing item code | 8 N, 9 U, 1 M. Missing code remains M and the row's quantity is U. |
| Overlapping rows or repeated rows with the same full quote | 8 N, 10 U for each document. No table row verified. |
| Unprinted optional line net in an otherwise supported row | 17 N, line net U. The plausible amount has no printed line-net cell for that row. |
| Wrong buyer, wrong current total, wrong invoice identity, neighboring-row quantity/price, abbreviated numeric-only quote or reordered rows | The relevant fields stayed U or M. Repeated prices do not override row association. |
| Buyer information under an unrelated overhead label, and a row net beneath a table column label with no invoice subtotal | Neither unsupported header verified. The independently matched row net still verified. |
| Explicit source-verified extra item in a supported table | 18 N. `REVIEW_REQUIRED` with `LINE_MAPPING_UNRESOLVED`, Procurement, and an authorization/amendment-or-correction action for line 2. |
| Frozen image-only `SCAN_CONFLICT` | Zero N. `REVIEW_REQUIRED`; existing arithmetic discrepancy retained. The source finding now tells AP to compare with the PO and billed history or request a clearer/native PDF. |

The scope finding still reports exact 1-based line indices. Missing or unverified item identity remains AP clarification. Ambiguous PO identity, duplicate invoices, verified bank contradictions, hard budget and quantity blocks, image-only/mixed uncertainty, and unreadable-page guards retain their original control paths. This phase changes only independent source support and the specified finding-level workflow. The existing controlled fixture that is within PO commitment still requires Review for the unsupported extra item.

## Performance

The same offline inputs were run against an archived base `backend/app` and the worktree, using the same installed Python and dependency versions. Parser time includes real subprocess creation, native text work, rendering where applicable, JSON transport, and decoding. The reported statistic is the median of 11 calls after one warmup. Grounding is in-process wall-clock median per operation across seven batches of 300 pre-parsed inputs (no parser, inference, network or DB time).

| Input | Parser baseline → updated, ms | Grounding baseline → updated, µs | Native verified refs |
|---|---:|---:|---:|
| Single native | 403.174 → 398.873 | 443.729 → 651.338 | 13 → 13 |
| Two-page native | 412.076 → 444.126 | 450.689 → 688.130 | 13 → 13 |
| Native table | 408.230 → 407.429 | 609.548 → 836.632 | 0 → 18 |
| Image only | 525.065 → 506.151 | 50.144 → 49.856 | 0 → 0 |
| Native/raster mixed | 426.080 → 424.779 | 57.560 → 51.873 | 0 → 0 |

Native grounding added about 0.21–0.24 ms on these workloads. The two-page parser median added 32.05 ms and the other parser medians were close or lower in this run. Small samples and OS process startup variability limit what the timing deltas establish. The 600-rectangle metadata path applies only to eligible native pages. Input/page, memory/time, image pixel and text/line caps remain in place.

## Local persistence and browser

An offline API smoke copied a populated demo SQLite database through the SQLite backup API with the original opened read-only. The copy held seven historic runs and two audited actions. Five controlled uploads persisted in the copy. Reopening through a fresh app startup on the same copy reloaded all five extracted snapshots and PDFs byte-for-byte and history with zero extraction calls. Old run rows, stage rows, action rows, policy, schema, and procurement rows retained their original values. No internal rectangle or native layout payload appeared in public JSON.

Chrome rendered the five requested stored states at 1440 and 390 px. The browser checks observed verified Ready, distinct source uncertainty, Procurement routing for verified scope, overbilling Blocked, and scan-specific Needs review. They found no horizontal overflow or page errors. The existing broader QA checked 15 actual-data views and 7 controlled states, with persisted snapshots unchanged, keyboard and reduced-motion checks, and zero API mutations. Screenshots remain ignored under `tmp/phase06b2c3-runtime-final/` and `tmp/phase06b2c3-browser-qa-final/`.

Full API regressions exercise preview and confirmation using recorded evidence instead of re-extraction. Unresolved document or source uncertainty remains a review requirement through policy preview or confirmation. The authority snapshots, original assessments, review actions and billing ledger remain immutable. Persisted attempt telemetry is deferred because it would require a separate storage decision.

## Frozen benchmark integrity

All four reports match their prephase SHA-256 values. A protected-path Git diff verifies the evaluation runner, frozen data/seed manifests, original fixture PDFs, frontend, shared contracts, API, AI provider and orchestration unchanged.

| Historical report | Unchanged SHA-256 |
|---|---|
| `development-a.json` | `d88367a59def4dac27b2cf850ff4898b67bc3e701f5468b19726dbf4fb474e1c` |
| `development-b.json` | `0c6ca257a51a5300b49154976e2398b88053f0cd85f9268fcf6db7b4d449476f` |
| `heldout-b.json` | `323e77d7d49ab7b22c61f04dbd9a34abd669a1883b80ce5548b270fe8e50470d` |
| `heldout-c.json` | `da27bddd54ba6109373853b766e41aee4e36e2b7adb328bfe43c02cace28c8ac` |

No claim of post-fix independent performance is made. Unsupported multiline or ambiguous layouts remain potential unnecessary Review outcomes. The renderer check does not authenticate documents or prove individual glyph visibility. See the design for exact limitations.

## Verification commands

| Command | Result |
|---|---|
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q -rx --basetemp tmp/pytest06b2c3-gate --tb=short` | 422 passed in 103.06 s. Zero failures, skips or XFAILs. One pre-existing Starlette deprecation warning. Windows local loopback allowed. |
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests/test_source_layout.py -q --basetemp tmp/pytest06b2c3-layout-closed --tb=short` | 26 passed. |
| `npm --prefix frontend test` | 58 passed in 3 files. |
| `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` | Both passed. Vite transformed 1,754 modules. |
| `.venv/Scripts/python scripts/verify_manifests.py` | Passed, 6 vendors / 7 POs / 3 billed rows / 10 original financial scenarios. |
| `.venv/Scripts/python scripts/verify_git_hygiene.py` | Passed, 11 exclusions and 10 byte-identical frozen PDFs. |
| `.venv/Scripts/python -m pip check` and `npm --prefix frontend ls --depth=0` | Both passed. |
| `.venv/Scripts/python tmp/phase06b2c3-smoke-final.py` then `.venv/Scripts/python tmp/phase06b2c3-smoke-final.py --serve` | Five offline uploads, restart and loopback with seven historic runs and two audited actions preserved. Zero extraction on restart. |
| `node tmp/phase06b2c3-browser-final.mjs` | All five persisted states passed at both viewports. |
| `node frontend/scripts/qa.mjs` with `AP_COMPASS_UI_URL=http://127.0.0.1:8011` and `AP_COMPASS_QA_DIR=tmp/phase06b2c3-browser-qa-final` | Passed 15 actual-data views and 7 controlled states, plus keyboard, reduced motion, persistence and no-mutation checks. |
| `.venv/Scripts/python scripts/benchmark_source_grounding.py --backend tmp/phase06b2c3-base/backend` followed by `.venv/Scripts/python scripts/benchmark_source_grounding.py` | Five same-byte workloads on archived baseline and updated code. |
| `Get-FileHash evaluation/results/v1/*.json` and `git diff --exit-code phase-06b2c2-benchmark -- evaluation data tests/fixtures frontend backend/app/contracts backend/app/api backend/app/ai backend/app/orchestration` | First results intact, protected paths byte-unchanged. |

An optional benchmark-runner test run on the dirty working tree exercised the runner's intentional clean-production guard. Its one schema execution test stopped before evaluation. The clean checkpoint can run the same test using `.venv/Scripts/python -m pytest evaluation/test_benchmark_v1.py -q --basetemp tmp/pytest06b2c3-runner-clean`. It exercises trusted development facts in a temporary output directory and does not touch published results or independent documents.

**Gate: SOURCE REMEDIATION PASS — READY FOR POST-FIX VALIDATION.** Stop for review. The independent benchmark was not rerun.
