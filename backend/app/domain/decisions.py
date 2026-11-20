"""Pure deterministic evaluation: no DB, provider, clock, HTTP or UI dependency."""
from collections.abc import Callable, Sequence
from decimal import Context, Decimal, MAX_EMAX, MIN_EMIN, ROUND_HALF_EVEN, localcontext

from app.contracts import DecisionV1, EvaluationContextV1, FindingV1, PolicyV1
from .controls import bank_instructions, billed_duplicates
from .evidence import required_fields, source_evidence
from .document_integrity import document_content
from .matching import build_context
from .reconciliation import (
    financial_values, invoice_arithmetic, item_mapping, remaining_commitment,
    remaining_line_commitments, remaining_quantities, unit_price_tolerance,
)
from .rules import currency_compatibility, po_identity, po_status, vendor_po_consistency, vendor_requirement
from .validation import validate_inputs

Rule = Callable[[EvaluationContextV1, PolicyV1], tuple[FindingV1, ...]]
DEFAULT_RULES: tuple[Rule, ...] = (
    vendor_requirement, po_identity, billed_duplicates, vendor_po_consistency,
    po_status, currency_compatibility, required_fields, document_content, source_evidence,
    financial_values, invoice_arithmetic, item_mapping, remaining_commitment,
    remaining_quantities, remaining_line_commitments, unit_price_tolerance, bank_instructions,
)


def arithmetic_precision(context: EvaluationContextV1, policy: PolicyV1) -> int:
    """Enough digits for exact sums and two-operand products of supplied facts.

    Do not let caller-global precision or a fixed precision erase a price/ceiling
    boundary. The current rules use no division or monetary quantization.
    """
    def decimals(value):
        if isinstance(value, Decimal):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                yield from decimals(item)
        elif isinstance(value, (tuple, list)):
            for item in value:
                yield from decimals(item)

    values = tuple(decimals((context.model_dump(), policy.model_dump())))
    span = max(v.adjusted() for v in values) - min(v.as_tuple().exponent for v in values) + 1
    return max(50, 2 * span + len(str(len(values))) + 4)


def aggregate(findings: Sequence[FindingV1], policy: PolicyV1) -> DecisionV1:
    """Reason-code agnostic. Primary finding is first at the highest severity."""
    precedence = {"PASS": 0, "INFO": 0, "REVIEW": 1, "BLOCK": 2}
    highest = max((precedence[f.severity] for f in findings), default=0)
    primary = next((f for f in findings if precedence[f.severity] == highest), None)
    return DecisionV1(
        outcome=("READY_FOR_AP", "REVIEW_REQUIRED", "BLOCKED")[highest],
        findings=tuple(findings), primary_reason_code=primary.code if primary else None,
        owner=primary.owner if primary else None,
        next_action=primary.next_action if highest else "Continue to AP review; this does not authorize payment or posting.",
        policy_version=policy.version,
    )


def evaluate_with_rules(context: EvaluationContextV1, policy: PolicyV1,
                        additional_rules: Sequence[Rule] = ()) -> DecisionV1:
    """Add rules without removing mandatory checks or changing aggregation.

    Technical exceptions propagate to the future orchestrator. No business
    decision is fabricated for invalid authority, invalid policy or rule failure.
    """
    with localcontext(Context(prec=arithmetic_precision(context, policy), rounding=ROUND_HALF_EVEN,
                              Emax=MAX_EMAX, Emin=MIN_EMIN)):
        validate_inputs(context, policy)
        # Re-derive selection; caller-supplied candidate ranks/provenance cannot
        # hide ambiguity or replace an explicitly referenced authoritative PO.
        canonical = build_context(
            context.invoice, (context.canonical_vendor,) if context.canonical_vendor else (),
            context.procurement_records, context.prior_billed_records,
        )
        findings = tuple(f for rule in (*DEFAULT_RULES, *additional_rules) for f in rule(canonical, policy))
        return aggregate(findings, policy)


def evaluate(context: EvaluationContextV1, policy: PolicyV1) -> DecisionV1:
    return evaluate_with_rules(context, policy)


def preserve_submission_finding(decision: DecisionV1, recorded: DecisionV1, policy: PolicyV1) -> DecisionV1:
    """Carry the original submission-history finding into a reassessment."""
    additional = tuple(f for f in recorded.findings if f.code == "ALREADY_SUBMITTED")
    return aggregate((*decision.findings, *additional), policy) if additional else decision
