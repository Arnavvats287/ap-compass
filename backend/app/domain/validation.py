"""Invalid trusted inputs/configuration raise technical errors, never decisions."""
from decimal import Decimal

from app.contracts import EvaluationContextV1, PolicyV1
from .common import normalized


class InvalidEvaluationContext(ValueError):
    pass


def validate_inputs(context: EvaluationContextV1, policy: PolicyV1) -> None:
    if policy.commitment_overrun_allowance != 0:
        raise ValueError("Nonzero commitment overrun allowance is unsupported by the v1 hard ceiling")
    pos = {normalized(p.id): p for p in context.procurement_records}
    if len(pos) != len(context.procurement_records):
        raise InvalidEvaluationContext("Duplicate canonical PO identity")
    if context.selected_po is not None and pos.get(normalized(context.selected_po.id)) != context.selected_po:
        raise InvalidEvaluationContext("Selected PO differs from authoritative procurement snapshot")
    for po in pos.values():
        codes = [normalized(line.item_code) for line in po.lines]
        if not codes or len(codes) != len(set(codes)) or any(not code for code in codes):
            raise InvalidEvaluationContext("PO lines require unique nonempty item codes")
        if any(line.ordered_qty <= 0 or line.unit_price_net <= 0
               or line.authorized_net != line.ordered_qty * line.unit_price_net for line in po.lines):
            raise InvalidEvaluationContext("Invalid authoritative PO line amounts/quantities")
        if po.authorized_net != sum((line.authorized_net for line in po.lines), Decimal(0)):
            raise InvalidEvaluationContext("PO authorization differs from its line commitments")
    seen = set()
    for billed in context.prior_billed_records:
        po = pos.get(normalized(billed.po_id))
        if billed.id in seen or po is None or billed.vendor_id != po.vendor_id or normalized(billed.currency) != normalized(po.currency):
            raise InvalidEvaluationContext("Invalid authoritative billed identity or currency")
        seen.add(billed.id)
        codes = {normalized(line.item_code) for line in po.lines}
        if not billed.lines or any(normalized(line.item_code) not in codes or line.qty <= 0
                                   or line.unit_price_net < 0 or line.line_net != line.qty * line.unit_price_net
                                   for line in billed.lines):
            raise InvalidEvaluationContext("Invalid authoritative billed lines")
        if (billed.net < 0 or billed.tax < 0 or billed.net + billed.tax != billed.gross
                or billed.net != sum((line.line_net for line in billed.lines), Decimal(0))):
            raise InvalidEvaluationContext("Invalid authoritative billed totals")
