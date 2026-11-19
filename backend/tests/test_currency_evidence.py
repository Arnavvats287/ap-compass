"""Development-only invoice evidence controls, using the bounded parser and wire schema."""
import asyncio
from decimal import Decimal
from html import escape
import json

import httpx
import pymupdf
import pytest

from app.contracts import PolicyV1
from app.documents.pipeline import extract_pdf
from app.domain import build_context, evaluate
from app.main import create_app
from test_document_engine import FakeProvider
from test_finance_engine import HISTORY, POS, VENDORS, codes
from test_orchestration_api import authority, upload
from test_review_api import body, complete
from test_source_layout import evidence, extract


HEADERS = (
    ("vendor_name_raw", "Supplier", "Orion Office Products"),
    ("invoice_number", "Invoice No", "DEV-CURRENCY-057"),
    ("invoice_date", "Invoice date", "2026-10-09"),
    ("po_reference", "PO No", "PO-6001"),
    ("currency", "Currency", "INR"),
)
MONEY = {"net": "1000.00", "tax": "180.00", "total": "1180.00",
         "lines[0].unit_price_net": "1000.00", "lines[0].net": "1000.00"}
LINE_FIELDS = ("item_code", "description", "qty", "unit_price_net", "net")


def invoice_fixture(layout="legacy", *, prefixes=None, currency="INR", extra_line=False, revision=False):
    """Draw ordinary visible label blocks or a small table without writing fixture files."""
    prefixes = prefixes or {}
    headers = tuple((field, title, currency if field == "currency" else value) for field, title, value in HEADERS)
    reply = {field: value for field, _, value in headers}
    reply.update(net="2000.00" if extra_line else MONEY["net"], tax="360.00" if extra_line else MONEY["tax"],
                 total="2360.00" if extra_line else MONEY["total"], bank_instructions=None, evidence=[])
    line = dict(item_code="OR-SUPPLY-01", description="Archive sleeves", qty="1",
                unit_price_net=MONEY["lines[0].unit_price_net"], net=MONEY["lines[0].net"])
    reply["lines"] = [line]
    with pymupdf.open() as document:
        page = document.new_page()

        def text(x, y, value):
            # MuPDF's built-in HTML font fallback supplies the visible rupee glyph cross-platform.
            page.insert_htmlbox((x, y, 595, y + 22), escape(value), css="* {font-family: sans-serif; font-size: 10pt;}")

        def claim(field, printed, quote):
            reply["evidence"].append(dict(field=field, page=1, raw_value=printed, quote=quote))

        def label(field, title, value, y):
            if layout == "legacy":
                quote = f"{title}: {value}"
                text(40, y, quote)
            else:
                quote = f"{title} {value}"
                text(40, y, title)
                text(185, y, value)
            claim(field, value, quote)

        def amount(field, numeric):
            return prefixes.get(field, "INR ") + f"{Decimal(numeric):,.2f}"

        for index, (field, title, value) in enumerate(headers):
            label(field, title, value, 42 + index * 25)
        text(40, 177, "Bill to: West Yard Workshop")
        text(40, 202, "Remit to: Sample Clearing Office")
        row = [line["item_code"], line["description"], prefixes.get("lines[0].qty", "") + line["qty"],
               amount("lines[0].unit_price_net", line["unit_price_net"]), amount("lines[0].net", line["net"])]
        if layout == "legacy":
            text(40, 247, row[1])
            claim("lines[0].description", row[1], row[1])
            for index, (key, title) in enumerate(zip((0, 2, 3, 4), ("Item code", "Quantity", "Unit price (net)", "Line net"))):
                label(f"lines[0].{LINE_FIELDS[key]}", title, row[key], 272 + index * 24)
            if extra_line:
                for i, value in enumerate(("Document handling", "Item code: DEV-HANDLING-27", "Quantity: 1",
                                           "Unit price (net): INR 1,000.00", "Line net: INR 1,000.00")):
                    text(40, 374 + 21 * i, value)
        else:
            xs = (40, 145, 305, 375, 495)
            for x, title, value in zip(xs, ("Item code", "Description", "Qty", "Unit net", "Line net"), row):
                text(x, 247, title)
                text(x, 272, value)
            for field, value in zip(LINE_FIELDS, row):
                claim(f"lines[0].{field}", value, " ".join(row))
            if extra_line:
                for x, value in zip(xs, ("DEV-HANDLING-27", "Document handling", "1", "INR 1,000.00", "INR 1,000.00")):
                    text(x, 297, value)
        for index, (field, title) in enumerate((("net", "Subtotal"), ("tax", "GST"), ("total", "Grand Total"))):
            label(field, title, amount(field, reply[field]), 500 + index * 26)
        if revision:
            text(40, 616, "Revised Grand Total: USD 1,180.00")
        document.subset_fonts()
        return document.tobytes(garbage=4, deflate=True), reply


def result(pdf, reply):
    invoice = extract(pdf, reply)
    decision = evaluate(build_context(invoice, VENDORS, POS, HISTORY), PolicyV1())
    return evidence(invoice), decision


@pytest.mark.parametrize("layout", ["legacy", "geometry"])
@pytest.mark.parametrize("prefix", ["INR ", "\N{INDIAN RUPEE SIGN}", ""])
def test_compatible_and_unprefixed_monetary_sources_verify(layout, prefix):
    states, decision = result(*invoice_fixture(layout, prefixes=dict.fromkeys(MONEY, prefix)))
    assert all(states[field] == "NATIVE_VERIFIED" for field in MONEY)
    assert states["currency"] == "NATIVE_VERIFIED" and states["lines[0].qty"] == "NATIVE_VERIFIED"
    assert decision.outcome == "READY_FOR_AP"


@pytest.mark.parametrize("layout", ["legacy", "geometry"])
@pytest.mark.parametrize("field", MONEY)
@pytest.mark.parametrize("prefix", ["USD ", "$"])
def test_foreign_printed_denomination_withholds_equivalent_amount(layout, field, prefix):
    states, decision = result(*invoice_fixture(layout, prefixes={field: prefix}))
    assert states[field] == "SOURCE_LOCATED_UNVERIFIED", (states[field], decision.outcome, codes(decision))
    assert states["currency"] == "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED" and "SOURCE_EVIDENCE_MISSING" in codes(decision)
    assert not {"CURRENCY_MISMATCH", "TOTAL_RECONCILIATION_FAILED"} & codes(decision)


@pytest.mark.parametrize("layout", ["legacy", "geometry"])
@pytest.mark.parametrize("source,claimed", [("USD ", ""), ("INR ", "USD "), ("", "INR "), ("CAD ", "")])
def test_raw_claim_cannot_rewrite_or_invent_source_denomination(layout, source, claimed):
    pdf, reply = invoice_fixture(layout, prefixes={"net": source})
    next(ref for ref in reply["evidence"] if ref["field"] == "net")["raw_value"] = claimed + "1,000.00"
    states, decision = result(pdf, reply)
    assert states["net"] != "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("layout", ["legacy", "geometry"])
def test_matching_magnitude_with_competing_denominations_withholds_total(layout):
    states, decision = result(*invoice_fixture(layout, revision=True))
    assert states["total"] == "SOURCE_LOCATED_UNVERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED" and "TOTAL_RECONCILIATION_FAILED" not in codes(decision)


@pytest.mark.parametrize("layout", ["legacy", "geometry"])
def test_quantity_is_not_a_currency_denomination(layout):
    states, decision = result(*invoice_fixture(layout, prefixes={"lines[0].qty": "INR "}))
    assert states["lines[0].qty"] != "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("layout", ["legacy", "geometry"])
def test_explicit_currency_requires_an_extracted_invoice_denomination(layout):
    pdf, reply = invoice_fixture(layout)
    reply["currency"] = None
    reply["evidence"] = [claim for claim in reply["evidence"] if claim["field"] != "currency"]
    states, decision = result(pdf, reply)
    assert all(states[field] == "SOURCE_LOCATED_UNVERIFIED" for field in MONEY)
    assert states["currency"] == "MISSING" and decision.outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("layout", ["legacy", "geometry"])
def test_coherent_foreign_source_keeps_existing_authoritative_currency_block(layout):
    states, decision = result(*invoice_fixture(layout, prefixes=dict.fromkeys(MONEY, "USD "), currency="USD"))
    assert all(states[field] == "NATIVE_VERIFIED" for field in MONEY)
    assert decision.outcome == "BLOCKED" and "CURRENCY_MISMATCH" in codes(decision)


@pytest.mark.parametrize("layout", ["legacy", "geometry"])
def test_omitted_printed_line_is_detected_in_this_fixture(layout):
    states, decision = result(*invoice_fixture(layout, extra_line=True))
    assert "LINE_TOTAL_RECONCILIATION_FAILED" in codes(decision)
    assert (states["lines[0].item_code"] == "NATIVE_VERIFIED") == (layout == "legacy")
    assert decision.outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("issuer,quote", [("West Yard Workshop", "Bill to: West Yard Workshop"),
                                          ("Sample Clearing Office", "Remit to: Sample Clearing Office")])
def test_buyer_and_remittance_roles_cannot_verify_supplier(issuer, quote):
    pdf, reply = invoice_fixture()
    reply["vendor_name_raw"] = issuer
    next(ref for ref in reply["evidence"] if ref["field"] == "vendor_name_raw").update(raw_value=issuer, quote=quote)
    states, decision = result(pdf, reply)
    assert states["vendor_name_raw"] == "SOURCE_LOCATED_UNVERIFIED"
    assert decision.outcome != "READY_FOR_AP"


@pytest.mark.parametrize("layout", ["legacy", "geometry"])
def test_identical_subtotal_cannot_ground_unit_price(layout):
    pdf, reply = invoice_fixture(layout)
    subtotal = next(ref for ref in reply["evidence"] if ref["field"] == "net")
    next(ref for ref in reply["evidence"] if ref["field"] == "lines[0].unit_price_net")["quote"] = subtotal["quote"]
    states, decision = result(pdf, reply)
    assert states["net"] == "NATIVE_VERIFIED"
    assert states["lines[0].unit_price_net"] != "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


def test_currency_review_persists_without_changing_historical_run_or_action(tmp_path):
    async def scenario():
        pdf, reply = invoice_fixture(prefixes={"net": "USD "})
        provider = FakeProvider([json.dumps(reply)])

        async def controlled(raw):
            return await extract_pdf(raw, provider, max_attempts=1)

        database = tmp_path / "evidence.sqlite"
        documents = tmp_path / "documents"
        app = create_app(database, document_dir=documents, extractor=controlled)
        async with app.router.lifespan_context(app):
            before = authority(app.state.engine)
            history_url = "/api/runs/" + complete(app)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                historical = (await client.get(history_url)).json()
                action = await client.post(history_url + "/po-confirmations", json=body())
                assert action.status_code == 201
                history = (await client.get(history_url + "/review-history")).json()
                submission = await upload(client, data=pdf)
                assert submission.status_code == 202
                await app.state.runs.idle()
                url = "/api/runs/" + submission.json()["run_id"]
                snapshot = (await client.get(url)).json()
                assert snapshot["decision"]["outcome"] == "REVIEW_REQUIRED"
                assert snapshot["decision"]["primary_reason_code"] == "SOURCE_EVIDENCE_MISSING"
                net = next(ref for ref in snapshot["extracted_invoice"]["evidence"] if ref["field"] == "net")
                assert net["raw_value"] == "USD 1,000.00" and net["evidence_state"] == "SOURCE_LOCATED_UNVERIFIED"
                assert authority(app.state.engine) == before
                assert (await client.get(history_url)).json() == historical

        reload_calls = []

        async def unexpected(raw):
            reload_calls.append(raw)
            raise AssertionError("Reload must not call extraction")

        reopened = create_app(database, document_dir=documents, extractor=unexpected)
        async with reopened.router.lifespan_context(reopened):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=reopened), base_url="http://test") as client:
                assert (await client.get(url)).json() == snapshot
                assert (await client.get(url + "/document")).content == pdf
                assert (await client.get(history_url)).json() == historical
                assert (await client.get(history_url + "/review-history")).json() == history
            assert authority(reopened.state.engine) == before
        assert len(provider.calls) == 1 and not reload_calls

    asyncio.run(scenario())
