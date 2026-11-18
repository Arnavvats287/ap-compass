"""Net-of-tax reconciliation using exact Decimal values and independent rules."""
from decimal import Decimal

from app.contracts import EvaluationContextV1, PolicyV1
from .common import finding, normalized

ZERO = Decimal(0)


def billed_for_po(context):
    po = context.selected_po
    return tuple(b for b in context.prior_billed_records
                 if po and normalized(b.po_id) == normalized(po.id))


def same_currency(context):
    return (context.selected_po is not None and bool(context.invoice.currency)
            and normalized(context.invoice.currency) == normalized(context.selected_po.currency))


def line_groups(context):
    """Aggregate split invoice lines against each one authoritative PO line."""
    if context.selected_po is None:
        return ()
    return tuple((po_line, tuple((i, line) for i, line in enumerate(context.invoice.lines)
                                if normalized(line.item_code) == normalized(po_line.item_code)))
                 for po_line in context.selected_po.lines)


def calculated_net(line):
    # Derived calculation only, never an edit of a missing extracted fact.
    if line.net is not None:
        return line.net
    if line.qty is not None and line.unit_price_net is not None:
        return line.qty * line.unit_price_net
    return None


def financial_values(context: EvaluationContextV1, policy: PolicyV1):
    invoice = context.invoice
    invalid = [name for name in ("net", "total")
               if getattr(invoice, name) is not None and getattr(invoice, name) <= 0]
    if invoice.tax is not None and invoice.tax < 0:
        invalid.append("tax")
    for i, line in enumerate(invoice.lines):
        for name in ("qty", "unit_price_net", "net"):
            value = getattr(line, name)
            if value is not None and (value < 0 or (name == "qty" and value == 0)):
                invalid.append(f"lines[{i}].{name}")
    if invalid:
        return (finding("FINANCIAL_VALUE_INVALID", "REVIEW", "Unsupported financial values",
                        "Negative values, nonpositive quantities or nonpositive invoice net/total require review: "
                        + ", ".join(invalid), fields=", ".join(invalid)),)
    return ()


def invoice_arithmetic(context: EvaluationContextV1, policy: PolicyV1):
    invoice = context.invoice
    findings = []
    if all(value is not None for value in (invoice.net, invoice.tax, invoice.total)):
        expected = invoice.net + invoice.tax
        difference = abs(expected - invoice.total)
        if difference > policy.amount_rounding_allowance:
            findings.append(finding("TOTAL_RECONCILIATION_FAILED", "REVIEW", "Invoice totals do not reconcile",
                                    f"Net plus stated tax is {expected}; stated gross is {invoice.total}. "
                                    f"The difference {difference} exceeds the rounding allowance.",
                                    owner="Vendor", action="Request an invoice with reconciled stated amounts; do not invent a corrected total.",
                                    expected_gross=expected, stated_gross=invoice.total, difference=difference))
    line_nets = tuple(calculated_net(line) for line in invoice.lines)
    if invoice.net is not None and line_nets and all(value is not None for value in line_nets):
        calculated = sum(line_nets, ZERO)
        if abs(calculated - invoice.net) > policy.amount_rounding_allowance:
            findings.append(finding("LINE_TOTAL_RECONCILIATION_FAILED", "REVIEW", "Invoice lines do not reconcile to net",
                                    f"Invoice line net sum {calculated} differs from stated invoice net {invoice.net}.",
                                    owner="Vendor", action="Request itemized invoice lines consistent with the stated net amount."))
    for i, line in enumerate(invoice.lines):
        if all(value is not None for value in (line.qty, line.unit_price_net, line.net)):
            if abs(line.qty * line.unit_price_net - line.net) > policy.amount_rounding_allowance:
                findings.append(finding("LINE_TOTAL_RECONCILIATION_FAILED", "REVIEW", "Line amount differs from quantity times price",
                                        f"Invoice line {i + 1} does not reconcile to its stated quantity and unit price.",
                                        owner="Vendor", action="Ask the vendor to correct the item's quantity, unit price or line amount."))
    return tuple(findings)


def remaining_commitment(context: EvaluationContextV1, policy: PolicyV1):
    po = context.selected_po
    if not same_currency(context) or context.invoice.net is None:
        return ()
    prior = sum((b.net for b in billed_for_po(context)), ZERO)
    remaining = po.authorized_net - prior
    if context.invoice.net > remaining:
        excess = context.invoice.net - remaining
        return (finding("PO_BALANCE_EXCEEDED", "BLOCK", "Invoice exceeds remaining PO commitment",
                        f"{po.id} authorizes net {po.authorized_net}; prior billed net is {prior}; "
                        f"remaining net is {remaining}. This invoice requests net {context.invoice.net}, excess {excess}.",
                        source="procurement_and_billed_ledger", owner="Procurement",
                        action="Request a corrected invoice or have Procurement approve an authorized PO amendment; re-evaluate afterward.",
                        po_id=po.id, authorized_net=po.authorized_net, prior_billed_net=prior,
                        remaining_net=remaining, requested_net=context.invoice.net, excess_net=excess),)
    return ()


def item_mapping(context: EvaluationContextV1, policy: PolicyV1):
    po = context.selected_po
    known = {normalized(line.item_code) for line in po.lines} if po else set()
    unresolved = [str(i + 1) for i, line in enumerate(context.invoice.lines)
                  if not normalized(line.item_code) or normalized(line.item_code) not in known]
    if unresolved:
        return (finding("LINE_MAPPING_UNRESOLVED", "REVIEW", "Invoice items are not mapped to authorized PO scope",
                        "Invoice lines requiring item-code/PO clarification: " + ", ".join(unresolved),
                        source="procurement", action="Obtain item codes or itemized scope and verify each line against the intended PO."),)
    return ()


def remaining_quantities(context: EvaluationContextV1, policy: PolicyV1):
    findings = []
    for po_line, lines in line_groups(context):
        # Missing/invalid quantities remain unresolved under other isolated rules.
        if not lines or any(line.qty is None or line.qty <= 0 for _, line in lines):
            continue
        prior = sum((line.qty for b in billed_for_po(context) for line in b.lines
                     if normalized(line.item_code) == normalized(po_line.item_code)), ZERO)
        requested = sum((line.qty for _, line in lines), ZERO)
        remaining = po_line.ordered_qty - prior
        if requested > remaining:
            findings.append(finding("PO_QUANTITY_EXCEEDED", "BLOCK", "Invoice exceeds remaining item quantity",
                                    f"{po_line.item_code}: ordered {po_line.ordered_qty}, previously billed {prior}, "
                                    f"remaining {remaining}, requested {requested}.",
                                    source="procurement_and_billed_ledger", owner="Procurement",
                                    action="Request a corrected item quantity or an authorized PO amendment; re-evaluate afterward.",
                                    item_code=po_line.item_code, prior_billed_qty=prior, remaining_qty=remaining,
                                    requested_qty=requested, excess_qty=requested - remaining))
    return tuple(findings)


def remaining_line_commitments(context: EvaluationContextV1, policy: PolicyV1):
    if not same_currency(context):
        return ()
    findings = []
    for po_line, lines in line_groups(context):
        amounts = tuple(calculated_net(line) for _, line in lines)
        if not amounts or any(value is None or value < 0 for value in amounts):
            continue
        prior = sum((line.line_net for b in billed_for_po(context) for line in b.lines
                     if normalized(line.item_code) == normalized(po_line.item_code)), ZERO)
        remaining = po_line.authorized_net - prior
        requested = sum(amounts, ZERO)
        if requested > remaining:
            findings.append(finding("PO_LINE_BALANCE_EXCEEDED", "BLOCK", "Invoice exceeds the item's remaining commitment",
                                    f"{po_line.item_code}: remaining line net {remaining}, requested line net {requested}.",
                                    source="procurement_and_billed_ledger", owner="Procurement",
                                    action="Correct the item amount or obtain an authorized PO line amendment; re-evaluate afterward.",
                                    item_code=po_line.item_code, remaining_net=remaining,
                                    requested_net=requested, excess_net=requested - remaining))
    return tuple(findings)


def unit_price_tolerance(context: EvaluationContextV1, policy: PolicyV1):
    if not same_currency(context):
        return ()
    findings = []
    for po_line, lines in line_groups(context):
        for index, line in lines:
            if line.unit_price_net is None or line.unit_price_net < 0:
                continue
            # Cross multiplication avoids recurring division and float percentages.
            if abs(line.unit_price_net - po_line.unit_price_net) > po_line.unit_price_net * policy.price_tolerance_pct:
                findings.append(finding("PRICE_VARIANCE", "REVIEW", "Unit price is outside policy tolerance",
                                        f"Invoice line {index + 1} price {line.unit_price_net} versus PO price "
                                        f"{po_line.unit_price_net}; allowed variation {policy.price_tolerance_pct * 100}%.",
                                        source="policy_and_procurement", owner="Procurement",
                                        action="Confirm the agreed unit price or request a corrected invoice.",
                                        item_code=po_line.item_code, invoice_price=line.unit_price_net,
                                        po_price=po_line.unit_price_net, tolerance_pct=policy.price_tolerance_pct))
    return tuple(findings)
