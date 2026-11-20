"""Native stacked item tables using the real PDF parser and financial engine."""
from io import BytesIO

import pytest
from reportlab.pdfgen.canvas import Canvas

from test_source_generalization import assess


def specimen(*, conflict=False, currency="INR", missing_sku=False, unauthorized=False,
             duplicate_summary=False, competing_issue_date=False):
    buf = BytesIO()
    doc = Canvas(buf, invariant=1)

    def row(y, cells):
        for x, value in cells:
            doc.drawString(x, y, value)

    doc.setFont("Helvetica-Bold", 20)
    row(765, [(44, "Orion Office Products")])
    doc.setFont("Helvetica", 10)
    row(725, [(44, "Invoice"), (225, "Issued"), (402, "Due")])
    row(709, [(44, "FIELD-490"), (225, "2026-11-05"), (402, "2026-12-05")])
    row(668, [(44, "PO reference"), (150, "PO-6001")])
    row(628, [(44, "Item / stock code"), (285, "Packs"), (368, "Net / pack"), (485, "Extended net")])

    amounts = [("Desk supplies", "OR-SUPPLY-01", "3", "3,000.00"),
               ("Filing supplies", "OUTSIDE-7" if unauthorized else "OR-SUPPLY-01", "2", "2,000.00")]
    for index, (description, sku, qty, value) in enumerate(amounts):
        y = 600 - 43 * index
        row(y, [(44, description), (285, qty), (368, "1,000.00"), (485, value)])
        if not missing_sku or index == 0:
            row(y - 15, [(44, sku)])

    row(485, [(44, f"Subtotal ({currency})"), (218, f"GST 18% ({currency})"), (395, "Balance due")])
    row(468, [(44, "5,000.00"), (218, "900.00"), (395, f"{currency} 5,900.00")])
    if conflict:
        row(420, [(45, "Grand Total: INR 6,700.00")])
    if competing_issue_date:
        row(422, [(44, "Invoice date: 2026-11-07")])
    if duplicate_summary:
        row(420, [(44, "Account statement")])
        row(400, [(44, "Subtotal (INR)"), (218, "GST 18% (INR)"), (395, "Balance due")])
        row(383, [(44, "6,000.00"), (218, "1,080.00"), (395, "INR 7,080.00")])
    doc.save()

    invoice = dict(vendor_name_raw="Orion Office Products", invoice_number="FIELD-490",
                   invoice_date="2026-11-05", po_reference="PO-6001", currency="INR",
                   net="5000", tax="900", total="5900", lines=[], bank_instructions=None, evidence=[])

    def claim(field, raw, quote=None):
        invoice["evidence"].append(dict(field=field, page=1, raw_value=raw, quote=quote or raw))

    for name in ("vendor_name_raw", "invoice_number", "invoice_date", "po_reference"):
        claim(name, invoice[name])
    claim("currency", "INR", f"Subtotal ({currency})")
    claim("net", "5,000.00")
    claim("tax", "900.00")
    claim("total", "5,900.00", f"{currency} 5,900.00")
    for index, (description, sku, qty, value) in enumerate(amounts):
        line = dict(description=description, item_code=sku, qty=qty, unit_price_net="1000", net=value.replace(",", ""))
        invoice["lines"].append(line)
        for name in line:
            claim(f"lines[{index}].{name}", {"unit_price_net": "1,000.00", "net": value}.get(name, line[name]))
    return buf.getvalue(), invoice


def test_short_quotes_use_independent_header_and_stacked_row_locations():
    states, decision = assess(*specimen())
    assert set(states.values()) == {"NATIVE_VERIFIED"}
    assert decision.outcome == "READY_FOR_AP"


@pytest.mark.parametrize("mode", [
    "wrong_row", "wrong_field", "wrong_date", "same_value_other_role", "competing_gross",
    "duplicate_summary", "competing_issue_date", "currency", "missing_sku", "omitted_row",
])
def test_stacked_recognition_fails_closed(mode):
    pdf, invoice = specimen(conflict=mode == "competing_gross",
                            currency="USD" if mode == "currency" else "INR",
                            missing_sku=mode == "missing_sku", duplicate_summary=mode == "duplicate_summary",
                            competing_issue_date=mode == "competing_issue_date")
    target = {"wrong_date": "invoice_date", "competing_issue_date": "invoice_date", **dict.fromkeys(
        ("wrong_field", "same_value_other_role", "competing_gross", "currency", "duplicate_summary"), "total"
    )}.get(mode, "lines[0].qty")
    ref = next(ref for ref in invoice["evidence"] if ref["field"] == target)
    if mode == "wrong_row":
        invoice["lines"][0]["qty"] = ref["raw_value"] = ref["quote"] = "2"
    if mode == "wrong_field":
        ref["quote"] = "5,000.00"
    if mode == "wrong_date":
        ref["quote"] = "2026-12-05"
    if mode == "same_value_other_role":
        ref["quote"] = "Payment account total INR 5,900.00"
    if mode == "omitted_row":
        invoice["lines"].pop()
        invoice["evidence"] = [e for e in invoice["evidence"] if not e["field"].startswith("lines[1]")]
    states, decision = assess(pdf, invoice)
    assert states[target] != "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


def test_verified_unauthorized_stacked_line_does_not_clear():
    states, decision = assess(*specimen(unauthorized=True))
    assert states["lines[1].item_code"] == "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"
    finding = next(f for f in decision.findings if f.code == "LINE_MAPPING_UNRESOLVED")
    assert finding.owner == "Procurement"

@pytest.mark.parametrize("field,value", [("invoice_number", "OUTSIDE-7"), ("po_reference", "FIELD-490")])
def test_real_identifiers_do_not_verify_in_a_different_role(field, value):
    pdf, invoice = specimen(unauthorized=True)
    invoice[field] = value
    next(ref for ref in invoice["evidence"] if ref["field"] == field).update(raw_value=value, quote=value)
    states, decision = assess(pdf, invoice)
    assert states[field] != "NATIVE_VERIFIED"
    assert decision.outcome != "READY_FOR_AP"
