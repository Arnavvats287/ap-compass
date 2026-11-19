# Phase 2 — Pure financial engine

## Entry points and trust boundary

```python
from app.domain import build_context, evaluate
context = build_context(invoice, trusted_vendors, trusted_pos, trusted_billed_history)
decision = evaluate(context, policy)
```

Inputs are existing frozen Pydantic v1 snapshots. The domain package imports no DB, network,
provider, document parser, API, filesystem or frontend modules. No clock, randomness or writes.
Return type is the existing `DecisionV1`. No public contracts, seed data or schema changed.
Callers must supply the complete relevant authoritative procurement/billed snapshots and the trusted vendor
master; the engine cannot detect an omitted billed record from a tuple alone. Extracted/model-generated data
must never be passed as authoritative vendor, PO, bank-master or ledger records.

`build_context` resolves the raw supplier name against canonical names and listed aliases, using only
case/whitespace normalization. Alias collisions remain unresolved. The extracted normalized vendor-name
field is not allowed to override raw-source identity. Fuzzy names never verify a supplier.

An explicit PO is looked up across all supplied authoritative POs, including a different vendor's,
closed or overbilled PO. It is never replaced by a financially convenient PO. When the reference is missing,
all canonical-vendor POs are retrieved; exact item-code overlap distinguishes scope. Candidate `rank` is an
ordinal (ties share rank 1), not confidence. PO ID sorts presentation only, never tie-breaking selection.
No balance, date, status or price threshold filters identity. Tied top candidates stay unresolved. A unique
candidate still produces PO_REFERENCE_MISSING under the initial policy. Setting require_explicit_po=false
can remove that review only for unambiguous identity and all other passing controls; ambiguity remains review.
No human-confirmation functionality is implemented or inferred from a provenance string.

`evaluate` checks trusted-input consistency and re-derives identity from the canonical vendor/procurement
snapshots. Supplied selected PO/candidate ranks cannot forge an increased commitment or hide ambiguity.
A selected PO differing from the authoritative record is a technical input error. Context is never mutated.

## Rule catalog

Each rule is a small `(context, policy) -> tuple[FindingV1, ...]` function.

| Function | Reason codes | Behavior |
|---|---|---|
| vendor_requirement | VENDOR_UNVERIFIED | Unknown, colliding or unapproved vendor requires Procurement review |
| po_identity | PO_MATCH_CONFIRMED, PO_REFERENCE_MISSING, PO_AMBIGUOUS, PO_NOT_FOUND | Identify separately from eligibility; expose provenance and unresolved alternatives |
| vendor_po_consistency | VENDOR_PO_CONFLICT | Known supplier/explicit-PO contradiction blocks |
| po_status | PO_CLOSED | Any status other than OPEN blocks billing; retain identity |
| currency_compatibility | CURRENCY_MISMATCH | Block mismatching currency; skip meaningless cross-currency monetary comparisons |
| required_fields | CRITICAL_FIELD_MISSING | Missing header/line financial facts stay null and require review |
| source_evidence | SOURCE_EVIDENCE_MISSING | Missing, contradictory, image-only or unverified critical evidence requires review |
| financial_values | FINANCIAL_VALUE_INVALID | Negative amounts/nonpositive quantity or invoice net/total require review; no credit-note processing |
| invoice_arithmetic | TOTAL_RECONCILIATION_FAILED, LINE_TOTAL_RECONCILIATION_FAILED | Header net+tax=gross, stated line qty×price=net and line sum=header net within amount allowance |
| item_mapping | LINE_MAPPING_UNRESOLVED | Exact case/whitespace-normalized item-code mapping; bundled/unmapped lines require review |
| remaining_commitment | PO_BALANCE_EXCEEDED | PO authorized net minus authoritative billed net; no allowance for overrun |
| remaining_quantities | PO_QUANTITY_EXCEEDED | Ordered minus authoritative billed quantities; aggregate split invoice lines |
| remaining_line_commitments | PO_LINE_BALANCE_EXCEEDED | Per-item remaining net authorization; aggregate split invoice lines |
| unit_price_tolerance | PRICE_VARIANCE | Absolute price difference <= PO price×policy tolerance; does not override ceilings |
| billed_duplicates | EXACT_DUPLICATE, POSSIBLE_DUPLICATE | Exact canonical-vendor/invoice-number identity blocks; weaker deterministic signals require review |
| bank_instructions | BANK_DETAILS_NOT_PROVIDED, BANK_MASTER_UNVERIFIED, BANK_DETAILS_UNVERIFIED, BANK_DETAILS_MISMATCH | Absence is informational; uncertain source/master is review; verified contradiction blocks |

Every REVIEW/BLOCK finding includes an owner and action; bank values are not echoed in explanations.
All independent findings are retained. Severity precedence is BLOCK > REVIEW > READY. Primary reason is
first at the maximum severity in the deterministic rule order; this is a presentation choice, not loss of other exceptions.
PO_MATCH_CONFIRMED means identified, not eligible, financially approved, paid or posted.

## Money, evidence and policy details

- Finite Decimal inputs, sums and products only; no floats, division, implicit quantization or unknown-to-zero conversion.
  Evaluation uses input-derived precision, including carry headroom, independent of the caller's Decimal context.
  A regression guards the 2% boundary with a difference beyond the 60th decimal place.
- Empty known ledger sums begin at Decimal(0). Unknown extracted fields never do.
- Line net is optional in the existing contract. If absent, a separate calculation may use known qty×price for
  reconciliation; it never fills the extracted field. If those operands are missing, review is mandatory.
- Price tolerance is inclusive and symmetric. Header/line arithmetic allowance is inclusive (default INR 1.00).
  Value and quantity ceilings are strict, even for overruns below INR 1.00.
- The frozen v1 invariant prohibits commitment overrun. A nonzero commitment_overrun_allowance raises ValueError
  as unsupported policy configuration rather than silently permitting an overrun. The shared field remains unchanged.
- Critical evidence field keys are vendor_name_raw, invoice_number, invoice_date, po_reference (when present),
  currency, net, tax, total, lines[i].item_code/qty/unit_price_net and lines[i].net when supplied.
  Bank fields use bank_instructions.account and bank_instructions.ifsc.
- The evaluator consumes a single NATIVE_VERIFIED/native_text reference per critical field, with page, nonempty
  quote/raw value and matching normalized value. It never promotes a model quote or verifies a PDF itself.
  The source adapter is responsible for genuine verification. Tests explicitly label evidence as synthetic oracle assertions.
- Exact duplicate key: canonical vendor ID + invoice number with only case/whitespace normalization.
  It ignores changed date/layout/amount. Different canonical vendors do not share this key.
- Possible duplicate: same vendor and separator-only/alphanumeric invoice-number variant, OR same vendor, PO,
  currency and net with invoice dates within seven calendar days (inclusive, either direction). This is review-only,
  not proof. Threshold/heuristic is documented for architectural review in ADR-014.
- Bank comparison requires verified invoice account/IFSC and complete trusted master. Missing instructions are not fraud.
  Contradiction is a hold pending independent known-contact verification, not a proven fraud conclusion.

## Extension and technical failures

`DEFAULT_RULES` is an ordered tuple of 16 evaluators. `evaluate_with_rules(context, policy, additional_rules)`
adds controls without removing mandatory rules. Aggregation depends only on severity, never a catalog of reason codes.
New controls return existing FindingV1 and need no aggregator rewrite; a regression proves a previously unknown code works.
Changing 2% to 5% only changes PolicyV1 at the call site. No matching, extraction, API or UI changes are needed.

Corrupt/contradictory authoritative snapshots, duplicate canonical PO IDs, unsupported policy configuration and
rule exceptions raise outward without a business decision. The future orchestrator must map technical failures
to execution states; no PROCESSING_FAILED business outcome or run pipeline is implemented in Phase 2.
Snapshot validation is not a database-integrity service and cannot establish completeness of caller-supplied data.

## Verification and boundaries

See PHASE_02_REPORT.md: 99 domain + 30 unchanged foundation tests. Database-isolation test reads real seeded
SQLite snapshots, blocks DB/network access during 20 evaluations, compares all authority rows and snapshots,
and checks the database file SHA256 before/after. Nothing consumes PO balance.

No Gemini, OCR, PDF upload, frontend changes, orchestration, workers, human approval, Docker or deployment work.
The INJECTION manifest's financial facts are evaluated, but no actual prompt-injection extraction test is claimed.


## Phase 6B.1 explicit human identity entry point

evaluate_with_confirmed_po(context,policy,POConfirmation) is a separate pure path. Ordinary evaluate,matching
and all existing rule functions remain unchanged. It rederives canonical context,requires approved vendor/
missing explicit reference/authoritative same-vendor candidate/rationale,and substitutes only po_identity
with a human-provenance PO_MATCH_CONFIRMED. Same DEFAULT_RULES otherwise,aggregator and Decimal context.
Source evidence and missing facts are never repaired by confirmation. Financial eligibility is not identity.
Application validation additionally restricts selection to retained original/current candidates and a completed
source; action/result are persisted atomically outside the pure engine. See ADR-020,HUMAN_PO_RESOLUTION.md.
