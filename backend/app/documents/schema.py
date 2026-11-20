"""Small private model-output schema. The model cannot choose evidence states."""
import logging
import re
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from app.contracts import BankInstructionsV1, ExtractedInvoiceV1, InvoiceLineV1
from .types import ExtractionError

logger = logging.getLogger(__name__)

Text = Annotated[str, StringConstraints(max_length=600)]
DECIMAL_INSTRUCTION = "Plain decimal string such as 1234.50. No currency symbol, separators, units or exponents."
DECIMAL_PATTERN = r"^-?\d{1,18}(?:\.\d{1,6})?$"
Number = Annotated[
    str, StringConstraints(pattern=DECIMAL_PATTERN, max_length=26),
    Field(description=DECIMAL_INSTRUCTION),
]
EVIDENCE_KEY_PATTERN = (
    r"^(vendor_name_raw|invoice_number|invoice_date|po_reference|currency|net|tax|total|"
    r"lines\[\d{1,2}\]\.(description|item_code|qty|unit_price_net|net)|bank_instructions\.(account|ifsc))$"
)
FieldKey = Annotated[str, StringConstraints(pattern=EVIDENCE_KEY_PATTERN)]


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)


class SourceClaim(WireModel):
    field: FieldKey = Field(description=(
        "Exact application field key. Header keys: vendor_name_raw, invoice_number, invoice_date, "
        "po_reference, currency, net, tax, total. For a line use lines[0].item_code, lines[0].description, "
        "lines[0].qty, lines[0].unit_price_net or lines[0].net; begin at index 0. For bank facts use "
        "bank_instructions.account or bank_instructions.ifsc. Do not use printed labels as keys."
    ))
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



# These are application-owned names. Never interpolate unknown keys or a rejected value.
WIRE_FIELDS = frozenset().union(*(model.model_fields for model in (WireInvoice, WireLine, WireBank, SourceClaim)))
EVIDENCE_LEAVES = set(WireLine.model_fields) | {"quantity", "unit_price", "line_net", "line_total"}
EVIDENCE_SHAPES = (
    ("bracketed_line", re.compile(r"lines\[\d+\]\.([a-z_]+)", re.ASCII)),
    ("dotted_line", re.compile(r"lines\.\d+\.([a-z_]+)", re.ASCII)),
    ("plural_bracketed_line", re.compile(r"line_items\[\d+\]\.([a-z_]+)", re.ASCII)),
    ("singular_bracketed_line", re.compile(r"line\[\d+\]\.([a-z_]+)", re.ASCII)),
)


def wire_error_path(location):
    path = "$"
    for part in location[:5]:
        if type(part) is int and 0 <= part < 260:
            path += f"[{part}]"
        elif part in WIRE_FIELDS:
            path += f".{part}"
        else:
            return path + ".<unknown>"
    return path


def pattern_diagnostic(location, value):
    if location and location[0] == "evidence" and location[-1] == "field":
        shape = "noncanonical-key"
        if isinstance(value, str):
            for name, pattern in EVIDENCE_SHAPES:
                if match := pattern.fullmatch(value):
                    leaf = match[1] if match[1] in EVIDENCE_LEAVES else "unknown-leaf"
                    shape = f"{name}:{leaf}"
                    break
            else:
                if value in EVIDENCE_LEAVES:
                    shape = f"unqualified:{value}"
                elif re.fullmatch(r"lines\[\]\.[a-z_]+", value, re.ASCII):
                    shape = "omitted-line-index"
                elif any(char.isspace() for char in value):
                    shape = "space-separated-key"
        return "evidence_field_key", shape
    if (len(location) == 1 and location[0] in {"net", "tax", "total"}) or (
        len(location) == 3 and location[0] == "lines" and location[-1] in {"qty", "unit_price_net", "net"}
    ):
        # Symbols and counts only. Digits, currency names, and strings stay private.
        text = value if isinstance(value, str) else ""
        frac = re.search(r"\.([0-9]+)$", text)
        integer = re.match(r"^[+-]?([0-9]+)", text)
        markers = [label for present, label in (
            ("," in text, "comma"),
            (text != text.strip(), "edge-whitespace"),
            (bool(re.search(r"[0-9][eE][+-]?[0-9]", text)), "exponent"),
            (any(char.isalpha() for char in text), "letters"),
            (any(char in "$£€₹" for char in text), "currency-symbol"),
            (text.startswith("+"), "plus-sign"),
            (text.startswith((".", "-.")), "missing-integer"),
            (text.endswith("."), "missing-fraction"),
        ) if present]
        return "decimal_string", (
            f"text:length={len(text)};integer_digits={len(integer[1]) if integer else 0};"
            f"fraction_digits={len(frac[1]) if frac else 0};markers={','.join(markers) or 'none'}"
        )
    return "unclassified_pattern", "redacted"


def log_wire_rejection(errors):
    for issue in errors[:20]:
        location = issue["loc"]
        kind = issue["type"]
        if kind == "string_pattern_mismatch":
            constraint, shape = pattern_diagnostic(location, issue["input"])
            logger.warning("wire_schema path=%s issue=string_pattern_mismatch constraint=%s shape=%s",
                           wire_error_path(location), constraint, shape)
        else:
            # Error types come from our own Pydantic models, not the response.
            logger.warning("wire_schema path=%s issue=%s", wire_error_path(location), kind)


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
        raise ExtractionError("MODEL_OUTPUT_SCHEMA")
    try:
        wire = WireInvoice.model_validate_json(response)
    except ValidationError as error:
        # Pydantic distinguishes bad JSON before validating the wire fields.
        # Classify rejected values in memory. The log contains only static names and shapes.
        errors = error.errors(include_input=True, include_context=False, include_url=False)
        malformed = any(item["type"] == "json_invalid" for item in errors)
        if not malformed:
            log_wire_rejection(errors)
        code = "MODEL_OUTPUT_JSON" if malformed else "MODEL_OUTPUT_SCHEMA"
        raise ExtractionError(code) from None
    try:
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
        raise ExtractionError("MODEL_OUTPUT_SCHEMA") from None
