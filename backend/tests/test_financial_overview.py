from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import create_app
from test_finance_engine import facts
from test_review_api import complete


def test_dashboard_projects_stored_gross_by_currency_and_keeps_technical_runs_separate(tmp_path):
    app = create_app(tmp_path / "db", document_dir=tmp_path / "docs")
    with TestClient(app) as client:
        repo = app.state.runs.repository

        def stored(case, gross, currency):
            run_id = complete(app, facts(case))
            invoice = repo.load(run_id).extracted_invoice
            repo.update(run_id, extracted_invoice=invoice.model_copy(update={
                "total": None if gross is None else Decimal(gross), "currency": currency,
            }))

        stored("HAPPY_PARTIAL", "9007199254740993.000007", "INR")
        stored("HAPPY_CLEAN", "0.000001", "INR")
        stored("HAPPY_CLEAN", "2.50", "USD")
        stored("OVERBILLED_PARTIAL", "10.00", "INR")
        stored("PRICE_3PCT", None, "INR")
        failed = repo.create("f" * 32)
        repo.terminate(failed.id, "INVALID_PDF")
        result = client.get("/api/dashboard").json()
        assert result["invoice_gross"] == {
            "submitted": {"by_currency": {"INR": "9007199254741003.000008", "USD": "2.50"}, "missing_count": 2},
            "ready": {"by_currency": {"INR": "9007199254740993.000008", "USD": "2.50"}, "missing_count": 0},
            "review_required": {"by_currency": {}, "missing_count": 1},
            "blocked": {"by_currency": {"INR": "10.00"}, "missing_count": 0},
        }
        assert result["flagged_invoice_net_by_currency"] == {"INR": "40300"}
        assert (result["ready"], result["review_required"], result["blocked"], result["processing_failed"]) == (3, 1, 1, 1)


def test_dashboard_empty_gross_uses_unknown_empty_buckets_not_currency_zeros(tmp_path):
    with TestClient(create_app(tmp_path / "db", document_dir=tmp_path / "docs")) as client:
        gross = client.get("/api/dashboard").json()["invoice_gross"]
    assert set(gross) == {"submitted", "ready", "review_required", "blocked"}
    assert all(value == {"by_currency": {}, "missing_count": 0} for value in gross.values())
