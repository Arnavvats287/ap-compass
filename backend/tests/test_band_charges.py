import json
from io import BytesIO
from pathlib import Path

import pytest
from reportlab.pdfgen.canvas import Canvas

from app.ai.gemini import extraction_instruction
from app.ai.provider import SERVICE_PERIOD_INSTRUCTION, SYSTEM_INSTRUCTION
from app.documents.band_charges import band_charges
from app.documents.evidence import ground_evidence
from app.documents.inspection import inspect_pdf
from app.documents.schema import parse_response
from app.documents.source_layout import rows_for


def service_pdf(variant=None):
    stream = BytesIO()
    pdf = Canvas(stream, pagesize=(800, 620), invariant=1)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(35, 570, "Meridian Cloud")
    pdf.drawString(35, 550, "Pvt Ltd")
    pdf.drawString(35, 533, "Service invoice")
    pdf.drawString(257, 578, "Bill To")
    pdf.drawString(257, 557, "Juniper Works India Pvt Ltd")
    pdf.drawString(257, 520, "Service period / Item")
    for y, text in ((486, "Invoice number"), (462, "TEST-1284"),
                    (440, "Service date" if variant == "no_issued" else "Issued"), (418, "31 Oct 2026"),
                    (396, "Customer PO"), (374, "PO-1042"), (352, "Billing currency"), (330, "INR"),
                    (300, "Due: 30 Nov 2026"), (280, "Customer reference: PO-9999"),
                    (260, "Prior balance: 5,000.00")):
        pdf.drawString(35, y, text)
    if competing := {"date_conflict": "Invoice date: 10 Nov 2026",
                     "po_conflict": "Purchase order: PO-9999",
                     "net_conflict": "Invoice net: 5,000.00",
                     "vendor_conflict": "Seller: Another Company Ltd",
                     "statement_context": "Account summary"}.get(variant):
        pdf.drawString(35, 340 if variant == "statement_context" else 235, competing)
    for x, heading in ((559, "Qty"), (637, "Net rate"),
                       (727, "Line net (USD)" if variant == "usd" else "Line net")):
        pdf.drawRightString(x, 520, heading)
    for anchor_y, period, qty, net in ((465, "11-18 Oct 2026", "4", "20000.00"),
                                      (405, "19-31 Oct 2026", "6", "30000.00")):
        caption = period if anchor_y == 465 or variant != "money_caption" else "Handling INR 125.00"
        pdf.drawString(257, anchor_y + 21, caption)
        pdf.drawString(257, anchor_y, "MC-CLOUD-01 / Cloud hosting service")
        for x, value in ((559, qty), (637, "5000.00"), (727, net)):
            pdf.drawRightString(x, anchor_y + 11, value)
    if variant == "unlabeled":
        pdf.drawRightString(727, 350, "125.00")
    elif variant == "unmapped":
        pdf.drawString(395, 350, "Expedited handling")
        pdf.drawRightString(727, 350, "125.00")
    for y, label, amount in ((330, "Net service charges", "50,000.00"),
                             (310, "GST 18%", "9,000.00"),
                             (290, "Invoice total", "INR 59,000.00")):
        pdf.drawRightString(596, y, label)
        pdf.drawRightString(727, y, amount)
    pdf.drawRightString(727, 50, "1 / 1")
    pdf.save()
    return stream.getvalue()


HEADER_FACTS = {
    "vendor_name_raw": ("Meridian Cloud Pvt Ltd", "Meridian Cloud Pvt Ltd", "Meridian Cloud Pvt Ltd"),
    "invoice_date": ("2026-10-31", "31 Oct 2026", "31 Oct 2026"),
    "po_reference": ("PO-1042", "PO-1042", "PO-1042"),
    "net": ("50000.00", "50,000.00", "Net service charges 50,000.00"),
}


def extract_lines(doc, mutation=None, *, header_facts=None):
    rows = [
        dict(item_code="MC-CLOUD-01", description="Cloud hosting service",
             qty=qty, unit_price_net="5000.00", net=net)
        for qty, net in (("4", "20000.00"), ("6", "30000.00"))
    ]
    if mutation == "omit":
        rows.pop()
    elif mutation == "duplicate":
        rows[1] = rows[0].copy()
    elif mutation == "swap_quantity":
        rows[1]["qty"] = rows[0]["qty"]
    claims = [dict(field=f"lines[{index}].{field}", page=1, raw_value=value,
                   quote="4" if mutation == "swap_quote" and index == 1 and field == "qty" else value)
              for index, row in enumerate(rows) for field, value in row.items()]
    reply = dict(vendor_name_raw="Meridian Cloud Pvt Ltd", invoice_number="TEST-1284",
                 invoice_date=None, po_reference="PO-1042", currency="INR", net="50000.00",
                 tax="9000.00", total="59000.00", lines=rows, bank_instructions=None, evidence=claims)
    for field, (value, raw, quote) in (header_facts or {}).items():
        reply[field] = value
        claims.append(dict(field=field, page=1, raw_value=raw, quote=quote))
    return ground_evidence(*parse_response(json.dumps(reply)), doc)


def verified_lines(result):
    return [ref for ref in result.evidence
            if ref.field.startswith("lines[") and ref.evidence_state == "NATIVE_VERIFIED"]


@pytest.fixture(scope="module")
def service_doc():
    return inspect_pdf(service_pdf())


def test_service_period_rows_with_same_item_code_are_verified_separately(service_doc):
    result = extract_lines(service_doc)
    refs = verified_lines(result)
    assert len(refs) == 10
    assert all(ref.quote.startswith("11-18 Oct 2026") for ref in refs if ref.field.startswith("lines[0]."))
    assert all(ref.quote.startswith("19-31 Oct 2026") for ref in refs if ref.field.startswith("lines[1]."))
    assert all(ref.evidence_state == "MISSING" for ref in result.evidence if not ref.field.startswith("lines["))


@pytest.mark.parametrize("mutation", ["omit", "duplicate", "swap_quantity"])
def test_banded_table_requires_complete_row_mapping(service_doc, mutation):
    assert not verified_lines(extract_lines(service_doc, mutation))


def test_banded_table_rejects_citation_from_other_row(service_doc):
    result = extract_lines(service_doc, "swap_quote")
    assert len(verified_lines(result)) == 9
    assert next(r for r in result.evidence if r.field == "lines[1].qty").evidence_state != "NATIVE_VERIFIED"


@pytest.mark.parametrize("variant", ["money_caption", "unlabeled", "unmapped"])
def test_unmapped_charge_content_refuses_line_proof(variant):
    doc = inspect_pdf(service_pdf(variant))
    assert band_charges(rows_for(doc.pages[0])) == ()
    assert not verified_lines(extract_lines(doc))


def test_printed_table_currency_is_not_discarded():
    doc = inspect_pdf(service_pdf("usd"))
    assert [charge.currency for charge in band_charges(rows_for(doc.pages[0]))] == ["USD", "USD"]
    assert not verified_lines(extract_lines(doc))


def test_exact_cell_prompt_is_scoped_to_supported_service_period_tables(service_doc):
    assert extraction_instruction(service_doc) == SERVICE_PERIOD_INSTRUCTION
    assert extraction_instruction(inspect_pdf(service_pdf("money_caption"))) == SYSTEM_INSTRUCTION
    standard = Path(__file__).resolve().parents[2] / "tests/fixtures/HAPPY_CLEAN.pdf"
    assert extraction_instruction(inspect_pdf(standard.read_bytes())) == SYSTEM_INSTRUCTION


def test_service_period_header_roles_are_verified(service_doc):
    result = extract_lines(service_doc, header_facts=HEADER_FACTS)
    headers = {ref.field: ref for ref in result.evidence if ref.field in HEADER_FACTS}
    assert {field: ref.evidence_state for field, ref in headers.items()} == dict.fromkeys(HEADER_FACTS, "NATIVE_VERIFIED")
    assert headers["invoice_date"].quote == "Issued 31 Oct 2026"
    assert headers["po_reference"].quote == "Customer PO PO-1042"
    assert headers["net"].quote == "Net service charges 50,000.00"


@pytest.mark.parametrize(("field", "claim"), [
    ("vendor_name_raw", ("Juniper Works India Pvt Ltd",) * 3),
    ("invoice_date", ("2026-11-30", "30 Nov 2026", "Due: 30 Nov 2026")),
    ("po_reference", ("PO-9999", "PO-9999", "Customer reference: PO-9999")),
    ("net", ("5000.00", "5,000.00", "Prior balance: 5,000.00")),
])
def test_nearby_values_do_not_prove_header_roles(service_doc, field, claim):
    result = extract_lines(service_doc, header_facts={**HEADER_FACTS, field: claim})
    assert next(ref for ref in result.evidence if ref.field == field).evidence_state != "NATIVE_VERIFIED"


@pytest.mark.parametrize(("variant", "field"), [
    ("no_issued", "invoice_date"),
    ("date_conflict", "invoice_date"),
    ("po_conflict", "po_reference"),
    ("net_conflict", "net"),
    ("vendor_conflict", "vendor_name_raw"),
    ("statement_context", "net"),
])
def test_missing_or_competing_role_fails_closed(variant, field):
    result = extract_lines(inspect_pdf(service_pdf(variant)), header_facts=HEADER_FACTS)
    assert next(ref for ref in result.evidence if ref.field == field).evidence_state != "NATIVE_VERIFIED"
