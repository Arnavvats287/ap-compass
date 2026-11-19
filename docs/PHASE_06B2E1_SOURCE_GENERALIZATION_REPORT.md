# Phase 6B.2E.1 source generalization and invoice completeness

## Starting point and boundaries

Development-only comparison against `4bac08cd84226703cdcef2b76089f72f4e920cbe`, checkpoint `phase-06b2d2-private-demo-hardening`. No private held-out files were opened or rerun. The ten published benchmark JSONs and ten tracked source PDFs match the base byte-for-byte by SHA-256. Golden oracles, procurement authority, benchmark scoring, output schemas, Gemini prompts/settings, finance logic, API and private-demo configuration have zero diff. Zero Gemini calls.

## Trust path and diagnosis

The wire schema supplies untrusted values, page, raw value and quote. The isolated PyMuPDF parser supplies the observed characters, route and bounded line rectangles independently. Grounding resolves the claim to a labelled header or a uniquely identifiable table row, checks the field and actual value, and supplies an evidence state. The deterministic evaluator consumes this state under existing source requirements.

| Evidence state | Meaning at this boundary |
|---|---|
| `NATIVE_VERIFIED` | One usable claim points to a native page. The field-specific label or row and column support the exact value. The claimed raw representation is compatible with what was printed. Document-level header conflicts, competing associations and source denomination checks still apply. |
| `SOURCE_LOCATED_UNVERIFIED` | A quote or geometry-derived representation was located, but uniqueness, role, field, row, completeness, denomination or another support check failed. For non-native pages the route and provider's page reference are recorded without independent native verification. |
| `MISSING` | The adapter has no usable claim/page/value or could not locate that claim in the native source. Even a visible fact cannot acquire an independently affirmed claim when the provider did not supply one. |

Split labels already paired with nearby right-hand or aligned lower cells, but their exact flattened quote was the only accepted representation. Similar brittleness affected full visual table row quotes. PDF content may be emitted column-first while its displayed rows are intact. Flattened reading order, valid separators in a model quote, repeated quantities/amounts, supplier/buyer/remittance roles and repeated statement totals are distinct issues. Missing claims remain outside the generalization.

Table scanning previously stopped at a vertical gap or a broadly recognized label. It could therefore certify a prefix of a table. A recognized table that failed geometry parsing instead looked indistinguishable from a layout with no table and could fall back to labelled-line verification. Three controlled, synthetic omission variants actually reached Ready at the base, despite an additional visible zero-price included line. The extracted values reconciled exactly, which is why arithmetic could offer no protection in those cases.

## Implementation

- `backend/app/documents/source_layout.py` constructs alternate normalized quote forms from the independently paired cells. A split label can use a colon or pipe delimiter. A complete visual row can use pipe separators between exact printed cells. Whitespace and case normalization are retained. Field values and the order of cell text stay intact. The evidence still has to refer to the independently supported label/value pair or unique row, and value support still uses the existing exact Decimal and source-denomination checks. This is a bounded representation change, with no free-form quote reconstruction.
- A recognized table still requires item-code, quantity, and unit-price columns. One clean column band, non-overlapping visual rows, exact column assignment and compatible printed types are required. Vertical spacing alone no longer ends the table. A recognized invoice amount band or account-summary label can close the charge region. Another charge-shaped row below that boundary withholds table support. Unknown or overlapping content within the charge region leaves it unresolved. The row count must agree with extraction, ordered item codes must match, and conflicting supplied descriptions withhold support. Completed row quotes must distinguish the row even where codes or prices repeat.
- `backend/app/documents/evidence.py` distinguishes absence of a recognized table from a recognized but unresolved table. In the latter case a labelled-line fallback cannot independently attest the extracted charge lines. Header verification remains independent. Existing source-review findings reflect the missing line support. No new findings, public fields or fabricated charge lines were added. The legacy standalone seller-heading guard also excludes adjacent remittance context.
- `backend/tests/source_layout_fixtures.py` adds original synthetic variants for split roles, column-ordered PDF content, row spacing, a footer followed by a charge, and a table with an added included service. `backend/tests/test_source_generalization.py` drives the real parser, strict wire response, grounding and deterministic evaluator. Rendered pages were visually inspected for distinct label roles, repeated item rows and separation of balances.

## Observed evidence and decisions

| Development observation | Base | Remediated |
|---|---|---|
| Beside/below labels, visual table quote with delimiters, repeated authorized code, equal unit prices, different quantities, separate statement balances (representative column-emitted fixture) | 0/18 native refs, Review | 18/18 native refs, Ready |
| Visible included service omitted after a wide row gap | Remaining quantity native verified, Ready | Remaining quantity source located unverified, Review |
| Visible included service omitted after the totals band | Remaining quantity native verified, Ready | Remaining quantity source located unverified, Review |
| Overlapping table with a labelled echo of the submitted line | Remaining quantity native verified, Ready | Remaining quantity source located unverified, Review |
| Two rows supplied in the complete widely spaced table | Second-row quantity unverified | Second-row quantity native verified, Ready |
| Verified extra item within remaining commitment | Formatted item claim missing, Review | Item code native verified, Review with `LINE_MAPPING_UNRESOLVED` owned by Procurement |
| Wrong field or wrong row quote that matches another independently located association | Missing in reformatted forms | Source located unverified, Review |
| Incorrect/invented item text, reordered price columns, supplier claim using remittance name, combined account balance under gross, or no provider quote | No defensible native association | Missing or unverified, Review |
| Recognized contradictory total or foreign source denomination with formatted quote | Existing ordinary-quote guards withheld support | Source located unverified, Review |
| Duplicated or merged extracted rows with reconciled submitted amounts | — | Remaining quantity source located unverified, Review |

In each omission test, net stays verified, `SOURCE_EVIDENCE_MISSING` fires, and `LINE_TOTAL_RECONCILIATION_FAILED` is absent. The omitted row is not inserted into the extraction. The complete repeated-item case preserves both quantities and its row descriptions. Existing regression cases exercise bank mismatches, image and mixed-route uncertainty, conflicts, duplicate and overbilling Blocks, unresolved scope, and policy controls. The private Docker smoke independently preserved Ready, Blocked, original missing-PO Review with an audited Ready reassessment, and 2% recorded Review with a Ready 5% preview.

## Limits and cost

The existing parser process and wire limits are unchanged. The subprocess supplies at most 600 eligible layout lines per page, with the existing 8 MiB input, 10 pages, 12-second wall time, and 512 MiB memory limits. A recognized table accepts at most 50 rows. With the column count fixed by the label grammar, the table scan is linear in inspected rows. It builds two full quote forms per supported row and indexes their occurrences. Geometry support does not accept arbitrary permutations, partial rows, paraphrases, competing labels or conclusions from amount-only text. Page continuations, rotated text, multiline cells and narrative invoices can remain unsupported or lack a completeness guarantee. The PDF parser's existing readability heuristic is separate from authenticity.

Same input before and after. Timing is median milliseconds across nine bounded subprocess inspections per fixture; grounding uses medians of nine groups of 30 calls with already parsed source and typed claims. Timing is local wall clock. Subprocess code did not change, and variation in parser observations includes CPU-load and startup noise.

| Fixture | Parser base → patched (ms) | Grounding base → patched (ms) |
|---|---:|---:|
| Original development native invoice | 482.814 → 447.104 | 0.800 → 0.735 |
| Column-emitted development table | 439.112 → 554.758 | 0.937 → 1.295 |
| Two-page native revision | 455.520 → 561.304 | 0.998 → 1.347 |
| Original development scan | 554.336 → 654.676 | 0.067 → 0.064 |

## Verification record

The initial 15 new development tests against the unmodified production code produced 9 failures and 6 passes. A subsequent draft test had inconsistent merged-line arithmetic. The fixture was corrected so the final regression actually isolates source support on that case. The actual base decisions above were rechecked with the two base verifier modules and the same final PDF inputs, parser, wire schema and evaluator.

| Command or check | Actual result |
|---|---|
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest06b2e1-final --tb=short` | 508 passed in 135.25 s, including 20 new generalization cases, 49 currency-evidence cases and 17 private-demo cases. Existing Starlette/AnyIO deprecation warning. No failures, skips or XFAILs. |
| `npm --prefix frontend test` | 58 passed across 3 files. |
| `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` | Passed. Vite transformed 1,754 modules. |
| `.venv/Scripts/python scripts/verify_manifests.py` and `.venv/Scripts/python scripts/verify_git_hygiene.py` | Passed. Six vendors, seven POs, three prior bills, ten original scenarios, 11 hygiene checks and ten fixture PDFs. |
| `.venv/Scripts/python -m pip check` and `npm --prefix frontend ls --depth=0` | Passed. |
| `docker build -t ap-compass:source-generalization .`, `scripts/private_demo.py`, and `frontend/scripts/private-demo-qa.mjs` including `--restart` | Passed on loopback in a disposable volume. Basic-auth challenge, embedded PDF, deep link, audited confirmation, read-only tolerance preview, upload-off restart, four unchanged run snapshots and four original PDF hashes verified. |
| Base Git object comparison | SHA-256 matched ten published JSONs and ten tracked PDFs byte-for-byte. Protected paths have zero diff. |

The new upload regression uses disposable storage. It persisted the missing-row evidence finding, retained Review in the 5% preview, reloaded the exact snapshot and PDF, and compared an existing decision, demo review action and procurement authority unchanged after restart. Its controlled provider was called once for the upload and zero times for reload or preview. Existing private admission, human review and history tests are included in the complete suite. No live or independent benchmark improvement has been measured.

**SOURCE GENERALIZATION PASS — READY FOR INDEPENDENT EVALUATION.**
