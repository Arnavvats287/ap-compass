"""Controlled provider replies backed by printed text, with no trust state."""
from decimal import Decimal
import re

import pymupdf

from app.documents.schema import SourceClaim, WireInvoice
from app.documents.types import ProviderReply
from benchmark_inputs import HEADER, LINE_FIELDS, wire_facts


LABELS = {
    "vendor_name_raw": ("supplier", "vendor", "from"),
    "invoice_number": ("invoice number", "invoice no", "invoice #"),
    "invoice_date": ("invoice date", "date"),
    "po_reference": ("purchase order", "po reference", "po number", "po"),
    "currency": ("currency",),
    "net": ("net subtotal", "invoice net", "net amount", "subtotal", "taxable amount"),
    "tax": ("tax", "gst", "vat"),
    "total": ("invoice total", "current invoice total", "grand total", "gross total"),
    "description": (),
    "item_code": ("item code", "sku"),
    "qty": ("quantity", "qty"),
    "unit_price_net": ("unit price (net)", "unit net price", "net unit price"),
    "line_net": ("line net", "line amount"),
    "account": ("account number", "bank account"),
    "ifsc": ("ifsc",),
}
DECIMAL_FIELDS = {"qty", "net", "tax", "total", "unit_price_net", "line_net"}
PRINTED_AMOUNT = re.compile(r"(?<![\w,.])-?\d+(?:,\d+)*(?:\.\d+)?(?![\w,.])")


def plain(text):
    return " ".join(text.split())


def value_excerpt(text, value, numeric):
    if numeric:
        return next((m.group() for m in PRINTED_AMOUNT.finditer(text)
                     if Decimal(m.group().replace(",", "")) == Decimal(value)), None)
    match = re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", text, re.I)
    return match.group() if match else None


def claims_for(case, raw, annotation):
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        if len(pdf) != case["pdf"]["page_count"]:
            raise ValueError("PDF page count differs from registry")
        pages = {page.number + 1: page.get_text().splitlines() for page in pdf}
    for page, lines in annotation.get("image_text", {}).items():
        if int(page) not in pages:
            raise ValueError("Invalid transcribed page reference")
        pages[int(page)] += lines
    rows = [(page, plain(text)) for page, lines in pages.items() for text in lines if text.strip()]
    wire = wire_facts(case)

    def locate(field, leaf, value, scope):
        if value is None:
            return None
        numeric = leaf in DECIMAL_FIELDS
        if override := annotation.get("field_sources", {}).get(field):
            page, quote = override["page"], plain(override["quote"])
            # View order can split table cells into successive native lines.
            raw_value = value_excerpt(quote, value, numeric)
            if page not in pages or quote not in plain(" ".join(pages[page])) or raw_value is None:
                raise ValueError(f"Unsupported source override for {case['case_id']} {field}")
            return SourceClaim(field=field, page=page, raw_value=raw_value, quote=quote)
        for page, quote in scope:
            label, separator, tail = quote.partition(":")
            key = label.casefold().strip().rstrip(".")
            # Tax prose often includes the tax type or the published rate.
            if leaf == "tax":
                key = key.split("(", 1)[0].strip()
            if separator and key in LABELS[leaf]:
                exact = value_excerpt(tail, value, numeric)
            elif leaf in {"description", "vendor_name_raw"} and quote.casefold() == value.casefold():
                exact = quote
            else:
                continue
            if exact is not None:
                return SourceClaim(field=field, page=page, raw_value=exact, quote=quote)
        raise ValueError(f"Present fact lacks an audited printed claim for {case['case_id']} {field}")

    claims = [locate(field, field, getattr(wire, field), rows) for field in HEADER]
    anchors = [i for i, (_, text) in enumerate(rows)
               if text.partition(":")[0].casefold().strip() in LABELS["item_code"]]
    for index, line in enumerate(wire.lines):
        scope = rows
        if len(anchors) == len(wire.lines):
            stop = anchors[index + 1] - 1 if index + 1 < len(anchors) else len(rows)
            scope = rows[max(0, anchors[index] - 1):stop]
        for leaf in LINE_FIELDS:
            claims.append(locate(f"lines[{index}].{leaf}", "line_net" if leaf == "net" else leaf,
                                 getattr(line, leaf), scope))
    if wire.bank_instructions:
        for leaf in ("account", "ifsc"):
            claims.append(locate(f"bank_instructions.{leaf}", leaf, getattr(wire.bank_instructions, leaf), rows))
    return {claim.field: claim for claim in claims if claim is not None}


class ControlledProvider:
    model_id = "TEST_ONLY-benchmark-wire-v1"

    def __init__(self, case, claims):
        data = wire_facts(case).model_dump()
        data["evidence"] = [claim.model_dump() for claim in claims.values()]
        self.reply = WireInvoice.model_validate(data).model_dump_json()
        self.calls = 0

    async def generate(self, document, timeout_seconds):
        self.calls += 1
        return ProviderReply(self.reply, self.model_id)
