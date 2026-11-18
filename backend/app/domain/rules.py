"""Independent identity and eligibility rules, returning immutable findings."""
from app.contracts import EvaluationContextV1, PolicyV1
from .common import finding, normalized


def vendor_requirement(context: EvaluationContextV1, policy: PolicyV1):
    vendor = context.canonical_vendor
    if vendor is None or not vendor.approved:
        return (finding("VENDOR_UNVERIFIED", "REVIEW", "Supplier approval is unresolved",
                        "The invoice supplier is not uniquely resolved to an approved canonical vendor.",
                        source="vendor_master", owner="Procurement",
                        action="Verify the supplier and approved vendor record before AP processing."),)
    return ()


def po_identity(context: EvaluationContextV1, policy: PolicyV1):
    findings = []
    if not normalized(context.invoice.po_reference) and policy.require_explicit_po:
        findings.append(finding("PO_REFERENCE_MISSING", "REVIEW", "Invoice has no explicit PO reference",
                                "A candidate recommendation does not confirm the invoice's purchase order.",
                                action="Ask the vendor for the correct PO reference and verify it."))
    top = [c for c in context.candidates if c.rank == 1]
    if context.selected_po is None and len(top) > 1:
        findings.append(finding("PO_AMBIGUOUS", "REVIEW", "More than one purchase order is plausible",
                                "Identity evidence cannot distinguish these POs: " + ", ".join(c.po.id for c in top),
                                source="procurement", action="Confirm the intended PO with Procurement and the vendor."))
    elif context.selected_po is None:
        findings.append(finding("PO_NOT_FOUND", "REVIEW", "Purchase order could not be identified",
                                "No unique authoritative PO matches the supplied identity facts.",
                                source="procurement", owner="Procurement",
                                action="Obtain the correct PO reference and verify the authorized procurement record."))
    else:
        findings.append(finding("PO_MATCH_CONFIRMED", "PASS", "Purchase order identified",
                                f"{context.selected_po.id}: {context.selection_provenance}. Eligibility is checked separately.",
                                source="procurement", po_id=context.selected_po.id))
    return tuple(findings)


def vendor_po_consistency(context: EvaluationContextV1, policy: PolicyV1):
    vendor, po = context.canonical_vendor, context.selected_po
    if vendor and po and vendor.id != po.vendor_id:
        return (finding("VENDOR_PO_CONFLICT", "BLOCK", "Invoice supplier and PO supplier conflict",
                        f"The identified PO {po.id} belongs to a different canonical vendor.",
                        source="procurement", owner="Procurement",
                        action="Resolve the supplier/PO contradiction; obtain a corrected invoice or authorized PO.",
                        po_id=po.id),)
    return ()


def po_status(context: EvaluationContextV1, policy: PolicyV1):
    po = context.selected_po
    if po and normalized(po.status) != "open":
        return (finding("PO_CLOSED", "BLOCK", "Purchase order is not open for billing",
                        f"{po.id} has status {po.status}; identification does not establish eligibility.",
                        source="procurement", owner="Procurement",
                        action="Have Procurement verify the PO status and authorization before resubmission.", po_id=po.id),)
    return ()


def currency_compatibility(context: EvaluationContextV1, policy: PolicyV1):
    po = context.selected_po
    if po and context.invoice.currency and normalized(po.currency) != normalized(context.invoice.currency):
        return (finding("CURRENCY_MISMATCH", "BLOCK", "Invoice and purchase order currencies differ",
                        f"Invoice currency {context.invoice.currency} cannot be compared with PO currency {po.currency}.",
                        source="procurement", owner="Procurement",
                        action="Obtain a corrected invoice or confirm a PO authorized in the correct currency."),)
    return ()
