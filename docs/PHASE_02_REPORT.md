# Phase 2 — Deterministic financial engine: review report

**Date:** 2026-11-19 (IST). **Gate:** PASS locally; architectural review pending. STOP after Phase 2.

## 1. Matching architecture

Pure `build_context(invoice, vendors, procurement_records, prior_billed_records)` creates the existing immutable
EvaluationContextV1. Vendor identity uses canonical names/listed aliases with case/whitespace normalization only.
Unknown names/colliding aliases stay unresolved. Explicit PO lookup retains closed, overbilled and wrong-vendor POs
for eligibility findings. Missing references retrieve all same-vendor POs, ranked by exact item-code overlap.
Equal top identity support remains ambiguous; stable ID ordering never chooses a winner. Rank is ordinal, not confidence.
No balance, policy threshold, date or status filters PO identity.

Pure `evaluate(context, policy) -> DecisionV1` validates authoritative inputs, independently re-derives identity,
runs 16 small mandatory evaluators and aggregates severity. Supplied ranks/provenance cannot hide ambiguity.
No DB/provider/network/HTTP/filesystem/clock/UI dependency or financial writes.

## 2. Rules and reason codes

See FINANCE_ENGINE.md for full function-to-code mapping and field-key conventions.

- Identity/status/currency: VENDOR_UNVERIFIED, PO_MATCH_CONFIRMED, PO_REFERENCE_MISSING, PO_AMBIGUOUS,
  PO_NOT_FOUND, VENDOR_PO_CONFLICT, PO_CLOSED, CURRENCY_MISMATCH.
- Data/source quality: CRITICAL_FIELD_MISSING, SOURCE_EVIDENCE_MISSING, FINANCIAL_VALUE_INVALID.
- Arithmetic/scope: TOTAL_RECONCILIATION_FAILED, LINE_TOTAL_RECONCILIATION_FAILED, LINE_MAPPING_UNRESOLVED.
- Historical financial reconciliation: PO_BALANCE_EXCEEDED, PO_QUANTITY_EXCEEDED, PO_LINE_BALANCE_EXCEEDED.
- Price/duplicates: PRICE_VARIANCE, EXACT_DUPLICATE, POSSIBLE_DUPLICATE.
- Bank controls: BANK_DETAILS_NOT_PROVIDED, BANK_MASTER_UNVERIFIED, BANK_DETAILS_UNVERIFIED, BANK_DETAILS_MISMATCH.

All REVIEW/BLOCK findings have owners/actions. Severity precedence is BLOCK > REVIEW > READY; every finding retained.
Generic aggregation recognizes severity, not reason-code names. The extension regression adds an unknown code without
changing aggregation or removing mandatory rules. Header and line reconciliation use Decimal; split lines are aggregated.
Price tolerance does not relax either financial ceiling. Input-derived precision prevents hidden Decimal boundary rounding.

## 3. Exact verification commands and results

From repository root:

```powershell
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests/test_finance_engine.py -q --basetemp tmp/pytest-phase02-boundaries
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest-phase02-final
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests/test_finance_engine.py -q -s -k engine_preserves_seeded_sqlite --basetemp tmp/pytest-phase02-ledger
.venv/Scripts/python scripts/verify_manifests.py
.venv/Scripts/python scripts/verify_git_hygiene.py
.venv/Scripts/python -m pip check
npm --prefix frontend run build
git diff --exit-code phase-01-foundation -- backend/app/contracts backend/app/db backend/app/api backend/app/main.py backend/tests/test_foundation.py data frontend tests scripts Dockerfile .dockerignore .gitattributes
```

| Check | Observed result |
|---|---|
| Domain suite | **99 passed**, zero failures, 1.08s |
| Entire backend suite | **129 passed** (30 foundation + 99 domain), **zero failures**, 2.22s |
| Third-party warning | One existing Starlette/AnyIO BlockingPortal alias deprecation warning |
| Focused persisted-ledger invariant | 1 passed, 98 deselected; 20 evaluations with DB/network blocked |
| Static oracle | PASS: 6 vendors / 7 POs / 3 billed / 10 expected scenarios |
| Git hygiene | PASS: 11 exclusions, placeholder allowed, no ignored tracked files, 4 PDF bytes preserved |
| Dependency consistency | No broken requirements |
| Frontend regression build | TypeScript/Vite PASS; 1682 modules; no frontend source changes |
| Protected Phase 1 files | Empty diff, exit 0 |
| Fixture smoke | All 10 fixture decisions plus PRICE_3PCT at 5% match expectations; table below |

Tests were added first: initial collection failed because engine entry points did not exist. After implementation,
a precision regression produced **1 failure / 77 passes**: fixed 50-digit Decimal precision incorrectly admitted a
price infinitesimally above the 2% boundary. Input-derived arithmetic precision fixed it; that regression and all
subsequent tests pass. No failures remain. Complete-suite HTTP tests used approved execution outside the Windows
sandbox, as required by the existing Phase 1 TestClient environment. Domain-only tests pass in the sandbox without network.

The fixture smoke was also executed with a repository-root Python here-string: added `backend` and `backend/tests`
to sys.path, imported CASES/context_for from test_finance_engine, and called evaluate for each fixture at PolicyV1(),
plus PRICE_3PCT at PolicyV1(version='policy-v2', price_tolerance_pct='0.05'). No extraction result is claimed.

## 4. Expected versus actual fixture decisions

These are **typed synthetic oracle facts**, not actual Gemini or PDF extraction. READY tests explicitly construct
NATIVE_VERIFIED/native_text oracle evidence. SCAN_CONFLICT explicitly uses SOURCE_LOCATED_UNVERIFIED/image_only.
The engine does not manufacture or upgrade evidence.

| Fixture | Expected | Actual | Observed reason codes |
|---|---|---|---|
| HAPPY_CLEAN | READY_FOR_AP | READY_FOR_AP | BANK_DETAILS_NOT_PROVIDED, PO_MATCH_CONFIRMED |
| HAPPY_PARTIAL | READY_FOR_AP | READY_FOR_AP | BANK_DETAILS_NOT_PROVIDED, PO_MATCH_CONFIRMED |
| AMBIGUOUS_PO | REVIEW_REQUIRED | REVIEW_REQUIRED | BANK_DETAILS_NOT_PROVIDED, CRITICAL_FIELD_MISSING, LINE_MAPPING_UNRESOLVED, PO_AMBIGUOUS, PO_REFERENCE_MISSING |
| OVERBILLED_PARTIAL | BLOCKED | BLOCKED | BANK_DETAILS_NOT_PROVIDED, PO_BALANCE_EXCEEDED, PO_LINE_BALANCE_EXCEEDED, PO_MATCH_CONFIRMED, PO_QUANTITY_EXCEEDED |
| DUPLICATE_REISSUED | BLOCKED | BLOCKED | BANK_DETAILS_NOT_PROVIDED, EXACT_DUPLICATE, PO_MATCH_CONFIRMED |
| SCAN_CONFLICT | REVIEW_REQUIRED | REVIEW_REQUIRED | BANK_DETAILS_NOT_PROVIDED, PO_MATCH_CONFIRMED, SOURCE_EVIDENCE_MISSING, TOTAL_RECONCILIATION_FAILED |
| BANK_CHANGED | BLOCKED | BLOCKED | BANK_DETAILS_MISMATCH, PO_MATCH_CONFIRMED |
| INJECTION | BLOCKED | BLOCKED | BANK_DETAILS_NOT_PROVIDED, PO_BALANCE_EXCEEDED, PO_LINE_BALANCE_EXCEEDED, PO_MATCH_CONFIRMED, PO_QUANTITY_EXCEEDED |
| UNKNOWN_VENDOR | REVIEW_REQUIRED | REVIEW_REQUIRED | BANK_DETAILS_NOT_PROVIDED, LINE_MAPPING_UNRESOLVED, PO_NOT_FOUND, PO_REFERENCE_MISSING, VENDOR_UNVERIFIED |
| PRICE_3PCT | REVIEW_REQUIRED | REVIEW_REQUIRED | BANK_DETAILS_NOT_PROVIDED, PO_MATCH_CONFIRMED, PRICE_VARIANCE |
| PRICE_3PCT at 5% | READY_FOR_AP | READY_FOR_AP | BANK_DETAILS_NOT_PROVIDED, PO_MATCH_CONFIRMED |

The manifest permits additional independent findings: overbilling also yields the item commitment finding;
ambiguous facts also identify missing quantities/prices and unresolved line scope. No expected outcomes were altered.
INJECTION covers only the manifest's numerical facts here; no document/model prompt-injection protection is claimed.

## 5. Historical billing immutability proof

The SQLite test initializes and idempotently seeds a temporary real DB, then loads VendorV1/PurchaseOrderV1/
PriorBilledInvoiceV1 snapshots from actual rows. It runs all 10 facts at 2% and 5% (20 evaluations) while monkeypatching
Session.execute and socket.socket to fail if evaluation attempts DB/network access. It verifies:

- Identical complete rows for 6 vendors, 7 POs, 7 lines and 3 billed invoices before/after.
- Identical serialized context/history snapshots before/after.
- Identical SQLite file bytes: SHA256 `9deec655e5c31cc08503ca2ffb003ab291b73a1047a5b3a131172fcee9848bce` in the focused observed run.

Separate tests prove repeated deterministic evaluation, lower balance cannot ready an overbill, 5% tolerance
cannot bypass a reduced net ceiling, exact duplicates block at all tested tolerances, missing amounts remain null,
known overbilling retains PO-3015, contradictory identities block, split lines cannot evade limits and caller-global
Decimal precision cannot change outcomes. Invariant variations are explicitly labeled synthetic snapshot projections;
they never edit the financial seed or its original expected outcomes.

## 6. Files and contract deviations

- Implemented backend/app/domain/{__init__,matching,rules,decisions}.py.
- Added backend/app/domain/{common,validation,evidence,reconciliation,controls}.py.
- Added backend/tests/test_finance_engine.py (99 tests).
- Added docs/FINANCE_ENGINE.md and this completed segment report.
- Updated README.md, PROJECT_STATUS.md, memory.md status/handoff, and DECISION_LOG.md (ADR-014 review heuristic).
- **No shared contract/schema deviations or extensions.** No DB/API/frontend/fixture/seed changes.
- Source evidence uses existing EvidenceRefV1.field keys; optional line net remains nullable, with a separate
  qty×price calculation when both source-supported operands exist. No fields are filled by inference.

## 7. Git checkpoint

- Base: phase-01-foundation at `12e4a5229903213017a852507d049133a1a7b871`; remote peeled tag confirmed unchanged.
- Branch: `codex/phase-02-finance-engine`.
- Remote: `https://github.com/Arnavvats287/ap-compass.git` (existing repository).
- Checkpoint: `phase-02-finance-engine`; resolve exact committed SHA with `git rev-parse phase-02-finance-engine^{commit}`.
- This report is prepared before its own commit. Actual push and final SHA are recorded in the final chat handoff,
  after branch/tag publication and remote verification. No force-push or Phase 1 tag overwrite authorized or used.

## 8. Known limitations

- Genuine evidence verification and complete authoritative-data loading remain trusted caller/adapter responsibilities.
  The evaluator cannot discover omitted billed records or prove that an attestation came from a real PDF.
- Exact item-code mapping only. Missing/bundled scope requires review; no semantic/fuzzy matching, embeddings or model identity.
- Possible-duplicate heuristic is a documented review signal (separator variant or seven-day equal business facts),
  not comprehensive fraud/duplicate detection. ADR-014 is presented for Phase 2 review.
- Negative/credit invoices are review-only; no credit-note ledger model. Missing line net is not fabricated.
- Nonzero commitment_overrun_allowance is unsupported under the frozen hard ceiling and raises a technical configuration error.
- Invalid authority/policy and rule errors propagate without a business decision; future orchestration must handle execution failures.
- No audited human PO confirmation. Provenance text alone is not confirmation.
- No Gemini/OCR, real extraction, uploads, API wiring, frontend changes, workers, orchestration, deployment/Docker work or learned hints.
- No new PDF fixtures, paid service or end-to-end invoice pipeline. No subagents used.

## 9. Acceptance gate and next authorized action

**Phase 2 acceptance: PASS locally; ready for architectural review.** No unresolved Phase 2 blocker.
Phase 1 review acceptance is recorded from the user's authorization. Phase 3 and later remain unstarted and unauthorized.
STOP here; wait for explicit Phase 2 repairs or the next bounded prompt.

## Completed segment-template checklist

- [x] Every required acceptance scenario ran against immutable original fixture expectations.
- [x] All existing tests plus new domain tests passed; technical failures remain distinct from business outcomes.
- [x] Historical authority and input snapshots unchanged under evaluation.
- [x] No unapproved contract/schema changes, fake stages, fake extraction results or UI metrics.
- [x] PROJECT_STATUS and memory updated from observed evidence.
- Actual PDF-to-decision execution stages/timestamps/model usage: NOT IMPLEMENTED / NOT RUN in this phase.
