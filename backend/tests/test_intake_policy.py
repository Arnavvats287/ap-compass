"""Real upload, source grounding and finance controls with a local test provider."""
from io import BytesIO
from decimal import Decimal
import json

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.main import create_app
from test_document_engine import FakeProvider, wire
from test_orchestration_api import Extractor, ROOT, authority


def submit(client, app, case, tolerance=None):
    filename = case + ".pdf"
    raw = (ROOT / "tests/fixtures" / filename).read_bytes()
    params = {"price_tolerance_pct": tolerance} if tolerance is not None else {}
    response = client.post("/api/runs", params=params, files={"file": (filename, raw, "application/pdf")})
    assert response.status_code == 202
    app_service = app.state.runs
    client.portal.call(app_service.idle)
    return client.get("/api/runs/" + response.json()["run_id"]).json()


def test_intake_policy_records_real_price_decisions_without_rewriting_history(tmp_path):
    extractor = Extractor("PRICE_3PCT")
    # The second explicit policy still runs, but the known submission requires review.
    extractor.provider = FakeProvider([json.dumps(wire("PRICE_3PCT"))] * 2)
    app = create_app(tmp_path / "runs.db", document_dir=tmp_path / "pdfs", extractor=extractor)
    with TestClient(app) as client:
        ledger = authority(app.state.engine)
        default = client.get("/api/policy").json()
        original = submit(client, app, "PRICE_3PCT")
        relaxed = submit(client, app, "PRICE_3PCT", "0.05")
        assert original["policy_snapshot"] == default
        assert original["decision"]["outcome"] == "REVIEW_REQUIRED"
        assert original["decision"]["primary_reason_code"] == "PRICE_VARIANCE"
        assert relaxed["decision"]["outcome"] == "REVIEW_REQUIRED"
        relaxed_codes = {finding["code"] for finding in relaxed["decision"]["findings"]}
        assert "PRICE_VARIANCE" not in relaxed_codes
        assert "ALREADY_SUBMITTED" in relaxed_codes
        assert relaxed["decision"]["policy_version"] == relaxed["policy_snapshot"]["version"]
        assert relaxed["policy_snapshot"]["version"] != default["version"]
        assert relaxed["policy_snapshot"]["price_tolerance_pct"] == "0.05"
        assert all(
            relaxed["policy_snapshot"][key] == value
            for key, value in default.items() if key not in {"version", "price_tolerance_pct"}
        )
        assert client.get("/api/runs/" + original["id"]).json() == original
        assert client.get("/api/policy").json() == default
        dash = client.get("/api/dashboard").json()
        assert (dash["ready"], dash["review_required"], dash["blocked"]) == (0, 2, 0)
        totals = dash["invoice_gross"]
        assert totals["ready"]["by_currency"] == {}
        assert Decimal(totals["review_required"]["by_currency"]["INR"]) == Decimal("24308")
        assert Decimal(totals["submitted"]["by_currency"]["INR"]) == Decimal("24308")
        assert authority(app.state.engine) == ledger
        sheet = load_workbook(BytesIO(client.get("/api/exports/invoices.xlsx").content))["Invoice Register"]
        assert sheet.max_column == 14
        assert sheet["N4"].value == "Execution state"
        assert [(row[8], row[13]) for row in sheet.iter_rows(min_row=5, values_only=True)] == [
            ("Needs review", "COMPLETED"), ("Needs review", "COMPLETED"),
        ]


def test_selected_policy_is_already_recorded_while_run_is_queued(tmp_path):
    extractor = Extractor("PRICE_3PCT")
    app = create_app(tmp_path / "runs.db", document_dir=tmp_path / "pdfs", extractor=extractor)
    with TestClient(app) as client:
        service = app.state.runs
        client.portal.call(service.semaphore.acquire)
        try:
            raw = (ROOT / "tests/fixtures/PRICE_3PCT.pdf").read_bytes()
            accepted = client.post("/api/runs?price_tolerance_pct=0.05",
                                   files={"file": ("price.pdf", raw, "application/pdf")})
            assert accepted.status_code == 202
            url = "/api/runs/" + accepted.json()["run_id"]
            queued = client.get(url).json()
            assert queued["execution_state"] == "QUEUED"
            assert queued["policy_snapshot"]["price_tolerance_pct"] == "0.05"
            assert queued["decision"] is None
            assert extractor.calls == 0
        finally:
            client.portal.call(service.semaphore.release)
        client.portal.call(service.idle)
        completed = client.get(url).json()
        assert completed["policy_snapshot"] == queued["policy_snapshot"]
        assert completed["decision"]["outcome"] == "READY_FOR_AP"


@pytest.mark.parametrize("case, required", [
    ("OVERBILLED_PARTIAL", {"PO_BALANCE_EXCEEDED", "PO_QUANTITY_EXCEEDED"}),
    ("DUPLICATE_REISSUED", {"EXACT_DUPLICATE"}),
])
def test_intake_tolerance_preserves_hard_controls(tmp_path, case, required):
    app = create_app(tmp_path / "runs.db", document_dir=tmp_path / "pdfs", extractor=Extractor(case))
    with TestClient(app) as client:
        run = submit(client, app, case, "0.05")
        assert run["policy_snapshot"]["price_tolerance_pct"] == "0.05"
        assert run["decision"]["outcome"] == "BLOCKED"
        assert required <= {item["code"] for item in run["decision"]["findings"]}


@pytest.mark.parametrize("value", ["0.03", "5", "NaN", ""])
def test_invalid_intake_tolerances_do_not_create_runs(tmp_path, value):
    extractor = Extractor()
    app = create_app(tmp_path / "runs.db", document_dir=tmp_path / "pdfs", extractor=extractor)
    with TestClient(app) as client:
        reply = client.post("/api/runs", params={"price_tolerance_pct": value})
        assert reply.status_code == 422
        assert client.get("/api/runs").json() == []
        assert extractor.calls == 0
