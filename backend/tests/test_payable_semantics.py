"""Synthetic payable layouts served through the actual parser, wire schema and evaluator."""
from io import BytesIO

import pytest
from reportlab.pdfgen.canvas import Canvas

from test_finance_engine import codes
from test_source_generalization import assess


LABELS = ("Current invoice amount due", "Invoice amount due", "Gross payable", "Total amount payable", "Amount payable")
AMOUNT = "INR 4,720.00"


def invoice_pdf(label="Gross payable", *, split=False, amount=AMOUNT, appendix=(), selected=None,
                account_heading=None, unrelated_column=False, wide_tax=None):
    output = BytesIO()
    pdf = Canvas(output, pagesize=(620, 790), invariant=1)
    pdf.setFont("Helvetica", 10)
    headers = (
        ("vendor_name_raw", "Supplier", "Orion Office Products"),
        ("invoice_number", "Invoice no.", "DEV-PAYABLE-44"),
        ("invoice_date", "Invoice date", "2026-10-11"),
        ("po_reference", "Purchase order", "PO-6001"),
        ("currency", "Currency", "INR"),
    )
    refs = []

    def printed(field, raw, line, page=1):
        refs.append(dict(field=field, page=page, raw_value=raw, quote=line))

    for i, (field, name, value) in enumerate(headers):
        text = f"{name}: {value}"
        pdf.drawString(112, 714 - 18 * i, text)
        printed(field, value, text)
    for i, (leaf, value, text) in enumerate((
        ("description", "Binders and labels", "Binders and labels"),
        ("item_code", "OR-SUPPLY-01", "Item code: OR-SUPPLY-01"),
        ("qty", "4", "Quantity: 4"),
        ("unit_price_net", "INR 1,000.00", "Unit price (net): INR 1,000.00"),
        ("net", "INR 4,000.00", "Line net: INR 4,000.00"),
    )):
        pdf.drawString(112, 560 - 20 * i, text)
        printed(f"lines[0].{leaf}", value, text)
    for field, text, value, y in (("net", "Net subtotal", "INR 4,000.00", 405),
                                  ("tax", "GST (18%)", "INR 720.00", 384)):
        if wide_tax:
            value = value.removeprefix("INR ") if field == "tax" else value
            if field != "tax" or wide_tax != "unlabelled":
                pdf.drawString(211, y, text)
            edge = 511 if field == "tax" and wide_tax == "misaligned" else 490
            pdf.drawRightString(edge, y, value)
            printed(field, value, f"{text} {value}")
        else:
            pdf.drawString(211, y, f"{text}: {value}")
            printed(field, value, f"{text}: {value}")
    if account_heading:
        pdf.drawString(211, 363, account_heading)
    y = 363 if wide_tax else 333
    if unrelated_column:
        pdf.drawString(397, y + 18, "Payment account total")
    if split:
        pdf.drawString(211, y, label)
        if wide_tax:
            pdf.drawRightString(490, y, amount)
        else:
            pdf.drawString(397, y, amount)
        quote = f"{label} {amount}"
    else:
        quote = f"{label}: {amount}"
        pdf.drawString(211, y, quote)
    for page, x, row_y, text, raw in appendix:
        if page == 2 and pdf.getPageNumber() == 1:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            pdf.drawString(112, 750, "Attachments to synthetic invoice DEV-PAYABLE-44")
        pdf.drawString(x, row_y, text)
        if raw:
            pdf.drawString(x+186, row_y, raw)
    pdf.save()
    if selected:
        claim_page, quote, amount = selected
    else:
        claim_page = 1
    printed("total", amount, quote, claim_page)
    return output.getvalue(), dict(
        **{field:value for field,_,value in headers},
        net="4000", tax="720", total="4720", bank_instructions=None, evidence=refs,
        lines=[dict(description="Binders and labels", item_code="OR-SUPPLY-01", qty="4",
                    unit_price_net="1000", net="4000")],
    )


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("split", [False, True], ids=["inline", "separate-cells"])
def test_current_payable_labels_can_verify(label, split):
    states, decision = assess(*invoice_pdf(label, split=split, appendix=(
        (1, 112, 230, "Account summary", None),
        (1, 112, 208, "Previous balance: INR 800.00", None),
        (1, 112, 186, "Combined account balance: INR 5,520.00", None),
    )))
    assert set(states.values()) == {"NATIVE_VERIFIED"}
    assert decision.outcome == "READY_FOR_AP"


@pytest.mark.parametrize("label", [
    "Previous balance", "Amount due on earlier invoices", "Combined statement balance",
    "Payment account total", "Settlement balance", "Unapplied credit", "Shipping amount due",
])
def test_unrelated_money_labels_cannot_verify_even_when_values_reconcile(label):
    states, decision = assess(*invoice_pdf(label, split=True))
    assert states["total"] == "SOURCE_LOCATED_UNVERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"
    assert "TOTAL_RECONCILIATION_FAILED" not in codes(decision)


def test_legacy_payable_does_not_borrow_an_embedded_line_from_another_quote():
    wrong_quote = f"Payment-account note / Invoice amount due: {AMOUNT}"
    states, decision = assess(*invoice_pdf("Invoice amount due", selected=(1, wrong_quote, AMOUNT),
                                          appendix=((1, 112, 230, wrong_quote, None),)))
    assert states["total"] == "SOURCE_LOCATED_UNVERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


def test_split_payable_cannot_borrow_amount_beneath_another_column_heading():
    states, decision = assess(*invoice_pdf("Current invoice amount due", split=True, unrelated_column=True))
    assert states["total"] == "SOURCE_LOCATED_UNVERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("page", [1, 2])
def test_gross_claim_cannot_use_another_printed_role_or_page(page):
    wrong_quote = f"Payment account total: {AMOUNT}"
    states, decision = assess(*invoice_pdf("Gross payable", split=True, selected=(page, wrong_quote, AMOUNT),
                                          appendix=((page, 112, 240, wrong_quote, None),)))
    assert states["total"] == "SOURCE_LOCATED_UNVERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("heading", ["Account summary", "Payment account summary", "Payment history", "Statement totals"])
@pytest.mark.parametrize("split", [False, True])
def test_generic_payable_inside_account_summary_cannot_verify(heading, split):
    states, decision = assess(*invoice_pdf("Total amount payable", split=split, account_heading=heading))
    assert states["total"] == "SOURCE_LOCATED_UNVERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


def test_revision_word_does_not_make_an_account_payable_an_invoice_source():
    states, decision = assess(*invoice_pdf("Revised gross payable", split=True, account_heading="Payment history"))
    assert states["total"] == "SOURCE_LOCATED_UNVERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("split", [False, True])
def test_new_payable_alias_requires_matching_denomination(split):
    states, decision = assess(*invoice_pdf("Gross payable", split=split, amount="USD 4,720.00"))
    assert states["total"] == "SOURCE_LOCATED_UNVERIFIED" and states["currency"] == "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


def test_new_payable_alias_requires_exact_decimal_value():
    states, decision = assess(*invoice_pdf("Gross payable", split=True, amount="INR 4,720.01"))
    assert states["total"] == "SOURCE_LOCATED_UNVERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


def test_payable_support_retains_printed_spacing_and_recognized_currency_format():
    states, decision = assess(*invoice_pdf("Invoice   amount   due", split=True, amount="Rs.  4,720.00"))
    assert states["total"] == "NATIVE_VERIFIED"
    assert decision.outcome == "READY_FOR_AP"


@pytest.mark.parametrize("split", [False, True])
def test_generic_payable_outside_invoice_amount_group_is_unverified(split):
    states, decision = assess(*invoice_pdf("Amount payable", split=split, account_heading="Settlement activity"))
    assert states["total"] == "SOURCE_LOCATED_UNVERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


def test_payable_quote_does_not_locate_on_a_page_without_the_printed_claim():
    states, decision = assess(*invoice_pdf("Gross payable", split=True, selected=(2, f"Gross payable {AMOUNT}", AMOUNT),
                                          appendix=((2, 112, 610, "Signed delivery note for October binders.", None),)))
    assert states["total"] == "MISSING"
    assert decision.outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("appendix", [
    ((1,112,240,"Gross payable: INR 5,720.00",None),),
    ((2,112,610,"Invoice amount due","INR 5,720.00"),),
    ((2,112,642,"Account summary",None),(2,112,610,"Current invoice amount due","INR 5,720.00")),
    ((2,112,610,"Total amount payable","USD 4,720.00"),),
], ids=["inline-same-page","split-other-page","split-account-summary","conflicting-denomination"])
def test_reconciling_selected_total_is_withheld_when_printed_payables_conflict(appendix):
    states, decision = assess(*invoice_pdf("Grand Total", split=True, appendix=appendix))
    assert states["total"] == "SOURCE_LOCATED_UNVERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"
    assert "TOTAL_RECONCILIATION_FAILED" not in codes(decision)
    assert "SOURCE_EVIDENCE_MISSING" in codes(decision)


def test_same_explicit_current_invoice_payable_repeated_in_account_summary_is_not_conflict():
    states, decision = assess(*invoice_pdf("Gross payable", split=True, appendix=(
        (2,112,642,"Account summary",None),(2,112,610,"Current invoice amount due",AMOUNT),
    )))
    assert states["total"] == "NATIVE_VERIFIED"
    assert decision.outcome == "READY_FOR_AP"


@pytest.mark.parametrize("layout,expected", [
    ("aligned", "NATIVE_VERIFIED"),
    ("misaligned", "SOURCE_LOCATED_UNVERIFIED"),
    ("unlabelled", "MISSING"),
])
def test_wide_tax_cell_needs_printed_label_and_aligned_invoice_amount_rows(layout, expected):
    states, decision = assess(*invoice_pdf("Grand total", split=True, wide_tax=layout))
    assert states["tax"] == expected
    assert decision.outcome == ("READY_FOR_AP" if expected == "NATIVE_VERIFIED" else "REVIEW_REQUIRED")
