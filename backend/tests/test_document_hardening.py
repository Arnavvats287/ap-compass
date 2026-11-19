from dataclasses import replace
from io import BytesIO
import json

import pymupdf
import pytest
from PIL import Image, ImageDraw

from app.contracts import PolicyV1
from app.documents.evidence import ground_evidence
from app.documents.fixtures import native_case
from app.domain import build_context, evaluate
from app.documents.inspection import inspect_pdf
from app.documents.schema import parse_response
from app.documents.types import ExtractionError
from test_document_engine import CASES, FakeProvider, ROOT, run, wire
from test_finance_engine import HISTORY, POS, VENDORS
from test_document_positive_controls import control


def test_document_consistency_withholds_disputed_headers():
    # Exercise the evidence boundary using already inspected, ordinary labelled observations.
    original = inspect_pdf(control("visible"))
    page = original.pages[0]
    continuation = (
        "Invoice number: Different synthetic invoice",
        "Revised net subtotal: INR 51000",
        "Final tax: INR 9180",
        "Revised final total: INR 60180",
    )
    inspection = replace(original, pages=(page, replace(
        page, number=2, native_text="\n".join(continuation),
        lines=tuple((line, 11) for line in continuation),
    )))
    invoice, claims = parse_response(json.dumps(wire()))
    result = ground_evidence(invoice, claims, inspection)
    refs = {ref.field: ref for ref in result.evidence}
    for field in ("invoice_number", "net", "tax", "total"):
        assert refs[field].evidence_state == "SOURCE_LOCATED_UNVERIFIED"
        assert refs[field].page == 1 and refs[field].quote
        assert getattr(result, field) == getattr(invoice, field)
    assert refs["currency"].evidence_state == "NATIVE_VERIFIED"
    decision = evaluate(build_context(result, VENDORS, POS, HISTORY), PolicyV1())
    assert decision.outcome == "REVIEW_REQUIRED"
    assert any(f.code == "SOURCE_EVIDENCE_MISSING" and f.next_action for f in decision.findings)


def test_repeated_summary_and_non_invoice_balances_preserve_verification():
    inspection = inspect_pdf(control("repeated_summary"))
    page = inspection.pages[-1]
    lines = ("Final net subtotal: INR 48000.00", "Final tax: INR 8640.0",
             "Final total: INR 56640.00", "Previous balance: INR 173",
             "Customer account balance: INR 40", "Line subtotal: INR 265")
    inspection = replace(inspection, pages=(inspection.pages[0], replace(
        page, native_text="\n".join(lines), lines=tuple((line, 11) for line in lines))))
    invoice, claims = parse_response(json.dumps(wire()))
    grounded = ground_evidence(invoice, claims, inspection)
    assert all(ref.evidence_state == "NATIVE_VERIFIED" for ref in grounded.evidence)


def payment_notice_pdf():
    # Ordinary synthetic invoice with a legible payment-related notice and no bank credentials.
    image = Image.new("RGB", (220, 45), "white")
    ImageDraw.Draw(image).text((8, 12), "Payment terms: net 30 days", fill="black")
    encoded = BytesIO()
    image.save(encoded, format="PNG")
    with pymupdf.open(stream=control("visible"), filetype="pdf") as pdf:
        pdf[0].insert_image(pymupdf.Rect(48, 240, 268, 285), stream=encoded.getvalue())
        return pdf.tobytes(no_new_id=True)


def test_small_raster_notice_is_routed_with_image():
    page, = inspect_pdf(payment_notice_pdf()).pages
    assert page.route == "mixed"
    assert page.image_png and page.native_text


def test_render_guard_rejects_blank_native_render():
    # The guard receives a uniform render and readable parser text as separate signals.
    from app.documents._parse_process import require_visible_native
    with pymupdf.open() as blank:
        page = blank.new_page()
        with pytest.raises(ExtractionError, match="EMPTY_PDF"):
            require_visible_native(page.get_pixmap())
    with pymupdf.open(stream=control("visible"), filetype="pdf") as visible:
        require_visible_native(visible[0].get_pixmap())


def test_extractable_prose_on_uniform_page_fails_in_parser_subprocess():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 80), "Synthetic readability sample containing no invoice or payment data.",
                         color=(1, 1, 1))
        assert len(page.get_text().strip()) >= 40 and page.get_pixmap().is_unicolor
        with pytest.raises(ExtractionError, match="EMPTY_PDF"):
            inspect_pdf(pdf.tobytes())


def test_actual_blank_and_visible_documents():
    with pymupdf.open() as pdf:
        pdf.new_page()
        with pytest.raises(ExtractionError, match="EMPTY_PDF"):
            inspect_pdf(pdf.tobytes())
    assert inspect_pdf(control("visible")).route == "native_text"

def test_unresolved_mixed_raster_retains_extraction_and_flags():
    provider = FakeProvider([json.dumps(wire())])
    result = run(payment_notice_pdf(), provider, max_attempts=2)
    assert result.invoice.document_integrity_flags == ("RASTER_CONTENT_UNRESOLVED",)
    assert result.invoice.bank_instructions is None
    assert len(provider.calls) == result.metadata.model_calls == 1
    assert provider.calls[0].pages[0].image_png


def test_mixed_document_with_bank_claims_withholds_bank_verification():
    with pymupdf.open(stream=native_case(CASES["BANK_CHANGED"]), filetype="pdf") as native:
        with pymupdf.open(ROOT / "tests/fixtures/SCAN_CONFLICT.pdf") as scan:
            native.insert_pdf(scan)
        inspection = inspect_pdf(native.tobytes())
    assert inspection.route == "mixed"
    invoice, claims = parse_response(json.dumps(wire("BANK_CHANGED", line_net=False)))
    image_claims = tuple(
        claim.model_copy(update={"page": 2})
        if claim.field.startswith("bank_instructions.") else claim
        for claim in claims
    )
    grounded = ground_evidence(invoice, image_claims, inspection)
    refs = {ref.field: ref.evidence_state for ref in grounded.evidence}
    assert refs["net"] == "NATIVE_VERIFIED"
    assert refs["bank_instructions.account"] == refs["bank_instructions.ifsc"] == "SOURCE_LOCATED_UNVERIFIED"
    decision = evaluate(build_context(grounded, VENDORS, POS, HISTORY), PolicyV1())
    assert decision.outcome == "REVIEW_REQUIRED"
    assert any(f.code == "BANK_DETAILS_UNVERIFIED" for f in decision.findings)
    assert all(f.code != "BANK_DETAILS_MISMATCH" for f in decision.findings)

    native_bank = ground_evidence(invoice, claims, inspection)
    blocked = evaluate(build_context(native_bank, VENDORS, POS, HISTORY), PolicyV1())
    assert blocked.outcome == "BLOCKED"
    assert {"BANK_DETAILS_MISMATCH", "DOCUMENT_CONTENT_UNVERIFIED"} <= {f.code for f in blocked.findings}

    wrong_claims = tuple(
        claim.model_copy(update={"quote": "This sentence is absent from the native page."})
        if claim.field.startswith("bank_instructions.") else claim
        for claim in claims
    )
    unsupported = ground_evidence(invoice, wrong_claims, inspection)
    assert all(ref.evidence_state == "MISSING" for ref in unsupported.evidence
               if ref.field.startswith("bank_instructions."))
