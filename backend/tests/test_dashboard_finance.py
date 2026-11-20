"""Dashboard reads SQLite authority and recorded outcomes without re-evaluating runs."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dashboard_finance import procurement_capacity, vendor_attention
from app.contracts import DecisionV1, ExtractedInvoiceV1, FindingV1, PolicyV1, RunSnapshotV1, VendorV1
from app.db.models import InvoiceRun
from app.main import create_app
from test_orchestration_api import authority
from test_review_api import body, complete

SOURCE = FindingV1(code="SOURCE_EVIDENCE_MISSING", severity="REVIEW", title="Source review",
                   explanation="Verify source", source_type="invoice")
DUPLICATE = FindingV1(code="EXACT_DUPLICATE", severity="BLOCK", title="Duplicate",
                      explanation="Prior billing", source_type="invoice")


def record(repo, state, name, outcome=None, amount=None, currency="INR", findings=()):
    run = repo.create("a" * 32)
    repo.update(run.id, execution_state=state,
                execution_error_code="PROVIDER_TIMEOUT" if state == "PROCESSING_FAILED" else None,
                extracted_invoice=ExtractedInvoiceV1(vendor_name_raw=name, invoice_number="DUP-1",
                                                    total=amount, currency=currency),
                policy_snapshot=PolicyV1(),
                decision=DecisionV1(outcome=outcome, policy_version="policy-v1", findings=findings)
                if outcome else None)
    return repo.load(run.id)


def test_dashboard_aggregates_original_attention_and_prior_billing_after_restart(tmp_path):
    path = tmp_path / "runs.db"
    app = create_app(path, document_dir=tmp_path / "docs")
    with TestClient(app) as client:
        ledger = authority(app.state.engine)
        repo = app.state.runs.repository
        reviewed_id = complete(app)
        record(repo, "COMPLETED", "Meridian Cloud Ltd.", "BLOCKED", "118.50", findings=(DUPLICATE,))
        record(repo, "COMPLETED", "Meridian Cloud Pvt Ltd", "REVIEW_REQUIRED", "5.25", "USD", (SOURCE,))
        record(repo, "COMPLETED", "Meridian Cloud Ltd.", "BLOCKED", "118.50", findings=(DUPLICATE,))
        record(repo, "COMPLETED", "No gross Co", "REVIEW_REQUIRED", findings=(SOURCE,))
        record(repo, "PROCESSING_FAILED", "Failed vendor", amount=None)
        before = client.get("/api/dashboard").json()
        reply = client.post(f"/api/runs/{reviewed_id}/po-confirmations", json=body())
        assert reply.status_code == 201 and reply.json()["reassessment"]["outcome"] == "READY_FOR_AP"
        assert client.get("/api/dashboard").json() == before
        assert authority(app.state.engine) == ledger

    with TestClient(create_app(path, document_dir=tmp_path / "docs")) as client:
        data = client.get("/api/dashboard").json()
        assert data == before
        meridian, unknown = data["vendor_attention"]
        assert meridian["name"] == "Meridian Cloud Pvt Ltd"
        assert meridian["source_names"] == ["Meridian Cloud Ltd.", "Meridian Cloud Pvt Ltd"]
        assert meridian["review_count"] == meridian["blocked_count"] == 2
        assert meridian["gross_by_currency"] == {"INR": "12037.00", "USD": "5.25"}
        assert unknown["missing_gross_count"] == 1 and unknown["gross_by_currency"] == {}
        assert data["processing_failed"] == 1
        assert data["invoice_gross"]["submitted"]["missing_count"] == 2
        assert {"code": "EXACT_DUPLICATE", "count": 2} in data["exception_insights"]
        po = next(row for row in data["procurement_capacity"] if row["po_id"] == "PO-1042")
        assert (po["approved_net"], po["previously_billed_net"], po["remaining_net"]) == ("200000", "120000", "80000")


def test_vendor_gross_sort_scope_and_empty_results(tmp_path):
    app = create_app(tmp_path / "runs.db", document_dir=tmp_path / "docs")
    with TestClient(app) as client:
        assert client.get("/api/dashboard").json()["vendor_attention"] == []
        repo = app.state.runs.repository
        items = [("Exclude this oldest vendor", "INR", "1000000", (DUPLICATE,))]
        items.extend((f"Vendor {n:02}", "INR", str(n), (SOURCE,)) for n in range(99))
        items.append(("Foreign vendor", "USD", "9999999", (SOURCE,)))
        created = datetime(2025, 1, 1, tzinfo=timezone.utc)
        with Session(app.state.engine) as session, session.begin():
            for i, (vendor, currency, total, findings) in enumerate(items):
                snapshot = RunSnapshotV1(
                    id=f"manual-{i}", document_id="x" * 32, execution_state="COMPLETED",
                    created_at=created + timedelta(seconds=i), updated_at=created + timedelta(seconds=i),
                    extracted_invoice=ExtractedInvoiceV1(vendor_name_raw=vendor, total=total, currency=currency),
                    policy_snapshot=PolicyV1(),
                    decision=DecisionV1(outcome="REVIEW_REQUIRED", findings=findings, policy_version="policy-v1"),
                )
                session.add(InvoiceRun(id=snapshot.id, payload=snapshot.model_dump(mode="json")))
        data = client.get("/api/dashboard").json()
        assert data["total_runs"] == 101
        assert [r["name"] for r in data["vendor_attention"]] == [f"Vendor {n}" for n in range(98, 88, -1)]
        assert data["exception_insights"] == [{"code": "SOURCE_EVIDENCE_MISSING", "count": 100}]


def test_attention_keeps_ambiguous_or_unapproved_vendor_spellings(tmp_path):
    app = create_app(tmp_path / "runs.db", document_dir=tmp_path / "docs")
    with TestClient(app):
        repo = app.state.runs.repository
        cases = [record(repo, "COMPLETED", name, "REVIEW_REQUIRED", "1.0000001")
                 for name in ("Twin", "TWIN", "Unapproved Alias")]
        vendors = [VendorV1(id="V-1", name="One", aliases=("Twin",), approved=True),
                   VendorV1(id="V-2", name="Two", aliases=("Twin",), approved=True),
                   VendorV1(id="V-3", name="Three", aliases=("Unapproved Alias",), approved=False)]
        assert {row["name"] for row in vendor_attention(cases, vendors)} == {"Twin", "TWIN", "Unapproved Alias"}
        masters, orders, prior = repo.authority()
        row = prior[0]
        wrong_currency = (row.model_copy(update={"currency": "USD"}), *prior[1:])
        capacity = procurement_capacity(masters, orders, wrong_currency)
        inconsistent = next(item for item in capacity if item["po_id"] == row.po_id)
        assert inconsistent["remaining_net"] is None and inconsistent["previously_billed_net"] is None
