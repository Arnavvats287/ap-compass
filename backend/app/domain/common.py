"""Shared value helpers, without I/O or decision aggregation."""
import re
from decimal import Decimal

from app.contracts import ExtractedInvoiceV1, FindingV1, FindingValueV1


def normalized(value: str | None) -> str:
    """Case/whitespace only; never invent aliases or merge punctuation."""
    return " ".join((value or "").split()).casefold()


def finding(code, severity, title, explanation, *, source="invoice", owner="AP",
            action="Verify the source invoice and request clarification from the vendor.",
            evidence=(), **values) -> FindingV1:
    return FindingV1(
        code=code, severity=severity, title=title, explanation=explanation,
        source_type=source, owner=owner if severity in ("REVIEW", "BLOCK") else None,
        next_action=action if severity in ("REVIEW", "BLOCK") else None,
        evidence_refs=tuple(evidence),
        values=tuple(FindingValueV1(name=k, value=None if v is None else str(v))
                     for k, v in values.items()),
    )


def field_value(invoice: ExtractedInvoiceV1, field: str):
    line = re.fullmatch(r"lines\[(\d+)\]\.(item_code|qty|unit_price_net|net)", field)
    if line:
        index = int(line[1])
        return getattr(invoice.lines[index], line[2]) if index < len(invoice.lines) else None
    if field.startswith("bank_instructions."):
        return getattr(invoice.bank_instructions, field.split(".")[1], None)
    return getattr(invoice, field, None)


def verified(invoice: ExtractedInvoiceV1, field: str) -> bool:
    """Consume source adapter attestation; never verify a document here."""
    refs = [ref for ref in invoice.evidence if ref.field == field]
    value = field_value(invoice, field)
    if value is None or len(refs) != 1:
        return False
    ref = refs[0]
    if not (ref.evidence_state == "NATIVE_VERIFIED" and ref.route == "native_text"
            and ref.page is not None and ref.quote and ref.quote.strip()
            and ref.raw_value and ref.raw_value.strip()
            and ref.normalized_value and ref.normalized_value.strip()):
        return False
    if isinstance(value, Decimal):
        try:
            return Decimal(ref.normalized_value) == value
        except ArithmeticError:
            return False
    return normalized(ref.normalized_value) == normalized(str(value))
