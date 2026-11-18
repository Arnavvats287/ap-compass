"""Pure identity resolution. Balances, status and price policy never filter POs."""
from collections.abc import Sequence

from app.contracts import (
    EvaluationContextV1, ExtractedInvoiceV1, POCandidateV1,
    PriorBilledInvoiceV1, PurchaseOrderV1, VendorV1,
)
from .common import normalized


def resolve_vendor(name: str | None, vendors: Sequence[VendorV1]) -> VendorV1 | None:
    key = normalized(name)
    if not key:
        return None
    matches = [v for v in vendors if key in {normalized(v.name), *(normalized(a) for a in v.aliases)}]
    # Colliding aliases stay unresolved regardless of input order.
    return matches[0] if len(matches) == 1 else None


def build_context(
    invoice: ExtractedInvoiceV1,
    vendors: Sequence[VendorV1],
    procurement_records: Sequence[PurchaseOrderV1],
    prior_billed_records: Sequence[PriorBilledInvoiceV1],
) -> EvaluationContextV1:
    """Use trusted masters. Rank exact code overlap, never financial eligibility.

    Missing reference: retrieve all same-vendor POs. Ties stay unresolved. Rank
    is ordinal, not confidence. A recommendation does not confirm a missing PO.
    """
    vendor = resolve_vendor(invoice.vendor_name_raw, vendors)
    pos = tuple(sorted(procurement_records, key=lambda p: p.id))
    explicit = normalized(invoice.po_reference)
    selected = None
    provenance = None
    candidates = ()
    if explicit:
        matches = [p for p in pos if normalized(p.id) == explicit]
        if len(matches) == 1:
            selected = matches[0]
            provenance = "Explicit invoice PO reference; financial eligibility not yet checked"
            candidates = (POCandidateV1(po=selected, selection_provenance=provenance, rank=1),)
    elif vendor:
        invoice_codes = {normalized(line.item_code) for line in invoice.lines if line.item_code}

        def overlap(po):
            return len(invoice_codes & {normalized(line.item_code) for line in po.lines})

        same_vendor = sorted((p for p in pos if p.vendor_id == vendor.id),
                             key=lambda p: (-overlap(p), p.id))
        candidates = tuple(POCandidateV1(
            po=po, rank=1 + sum(overlap(other) > overlap(po) for other in same_vendor),
            selection_provenance=(f"Canonical vendor {vendor.id}; exact item-code overlaps: {overlap(po)}; "
                                  "no financial eligibility filtering"),
        ) for po in same_vendor)
        top = [c for c in candidates if c.rank == 1]
        if len(top) == 1:
            selected = top[0].po
            provenance = "Unambiguous same-vendor candidate; " + top[0].selection_provenance
    return EvaluationContextV1(
        invoice=invoice, canonical_vendor=vendor, candidates=candidates,
        selected_po=selected, selection_provenance=provenance,
        prior_billed_records=tuple(sorted(prior_billed_records, key=lambda b: b.id)),
        procurement_records=pos,
    )
