"""Missing/uncertain critical facts remain reviewable. No invented verification."""
from app.contracts import EvaluationContextV1, PolicyV1
from .common import finding, verified


def required_fields(context: EvaluationContextV1, policy: PolicyV1):
    invoice = context.invoice
    fields = ["vendor_name_raw", "invoice_number", "invoice_date", "currency", "net", "tax", "total"]
    if invoice.po_reference and invoice.po_reference.strip():
        fields.append("po_reference")
    missing = [name for name in fields if getattr(invoice, name) is None
               or (isinstance(getattr(invoice, name), str) and not getattr(invoice, name).strip())]
    if not invoice.lines:
        missing.append("lines")
    for index, line in enumerate(invoice.lines):
        for name in ("qty", "unit_price_net"):
            if getattr(line, name) is None:
                missing.append(f"lines[{index}].{name}")
    if missing:
        return (finding("CRITICAL_FIELD_MISSING", "REVIEW", "Required invoice facts are missing",
                        "Missing values remain unknown: " + ", ".join(missing), fields=", ".join(missing)),)
    return ()


def source_evidence(context: EvaluationContextV1, policy: PolicyV1):
    invoice = context.invoice
    fields = ["vendor_name_raw", "invoice_number", "invoice_date", "currency", "net", "tax", "total"]
    if invoice.po_reference and invoice.po_reference.strip():
        fields.append("po_reference")
    for index, line in enumerate(invoice.lines):
        for name in ("item_code", "qty", "unit_price_net", "net"):
            if getattr(line, name) is not None:
                fields.append(f"lines[{index}].{name}")
    unresolved = [name for name in fields if not verified(invoice, name)]
    if not unresolved:
        return ()
    return (finding("SOURCE_EVIDENCE_MISSING", "REVIEW", "Critical source evidence needs verification",
                    "Missing, unverified or inconsistent evidence for: " + ", ".join(unresolved),
                    evidence=tuple(ref for ref in invoice.evidence if ref.field in unresolved),
                    fields=", ".join(unresolved)),)
