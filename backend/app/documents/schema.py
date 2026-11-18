"""Small private model-output schema. The model cannot choose evidence states."""
import re
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from app.contracts import BankInstructionsV1, ExtractedInvoiceV1, InvoiceLineV1
from .types import ExtractionError

Text = Annotated[str, StringConstraints(max_length=600)]
Number = Annotated[str, StringConstraints(pattern=r"^-?\d{1,18}(?:\.\d{1,6})?$", max_length=26)]
FieldKey = Annotated[str, StringConstraints(pattern=(
    r"^(vendor_name_raw|invoice_number|invoice_date|po_reference|currency|net|tax|total|"
    r"lines\[\d{1,2}\]\.(description|item_code|qty|unit_price_net|net)|bank_instructions\.(account|ifsc))$"
))]


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)


class SourceClaim(WireModel):
    field: FieldKey
    page: int | None = Field(ge=1, le=10)
    raw_value: Text | None
    quote: Text | None


class WireLine(WireModel):
    description: Text | None
    item_code: Text | None
    qty: Number | None
    unit_price_net: Number | None
    net: Number | None


class WireBank(WireModel):
    account: Text | None
    ifsc: Text | None


class WireInvoice(WireModel):
    vendor_name_raw: Text | None
    invoice_number: Text | None
    invoice_date: Text | None
    po_reference: Text | None
    currency: Text | None
    net: Number | None
    tax: Number | None
    total: Number | None
    lines: list[WireLine] = Field(max_length=50)
    bank_instructions: WireBank | None
    evidence: list[SourceClaim] = Field(max_length=260)


def provider_schema():
    """Keep generation grammar small; enforce every detailed bound locally."""
    omitted = {"title", "pattern", "maxLength", "maxItems", "minimum", "maximum"}
    def simplify(value):
        if isinstance(value, dict):
            return {key: simplify(item) for key, item in value.items() if key not in omitted}
        if isinstance(value, list):
            return [simplify(item) for item in value]
        return value
    return simplify(WireInvoice.model_json_schema())


def parse_response(response: str) -> tuple[ExtractedInvoiceV1, tuple[SourceClaim, ...]]:
    if not isinstance(response, str) or len(response.encode("utf-8")) > 256 * 1024:
        raise ExtractionError("INVALID_RESPONSE")
    try:
        wire = WireInvoice.model_validate_json(response)
        if wire.invoice_date is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", wire.invoice_date):
            raise ValueError("Date must be ISO")
        amount = lambda value: None if value is None else Decimal(value)
        bank = wire.bank_instructions
        # The frozen bank contract cannot represent partial nullable subfields.
        # Fail safely instead of filling missing details or declaring them absent.
        if bank is not None and (not bank.account or not bank.ifsc):
            raise ValueError("Incomplete bank instructions cannot satisfy the existing contract")
        invoice = ExtractedInvoiceV1(
            vendor_name_raw=wire.vendor_name_raw,
            vendor_name_normalized=None if wire.vendor_name_raw is None else " ".join(wire.vendor_name_raw.split()),
            invoice_number=wire.invoice_number,
            invoice_date=None if wire.invoice_date is None else date.fromisoformat(wire.invoice_date),
            po_reference=wire.po_reference, currency=wire.currency,
            net=amount(wire.net), tax=amount(wire.tax), total=amount(wire.total),
            lines=tuple(InvoiceLineV1(description=line.description, item_code=line.item_code,
                                    qty=amount(line.qty), unit_price_net=amount(line.unit_price_net), net=amount(line.net))
                        for line in wire.lines),
            bank_instructions=None if bank is None else BankInstructionsV1(account=bank.account, ifsc=bank.ifsc),
        )
        return invoice, tuple(wire.evidence)
    except (ValidationError, ValueError, ArithmeticError):
        raise ExtractionError("INVALID_RESPONSE") from None
