"""Ordinary synthetic mixed documents through the actual offline extraction and API."""
import asyncio
import json

import httpx
import pymupdf
import pytest

from app.documents.pipeline import extract_pdf
from app.documents.schema import parse_response, provider_schema
from app.documents.types import ExtractionError
from app.main import create_app
from review_fixtures import wire as review_wire
from test_document_engine import ROOT, FakeProvider, wire
from test_document_hardening import payment_notice_pdf
from test_orchestration_api import authority, upload
from test_review_api import body
from test_policy_preview import rows


def with_logo(raw):
    """A two-color fictional geometric mark with no financial content."""
    pixels = bytes([34, 86, 70] * 72 + [210, 180, 90] * 72)
    logo = pymupdf.Pixmap(pymupdf.csRGB, 12, 12, pixels, False)
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        pdf[0].insert_image(pymupdf.Rect(510, 100, 534, 124), pixmap=logo)
        return pdf.tobytes(no_new_id=True)


@pytest.mark.parametrize("flag", [[], None, ["RASTER_CONTENT_UNRESOLVED"]])
def test_provider_cannot_set_or_clear_integrity(flag):
    assert "document_integrity_flags" not in provider_schema()["properties"]
    with pytest.raises(ExtractionError, match="INVALID_RESPONSE"):
        parse_response(json.dumps({**wire(), "document_integrity_flags": flag}))


@pytest.mark.parametrize("case,variant,expected,hard_code", [
    ("HAPPY_CLEAN", "logo", "REVIEW_REQUIRED", None),
    ("HAPPY_CLEAN", "payment", "REVIEW_REQUIRED", None),
    ("OVERBILLED_PARTIAL", "logo", "BLOCKED", "PO_BALANCE_EXCEEDED"),
    ("DUPLICATE_REISSUED", "logo", "BLOCKED", "EXACT_DUPLICATE"),
    ("MISSING_PO_VALID", "logo", "REVIEW_REQUIRED", None),
    ("HAPPY_CLEAN", "invalid", None, None),
    ("HAPPY_CLEAN", "malformed_reply", None, None),
    ("HAPPY_CLEAN", "unusable_reply", None, None),
])
def test_mixed_run_persists_and_reassesses(tmp_path, case, variant, expected, hard_code):
    async def scenario():
        path = ROOT / "tests/fixtures" / (case + ".pdf")
        if case == "MISSING_PO_VALID":
            path = path.parent / "human_resolution" / path.name
        reply = review_wire(case) if case == "MISSING_PO_VALID" else wire(case)
        raw = payment_notice_pdf() if variant == "payment" else with_logo(path.read_bytes())
        text = json.dumps(reply)
        error = None
        if variant == "invalid":
            raw = b"%PDF-1.7\ninvalid content\n%%EOF"
            error = "INVALID_PDF"
        elif variant == "malformed_reply":
            text = "{"
            error = "INVALID_RESPONSE"
        elif variant == "unusable_reply":
            text = json.dumps({key: [] if key in ("lines", "evidence") else None for key in reply})
            error = "INVALID_RESPONSE"
        provider = FakeProvider([text], model="TEST_ONLY-mixed-review")

        async def extract(raw):
            return await extract_pdf(raw, provider, max_attempts=1)

        database, docs = tmp_path / "runs.db", tmp_path / "documents"
        app = create_app(database, document_dir=docs, extractor=extract)
        async with app.router.lifespan_context(app):
            before = authority(app.state.engine)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                policy = (await client.get("/api/policy")).json()
                response = await upload(client, data=raw)
                assert response.status_code == 202
                await app.state.runs.idle()
                run_path = "/api/runs/" + response.json()["run_id"]
                recorded = (await client.get(run_path)).json()
                if error:
                    assert recorded["execution_state"] == "PROCESSING_FAILED"
                    assert recorded["execution_error_code"] == error and recorded["decision"] is None
                    assert len(provider.calls) == (0 if variant == "invalid" else 1)
                    assert authority(app.state.engine) == before
                    return
                assert recorded["execution_state"] == "COMPLETED"
                assert recorded["source_route"] == "mixed"
                assert recorded["usage"]["model_calls"] == 1
                invoice = recorded["extracted_invoice"]
                assert invoice["document_integrity_flags"] == ["RASTER_CONTENT_UNRESOLVED"]
                assert invoice["bank_instructions"] is None and invoice["net"] == reply["net"]
                assert all(ref["evidence_state"] != "NATIVE_VERIFIED" for ref in invoice["evidence"])
                decision = recorded["decision"]
                assert decision["outcome"] == expected
                findings = {f["code"]: f for f in decision["findings"]}
                content = findings["DOCUMENT_CONTENT_UNVERIFIED"]
                assert content["severity"] == "REVIEW" and content["owner"] == "Accounts Payable"
                assert content["next_action"]
                assert findings["BANK_DETAILS_NOT_PROVIDED"]["title"] == "No payment instructions extracted"
                if hard_code:
                    assert findings[hard_code]["severity"] == "BLOCK"
                elif case == "HAPPY_CLEAN":
                    assert decision["primary_reason_code"] == content["code"]

        async def no_extraction(_raw):
            pytest.fail("Stored assessment unexpectedly called the extractor")

        restarted = create_app(database, document_dir=docs, extractor=no_extraction)
        async with restarted.router.lifespan_context(restarted):
            initial_rows = rows(restarted.state.engine)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=restarted), base_url="http://test") as client:
                assert (await client.get(run_path)).json() == recorded
                assert (await client.get(run_path + "/document")).content == raw
                for tolerance in ("0.02", "0.05"):
                    preview = await client.post(run_path + "/policy-preview", json={"price_tolerance_pct": tolerance})
                    assert preview.status_code == 200
                    decision = preview.json()["preview_decision"]
                    assert decision["outcome"] == expected
                    assert "DOCUMENT_CONTENT_UNVERIFIED" in {f["code"] for f in decision["findings"]}
                if case == "MISSING_PO_VALID":
                    action = await client.post(run_path + "/po-confirmations", json=body())
                    assert action.status_code == 201, action.text
                    reassessment = action.json()["reassessment"]
                    assert reassessment["outcome"] == "REVIEW_REQUIRED"
                    assert reassessment["primary_reason_code"] == "DOCUMENT_CONTENT_UNVERIFIED"
                    assert (await client.get(run_path + "/review-history")).json()["actions"] == [action.json()]
                assert (await client.get(run_path)).json() == recorded
                assert (await client.get("/api/policy")).json() == policy
            assert rows(restarted.state.engine) == initial_rows
            assert authority(restarted.state.engine) == before
        assert len(provider.calls) == 1

    asyncio.run(scenario())

def test_integrity_rule_holds_when_all_invoice_facts_are_verified():
    from app.contracts import PolicyV1
    from app.domain import build_context, evaluate
    from test_finance_engine import HISTORY, POS, VENDORS, facts

    original = facts("HAPPY_CLEAN")
    context = build_context(original, VENDORS, POS, HISTORY)
    assert evaluate(context, PolicyV1()).outcome == "READY_FOR_AP"
    flagged = original.model_copy(update={"document_integrity_flags": ("RASTER_CONTENT_UNRESOLVED",)})
    outcome = evaluate(build_context(flagged, VENDORS, POS, HISTORY), PolicyV1())
    assert outcome.outcome == "REVIEW_REQUIRED"
    assert outcome.primary_reason_code == "DOCUMENT_CONTENT_UNVERIFIED"
    assert flagged.evidence == original.evidence

def test_legacy_snapshot_and_review_history_survive_sqlite_copy(tmp_path):
    import sqlite3

    from app.contracts import RunSnapshotV1
    from test_review_api import complete

    async def forbidden(_raw):
        pytest.fail("Historical load unexpectedly called the extractor")

    async def scenario():
        original_path = tmp_path / "legacy.db"
        docs = tmp_path / "documents"
        source = create_app(original_path, document_dir=docs, extractor=forbidden)
        async with source.router.lifespan_context(source):
            baseline = authority(source.state.engine)
            run_path = "/api/runs/" + complete(source)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=source), base_url="http://test") as client:
                recorded = (await client.get(run_path)).json()
                assert "document_integrity_flags" not in recorded["extracted_invoice"]
                loaded = RunSnapshotV1.model_validate(recorded)
                assert loaded.extracted_invoice.document_integrity_flags is None
                assert loaded.model_dump(mode="json") == recorded
                response = await client.post(run_path + "/po-confirmations", json=body())
                assert response.status_code == 201
                assert response.json()["reassessment"]["outcome"] == "READY_FOR_AP"
                history = (await client.get(run_path + "/review-history")).json()

        copied_path = tmp_path / "copy.db"
        with sqlite3.connect(original_path.as_uri() + "?mode=ro", uri=True) as old:
            with sqlite3.connect(copied_path) as new:
                old.backup(new)
        def stored_rows(path):
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
                return (
                    db.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall(),
                    db.execute("SELECT payload FROM invoice_run ORDER BY id").fetchall(),
                    db.execute("SELECT payload FROM review_action ORDER BY id").fetchall(),
                )

        before = stored_rows(copied_path)
        copy = create_app(copied_path, document_dir=docs, extractor=forbidden)
        async with copy.router.lifespan_context(copy):
            assert authority(copy.state.engine) == baseline
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=copy), base_url="http://test") as client:
                assert (await client.get(run_path)).json() == recorded
                assert (await client.get(run_path + "/review-history")).json() == history
        assert stored_rows(copied_path) == before

    asyncio.run(scenario())

@pytest.mark.parametrize("mixed", [False, True])
def test_real_bank_grounding_preserves_native_support(mixed):
    from copy import deepcopy

    from app.contracts import PolicyV1
    from app.documents.fixtures import native_case
    from app.domain import build_context, evaluate
    from test_document_engine import CASES
    from test_finance_engine import HISTORY, POS, VENDORS

    case = deepcopy(CASES["BANK_CHANGED"])
    master = next(v.verified_bank for v in VENDORS if v.id == "V-BRI")
    bank = master.model_dump()
    case["bank_instructions"] = bank
    response = wire("BANK_CHANGED", line_net=False)
    response["bank_instructions"] = bank
    for claim in response["evidence"]:
        if claim["field"].startswith("bank_instructions."):
            field = claim["field"].split(".")[1]
            label = "Account number" if field == "account" else "IFSC"
            claim.update(raw_value=bank[field], quote=f"{label}: {bank[field]}")
    raw = native_case(case)
    if mixed:
        raw = with_logo(raw)
    provider = FakeProvider([json.dumps(response)])
    result = asyncio.run(extract_pdf(raw, provider, max_attempts=1))
    invoice = result.invoice
    states = {r.evidence_state for r in invoice.evidence if r.field.startswith("bank_instructions.")}
    assert states == {"SOURCE_LOCATED_UNVERIFIED" if mixed else "NATIVE_VERIFIED"}
    decision = evaluate(build_context(invoice, VENDORS, POS, HISTORY), PolicyV1())
    assert decision.outcome == ("REVIEW_REQUIRED" if mixed else "READY_FOR_AP")
    codes = {f.code for f in decision.findings}
    assert "BANK_DETAILS_MISMATCH" not in codes
    assert ("BANK_DETAILS_UNVERIFIED" in codes) is mixed
    assert ("DOCUMENT_CONTENT_UNVERIFIED" in codes) is mixed
