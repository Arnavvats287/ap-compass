"""API-local display projection; synthetic snapshots, no new finance behavior."""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.contracts import DecisionV1, ExtractedInvoiceV1, PolicyV1
from app.main import create_app


def record(repository, outcome, net, currency="INR", total="999999"):
    run = repository.create("0" * 32)
    repository.update(run.id, execution_state="COMPLETED", extracted_invoice=ExtractedInvoiceV1(
        net=net, total=total, currency=currency), policy_snapshot=PolicyV1(),
        decision=DecisionV1(outcome=outcome, policy_version="policy-v1"))
    return run


def test_flagged_projection_is_known_net_per_currency_and_completed_only(tmp_path):
    app = create_app(tmp_path/"db", document_dir=tmp_path/"documents")
    with TestClient(app) as client:
        repo = app.state.runs.repository
        record(repo, "BLOCKED", "30000")
        record(repo, "REVIEW_REQUIRED", "70000")
        record(repo, "REVIEW_REQUIRED", "123.45", "USD")
        record(repo, "READY_FOR_AP", "48000")
        record(repo, "REVIEW_REQUIRED", None)
        record(repo, "BLOCKED", "99", None)
        failed = repo.create("0"*32)
        repo.update(failed.id, execution_state="PROCESSING_FAILED", execution_error_code="PROVIDER_TIMEOUT",
                    extracted_invoice=ExtractedInvoiceV1(net="50000", currency="INR"))
        result = client.get("/api/dashboard").json()
        assert result["flagged_invoice_net_by_currency"] == {"INR": "100000", "USD": "123.45"}
        assert result["flagged_invoice_net_missing_count"] == 2
        assert result["total_runs"] == 7 and result["completed"] == 6
        assert result["ready"] == 1 and result["blocked"] == 2 and result["review_required"] == 3
        assert result["processing_failed"] == 1


def test_flagged_projection_preserves_large_and_subminor_decimal_precision(tmp_path):
    app = create_app(tmp_path/"db", document_dir=tmp_path/"documents")
    with TestClient(app) as client:
        repo = app.state.runs.repository
        record(repo, "BLOCKED", "1000000000000000000000000000000")
        record(repo, "REVIEW_REQUIRED", "0.00000000000000000000000000001")
        value = client.get("/api/dashboard").json()["flagged_invoice_net_by_currency"]["INR"]
        assert value == "1000000000000000000000000000000.00000000000000000000000000001"


def test_empty_projection_does_not_fabricate_amounts(tmp_path):
    app = create_app(tmp_path/"db", document_dir=tmp_path/"documents")
    with TestClient(app) as client:
        result = client.get("/api/dashboard").json()
        assert result["total_runs"] == 0
        assert result["flagged_invoice_net_by_currency"] == {}
        assert result["flagged_invoice_net_missing_count"] == 0
