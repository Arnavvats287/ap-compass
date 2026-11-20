from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.db.models import InvoiceRun
from app.documents.types import ExtractionError
from app.main import create_app
from review_fixtures import ReviewExtractor
from test_orchestration_api import Extractor, ROOT, authority
from test_review_api import body as confirmation


RAW = (ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes()


def post(client, raw=RAW, filename="invoice.pdf"):
    reply = client.post("/api/runs", files={"file": (filename, raw, "application/pdf")})
    assert reply.status_code == 202
    return reply.json()


def load(client, receipt):
    return client.get("/api/runs/" + receipt["run_id"]).json()


def test_identical_upload_reuses_active_and_completed_run_after_restart(tmp_path):
    extractor = Extractor()
    database, documents = tmp_path / "db", tmp_path / "documents"
    app = create_app(database, document_dir=documents, extractor=extractor)
    with TestClient(app) as client:
        client.portal.call(app.state.runs.semaphore.acquire)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                requests = [pool.submit(post, client, RAW, name) for name in ("invoice.pdf", "renamed.pdf")]
                original, repeat = sorted((request.result() for request in requests),
                                          key=lambda receipt: receipt["reused"])
            assert repeat["run_id"] == original["run_id"]
            assert original["reused"] is False
            assert repeat["reused"] is True
            assert repeat["execution_state"] == "QUEUED"
        finally:
            client.portal.call(app.state.runs.semaphore.release)
        client.portal.call(app.state.runs.idle)
        saved = load(client, original)
        assert saved["decision"]["outcome"] == "READY_FOR_AP"
    app = create_app(database, document_dir=documents, extractor=extractor)
    with TestClient(app) as client:
        repeat = post(client)
        assert repeat["run_id"] == original["run_id"]
        assert repeat["execution_state"] == "COMPLETED"
        assert repeat["outcome"] == "READY_FOR_AP"
        assert load(client, repeat) == saved
        assert len(client.get("/api/runs").json()) == len(list(documents.iterdir())) == 1
        assert extractor.calls == 1


def test_same_verified_invoice_in_different_pdf_requires_review(tmp_path):
    extractor = Extractor()
    extractor.provider.replies *= 2
    app = create_app(tmp_path / "db", document_dir=tmp_path / "documents", extractor=extractor)
    with TestClient(app) as client:
        baseline = authority(app.state.engine)
        first = post(client)
        client.portal.call(app.state.runs.idle)
        original = load(client, first)
        # Older runs have no file fingerprint but still have their recorded evidence.
        with app.state.engine.begin() as connection:
            connection.execute(update(InvoiceRun).where(InvoiceRun.id == first["run_id"])
                               .values(document_sha256=None))
        second = post(client, RAW + b"\n")
        client.portal.call(app.state.runs.idle)
        duplicate = load(client, second)
        assert second["run_id"] != first["run_id"]
        assert duplicate["decision"]["outcome"] == "REVIEW_REQUIRED"
        assert duplicate["decision"]["primary_reason_code"] == "ALREADY_SUBMITTED"
        finding = next(f for f in duplicate["decision"]["findings"] if f["code"] == "ALREADY_SUBMITTED")
        assert finding["values"] == [{"name": "prior_run_id", "value": first["run_id"]}]
        assert not any(f["code"] == "EXACT_DUPLICATE" for f in duplicate["decision"]["findings"])
        preview = client.post(f'/api/runs/{second["run_id"]}/policy-preview',
                              json={"price_tolerance_pct": "0.05"})
        assert preview.status_code == 200
        assert preview.json()["preview_decision"]["primary_reason_code"] == "ALREADY_SUBMITTED"
        assert load(client, first) == original
        assert authority(app.state.engine) == baseline


def test_failed_exact_upload_can_be_retried(tmp_path):
    extractor = Extractor(error=ExtractionError("PROVIDER_TIMEOUT"))
    app = create_app(tmp_path / "db", document_dir=tmp_path / "documents", extractor=extractor)
    with TestClient(app) as client:
        failed = post(client)
        client.portal.call(app.state.runs.idle)
        assert load(client, failed)["execution_state"] == "PROCESSING_FAILED"
        extractor.error = None
        retry = post(client)
        client.portal.call(app.state.runs.idle)
        assert retry["run_id"] != failed["run_id"]
        assert load(client, retry)["decision"]["outcome"] == "READY_FOR_AP"
        assert extractor.calls == 2


def test_an_unverified_earlier_invoice_number_is_not_duplicate_proof(tmp_path):
    extractor = Extractor()
    extractor.provider.replies *= 2

    async def extract(raw):
        result = await extractor(raw)
        if raw == RAW:
            evidence = tuple(ref for ref in result.invoice.evidence if ref.field != "invoice_number")
            return replace(result, invoice=result.invoice.model_copy(update={"evidence": evidence}))
        return result

    app = create_app(tmp_path / "db", document_dir=tmp_path / "documents", extractor=extract)
    with TestClient(app) as client:
        first = post(client)
        client.portal.call(app.state.runs.idle)
        assert load(client, first)["decision"]["primary_reason_code"] == "SOURCE_EVIDENCE_MISSING"
        second = post(client, RAW + b"\n")
        client.portal.call(app.state.runs.idle)
        assert load(client, second)["decision"]["outcome"] == "READY_FOR_AP"


def test_previously_billed_block_takes_priority_over_submission_review(tmp_path):
    raw = (ROOT / "tests/fixtures/DUPLICATE_REISSUED.pdf").read_bytes()
    extractor = Extractor("DUPLICATE_REISSUED")
    extractor.provider.replies *= 2
    app = create_app(tmp_path / "db", document_dir=tmp_path / "documents", extractor=extractor)
    with TestClient(app) as client:
        post(client, raw)
        client.portal.call(app.state.runs.idle)
        repeated = post(client, raw + b"\n")
        client.portal.call(app.state.runs.idle)
        decision = load(client, repeated)["decision"]
        assert decision["outcome"] == "BLOCKED"
        assert decision["primary_reason_code"] == "EXACT_DUPLICATE"
        assert any(f["code"] == "ALREADY_SUBMITTED" for f in decision["findings"])


def test_confirming_missing_po_does_not_clear_submission_review(tmp_path):
    raw = (ROOT / "tests/fixtures/human_resolution/MISSING_PO_VALID.pdf").read_bytes()
    app = create_app(tmp_path / "db", document_dir=tmp_path / "documents", extractor=ReviewExtractor())
    with TestClient(app) as client:
        post(client, raw)
        client.portal.call(app.state.runs.idle)
        repeated = post(client, raw + b"\n")
        client.portal.call(app.state.runs.idle)
        response = client.post(f'/api/runs/{repeated["run_id"]}/po-confirmations', json=confirmation())
        assert response.status_code == 201, response.text
        assert response.json()["reassessment"]["primary_reason_code"] == "ALREADY_SUBMITTED"
