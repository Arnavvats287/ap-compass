from io import BytesIO
import json

import pytest
from reportlab.pdfgen.canvas import Canvas

from app.contracts import PolicyV1
from app.documents.evidence import ground_evidence
from app.documents.inspection import inspect_pdf
from app.documents.schema import parse_response
from app.domain import build_context, evaluate
from test_finance_engine import HISTORY, POS, VENDORS


def specimen(*, appendix=False, conflict=False, late_identity=False, extra_line=False):
    stream = BytesIO()
    pdf = Canvas(stream, invariant=1)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(45, 775, "Orion Office Products")
    pdf.setFont("Helvetica", 10)
    rows = (
        (740, ((45, "Invoice No.: DEV-490"), (265, "Purchase order: PO-6001"))),
        (715, ((45, "Invoice date: 2026-11-05"), (265, "Currency: INR"))),
        (600, tuple(zip((45, 155, 315, 375, 465),
                       ("Item code", "Description", "Qty", "Unit net", "Line net")))),
        (575, tuple(zip((45, 155, 315, 375, 465),
                       ("OR-SUPPLY-01", "Stationery kits", "3", "1,000.00", "3,000.00")))),
        (530, ((332, "Net subtotal"), (465, "3,000.00"))),
        (508, ((332, "Tax (18%)"), (465, "540.00"))),
        (486, ((332, "Invoice total"), (465, "3,540.00"))),
    )
    for y, cells in rows:
        for x, text in cells:
            pdf.drawString(x, y, text)
    if extra_line:
        for x, text in zip((45, 155, 315, 375, 465),
                           ("OR-SUPPLY-01", "Service period B", "2", "1,000.00", "2,000.00")):
            pdf.drawString(x, 551, text)
    if late_identity:
        pdf.drawString(45, 420, "Invoice date: 2026-11-07")
    if appendix or conflict:
        pdf.showPage()
        pdf.drawString(45, 775, "Account summary")
        pdf.drawString(45, 745, "Combined account balance")
        pdf.drawString(260, 745, "7,000.00")
        if conflict:
            pdf.drawString(45, 710, "Revised invoice total: INR 6,700.00")
    pdf.save()
    printed = dict(vendor_name_raw="Orion Office Products", invoice_number="DEV-490",
                   invoice_date="2026-11-05", po_reference="PO-6001", currency="INR",
                   net="3,000.00", tax="540.00", total="3,540.00")
    row = dict(item_code="OR-SUPPLY-01", description="Stationery kits",
               qty="3", unit_price_net="1,000.00", net="3,000.00")
    claims = {**printed, **{f"lines[0].{field}": value for field, value in row.items()}}
    invoice = dict(**printed, lines=[row], bank_instructions=None, evidence=[
        dict(field=field, page=1, raw_value=value, quote=value) for field, value in claims.items()
    ])
    return stream.getvalue(), invoice


def assess(pdf, wire):
    invoice = ground_evidence(*parse_response(json.dumps(wire)), inspect_pdf(pdf))
    decision = evaluate(build_context(invoice, VENDORS, POS, HISTORY), PolicyV1())
    return {ref.field: ref for ref in invoice.evidence}, decision


@pytest.mark.parametrize("appendix", [False, True])
def test_independent_short_references_complete_a_one_row_invoice(appendix):
    refs, decision = assess(*specimen(appendix=appendix))
    assert decision.outcome == "READY_FOR_AP"
    assert {ref.evidence_state for ref in refs.values()} == {"NATIVE_VERIFIED"}
    assert refs["invoice_number"].quote == "Invoice No.: DEV-490"
    assert refs["lines[0].qty"].quote.startswith("OR-SUPPLY-01 Stationery kits 3")


@pytest.mark.parametrize("field,quote", [
    ("invoice_number", "PO-6001"), ("total", "7,000.00"),
    ("lines[0].qty", "1,000.00"),
])
def test_short_references_cannot_borrow_other_printed_fields(field, quote):
    pdf, invoice = specimen(appendix=True)
    next(ref for ref in invoice["evidence"] if ref["field"] == field)["quote"] = quote
    refs, decision = assess(pdf, invoice)
    assert refs[field].evidence_state != "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("issue,field", [("conflict", "total"), ("late_identity", "invoice_date")])
def test_competing_printed_values_remain_unresolved(issue, field):
    refs, decision = assess(*specimen(**{issue: True}))
    assert refs[field].evidence_state != "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


def test_a_single_extracted_row_cannot_hide_another_printed_charge():
    refs, decision = assess(*specimen(extra_line=True))
    assert refs["lines[0].qty"].evidence_state != "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


def test_a_verified_invoice_cell_does_not_validate_a_claim_on_the_wrong_page():
    pdf, invoice = specimen(appendix=True)
    next(ref for ref in invoice["evidence"] if ref["field"] == "invoice_number")["page"] = 2
    refs, decision = assess(pdf, invoice)
    assert refs["invoice_number"].evidence_state != "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"
