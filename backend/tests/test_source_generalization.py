"""Original development-only PDFs, strict wire claims, actual parser, real finance."""
import asyncio
from copy import deepcopy
import json
import re

import httpx
import pymupdf
import pytest

from app.contracts import PolicyV1
from app.documents.inspection import inspect_pdf
from app.documents.pipeline import extract_pdf
from app.domain import build_context, evaluate
from app.main import create_app
from source_layout_fixtures import source_layout
from test_currency_evidence import invoice_fixture
from test_document_engine import FakeProvider
from test_finance_engine import HISTORY, POS, VENDORS, codes
from test_orchestration_api import authority, upload
from test_review_api import body, complete
from test_source_layout import evidence, extract


def assess(pdf, reply):
    invoice = extract(pdf, reply)
    return evidence(invoice), evaluate(build_context(invoice, VENDORS, POS, HISTORY), PolicyV1())


def claim(reply, field):
    return next(ref for ref in reply["evidence"] if ref["field"] == field)


def formatted_claims(reply):
    for ref in reply["evidence"]:
        if ref["field"].startswith("lines["):
            parts = re.fullmatch(r"(\S+) (.+) (\d+) ([\d,.]+) ([\d,.]+)", ref["quote"]).groups()
            ref["quote"] = " | ".join(parts)
        else:
            label = ref["quote"].removesuffix(" " + ref["raw_value"])
            # Amount quotes include a source denomination outside the raw numeric claim.
            if label.endswith(" INR"):
                label = label.removesuffix(" INR")
                ref["quote"] = f"{label}: INR {ref['raw_value']}"
            else:
                ref["quote"] = f"{label}: {ref['raw_value']}"


@pytest.mark.parametrize("seller_below", [False, True])
def test_reformatted_quotes_ground_only_in_the_visual_cells(seller_below):
    pdf, reply = source_layout(column_order=True, statement=True, seller_below=seller_below)
    page, = inspect_pdf(pdf).pages
    assert page.route == "native_text" and page.line_rects
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        stream_order = document[0].get_text(sort=False)
    first = stream_order.index("OR-SUPPLY-01")
    assert stream_order.index("OR-SUPPLY-01", first + 1) < stream_order.index("Stationery kits")
    formatted_claims(reply)
    assert claim(reply, "lines[0].qty")["quote"] not in page.native_text
    states, decision = assess(pdf, reply)
    assert set(states.values()) == {"NATIVE_VERIFIED"}
    assert decision.outcome == "READY_FOR_AP"


@pytest.mark.parametrize("target, new_quote, expectation", [
    ("invoice_date", "PO No: PO-6001", "SOURCE_LOCATED_UNVERIFIED"),
    ("vendor_name_raw", "Supplier: Clearing Office", "MISSING"),
    ("total", "Combined account balance: INR 7,700.00", "MISSING"),
    ("lines[0].qty", "OR-SUPPLY-01 | Archive packs | 2 | 1,000.00 | 2,000.00", "SOURCE_LOCATED_UNVERIFIED"),
    ("lines[0].unit_price_net", "OR-SUPPLY-01 | Stationery kits | 3 | 3,000.00 | 1,000.00", "MISSING"),
    ("lines[0].item_code", "DEV-OTHER-01 | Stationery kits | 3 | 1,000.00 | 3,000.00", "MISSING"),
    ("lines[0].qty", "Included 3 units per purchase brochure", "MISSING"),
])
def test_formatted_claims_cannot_borrow_neighboring_semantics(target, new_quote, expectation):
    pdf, reply = source_layout(statement=True, seller_below=True, column_order=True)
    formatted_claims(reply)
    claim(reply, target)["quote"] = new_quote
    states, decision = assess(pdf, reply)
    assert states[target] == expectation
    assert decision.outcome == "REVIEW_REQUIRED"


def test_missing_provider_claim_is_never_created_from_visible_geometry():
    pdf, reply = source_layout(column_order=True)
    reply["evidence"].remove(claim(reply, "total"))
    states, decision = assess(pdf, reply)
    assert states["total"] == "MISSING" and decision.outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("field,title,option", [
    ("net", "Subtotal", {"prefixes": {"net": "USD "}}),
    ("total", "Grand Total", {"revision": True}),
])
def test_formatted_amount_claims_preserve_denomination_and_conflict_guards(field, title, option):
    pdf, reply = invoice_fixture("geometry", **option)
    ref = claim(reply, field)
    ref["quote"] = f"{title}: {ref['raw_value']}"
    states, decision = assess(pdf, reply)
    assert states[field] == "SOURCE_LOCATED_UNVERIFIED"
    assert states["currency"] == "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED" and "SOURCE_EVIDENCE_MISSING" in codes(decision)


def retain_first_row(reply):
    reply["lines"].pop()
    reply["evidence"] = [ref for ref in reply["evidence"] if not ref["field"].startswith("lines[1]")]


@pytest.mark.parametrize("shape", ["row_gap", "after_footer", "overlapping"])
def test_visible_omitted_charge_holds_review_even_when_extracted_arithmetic_reconciles(shape):
    pdf, reply = source_layout(included_service=True, legacy_echo=shape == "overlapping", **{shape: True})
    retain_first_row(reply)
    if shape == "overlapping":
        for field, quote in (("qty", "Quantity: 3"), ("unit_price_net", "Unit price: 1,000.00"),
                             ("item_code", "Item code: OR-SUPPLY-01"), ("net", "Line net: 3,000.00")):
            claim(reply, f"lines[0].{field}")["quote"] = quote
    states, decision = assess(pdf, reply)
    assert states["net"] == "NATIVE_VERIFIED"
    assert states["lines[0].qty"] == "SOURCE_LOCATED_UNVERIFIED"
    assert "SOURCE_EVIDENCE_MISSING" in codes(decision)
    assert "LINE_TOTAL_RECONCILIATION_FAILED" not in codes(decision)
    assert decision.outcome == "REVIEW_REQUIRED"


def test_complete_unusually_spaced_table_can_still_verify():
    pdf, reply = source_layout(row_gap=True)
    states, decision = assess(pdf, reply)
    assert states["lines[1].qty"] == "NATIVE_VERIFIED"
    assert decision.outcome == "READY_FOR_AP"


def test_verified_extra_charge_keeps_procurement_review():
    pdf, reply = source_layout(extra_item=True, column_order=True)
    formatted_claims(reply)
    states, decision = assess(pdf, reply)
    assert states["lines[1].item_code"] == "NATIVE_VERIFIED"
    assert (decision.outcome, decision.primary_reason_code, decision.owner) == (
        "REVIEW_REQUIRED", "LINE_MAPPING_UNRESOLVED", "Procurement")


@pytest.mark.parametrize("shape", ["duplicate", "merged"])
def test_table_requires_distinct_rows_even_when_extracted_totals_still_reconcile(shape):
    pdf, reply = source_layout(included_service=True, column_order=True)
    if shape == "merged":
        retain_first_row(reply)
        reply["lines"][0].update(qty="5", unit_price_net="600")
    else:
        reply["lines"][1] = deepcopy(reply["lines"][0])
        reply["lines"][1].update(qty="2", unit_price_net="0.00", net="0.00")
        for field in ("description", "item_code"):
            claim(reply, f"lines[1].{field}").update(
                {key: claim(reply, f"lines[0].{field}")[key] for key in ("raw_value", "quote")})
    states, decision = assess(pdf, reply)
    assert states["lines[0].qty"] == "SOURCE_LOCATED_UNVERIFIED"
    assert "LINE_TOTAL_RECONCILIATION_FAILED" not in codes(decision)
    assert decision.outcome == "REVIEW_REQUIRED"


def test_omitted_row_review_reloads_without_changing_recorded_runs_or_authority(tmp_path):
    async def scenario():
        pdf, reply = source_layout(included_service=True, row_gap=True)
        retain_first_row(reply)
        fake = FakeProvider([json.dumps(reply)])

        async def controlled(raw):
            return await extract_pdf(raw, fake, max_attempts=1)

        db, docs = tmp_path / "runs.db", tmp_path / "documents"
        app = create_app(db, document_dir=docs, extractor=controlled)
        async with app.router.lifespan_context(app):
            before = authority(app.state.engine)
            old = "/api/runs/" + complete(app)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                recorded = (await client.get(old)).json()
                assert (await client.post(old + "/po-confirmations", json=body())).status_code == 201
                review = (await client.get(old + "/review-history")).json()
                response = await upload(client, data=pdf)
                assert response.status_code == 202
                await app.state.runs.idle()
                url = "/api/runs/" + response.json()["run_id"]
                snapshot = (await client.get(url)).json()
                assert snapshot["decision"]["outcome"] == "REVIEW_REQUIRED"
                assert snapshot["decision"]["primary_reason_code"] == "SOURCE_EVIDENCE_MISSING"
                preview = await client.post(url + "/policy-preview", json={"price_tolerance_pct": "0.05"})
                assert preview.status_code == 200 and preview.json()["preview_decision"]["outcome"] == "REVIEW_REQUIRED"
                assert authority(app.state.engine) == before

        reopened = create_app(db, document_dir=docs, extractor=controlled)
        async with reopened.router.lifespan_context(reopened):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=reopened), base_url="http://test") as client:
                assert (await client.get(url)).json() == snapshot
                assert (await client.get(url + "/document")).content == pdf
                assert (await client.get(old)).json() == recorded
                assert (await client.get(old + "/review-history")).json() == review
            assert authority(reopened.state.engine) == before
        assert len(fake.calls) == 1

    asyncio.run(scenario())
