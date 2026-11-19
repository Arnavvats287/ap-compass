"""Explicit trusted human identity path. No document edits or relaxed financial/evidence policy."""
from dataclasses import dataclass
from decimal import Context, MAX_EMAX, MIN_EMIN, ROUND_HALF_EVEN, localcontext

from app.contracts import DecisionV1, EvaluationContextV1, PolicyV1
from .common import finding, normalized
from .decisions import DEFAULT_RULES, aggregate, arithmetic_precision
from .matching import build_context
from .rules import po_identity
from .validation import validate_inputs


class InvalidConfirmation(ValueError):
    """The proposed identity confirmation cannot be accepted."""


@dataclass(frozen=True)
class POConfirmation:
    po_id: str
    rationale: str


def confirmed_context(context: EvaluationContextV1, confirmation: POConfirmation) -> EvaluationContextV1:
    # Caller passes trusted masters, as for normal evaluate. Ignore claimed candidate ranks/selection.
    canonical = build_context(context.invoice, (context.canonical_vendor,) if context.canonical_vendor else (),
                              context.procurement_records, context.prior_billed_records)
    if (normalized(canonical.invoice.po_reference) or canonical.canonical_vendor is None
            or not canonical.canonical_vendor.approved):
        raise InvalidConfirmation('Missing reference and approved canonical supplier required')
    if (not isinstance(confirmation.rationale, str) or not confirmation.rationale.strip()
            or len(confirmation.rationale)>2000 or not isinstance(confirmation.po_id, str)):
        raise InvalidConfirmation('Explicit rationale and PO identity required')
    candidate = next((c for c in canonical.candidates if c.po.id == confirmation.po_id), None)
    if candidate is None or candidate.po.vendor_id != canonical.canonical_vendor.id:
        raise InvalidConfirmation('PO must be an authoritative same-vendor candidate')
    # No edits to invoice, source evidence, balances, policy, or remaining controls.
    return canonical.model_copy(update={'selected_po':candidate.po,
        'selection_provenance':'Audited human PO confirmation; '+candidate.selection_provenance})


def evaluate_with_confirmed_po(context: EvaluationContextV1, policy: PolicyV1,
                               confirmation: POConfirmation) -> DecisionV1:
    """The caller must atomically save the validated authenticated-or-explicitly-demo action and result.

    This pure path validates the proposed confirmation again. Only the PO identity rule is substituted;
    the ordinary evaluator is untouched. A confirmation is neither source verification nor approval.
    """
    with localcontext(Context(prec=arithmetic_precision(context,policy),rounding=ROUND_HALF_EVEN,
                              Emax=MAX_EMAX,Emin=MIN_EMIN)):
        validate_inputs(context,policy)
        canonical=confirmed_context(context,confirmation)
        def identity(confirmed, _policy):
            return (finding('PO_MATCH_CONFIRMED','PASS','Purchase order identified by human review',
                f'{confirmed.selected_po.id}: {confirmed.selection_provenance}. Financial eligibility is checked separately.',
                source='human_review',po_id=confirmed.selected_po.id),)
        findings=tuple(f for rule in DEFAULT_RULES for f in
                       (identity if rule is po_identity else rule)(canonical,policy))
        return aggregate(findings,policy)
