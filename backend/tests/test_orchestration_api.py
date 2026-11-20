"""Phase 4 real API/persistence/domain integration. Providers below are TEST DATA."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.main import create_app
from app.contracts import RunSnapshotV1, PolicyV1
from app.db.models import InvoiceRun, RunStage, Vendor, PurchaseOrder, POLine, PriorBilledInvoice, PolicySnapshot
from app.documents.pipeline import extract_pdf
from app.documents.types import ExtractionError
from app.orchestration.documents import DocumentStore
from test_document_engine import FakeProvider, wire, CASES, ROOT


class Extractor:
    def __init__(self, case="HAPPY_CLEAN", error=None, entered=None, release=None):
        self.case, self.error, self.entered, self.release = case, error, entered, release
        self.calls = 0
        self.provider = FakeProvider([json.dumps(wire(case))])

    async def __call__(self, raw):
        self.calls += 1
        if self.entered:
            self.entered.set()
        if self.release:
            await self.release.wait()
        if self.error:
            raise self.error
        return await extract_pdf(raw, self.provider, max_attempts=1)


def authority(engine):
    with engine.connect() as connection:
        return {model.__tablename__: tuple(tuple(row) for row in connection.execute(select(model.__table__).order_by(model.id)))
                for model in (Vendor, PurchaseOrder, POLine, PriorBilledInvoice)}


async def upload(client, case="HAPPY_CLEAN", filename=None, data=None, mime="application/pdf"):
    raw = data if data is not None else (ROOT / "tests/fixtures" / (case + ".pdf")).read_bytes()
    return await client.post("/api/runs", files={"file": (filename or case + ".pdf", raw, mime)})


@pytest.mark.parametrize("case", ["HAPPY_CLEAN", "HAPPY_PARTIAL", "OVERBILLED_PARTIAL", "DUPLICATE_REISSUED", "SCAN_CONFLICT"])
def test_e2e_real_pdf_with_fake_provider_and_restart(tmp_path, case):
    async def scenario():
        extractor = Extractor(case)
        app = create_app(tmp_path/"db.sqlite", document_dir=tmp_path/"documents", extractor=extractor)
        async with app.router.lifespan_context(app):
            before = authority(app.state.engine)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await upload(client, case)
                assert response.status_code == 202 and response.json()["execution_state"] == "QUEUED"
                run_id = response.json()["run_id"]
                await app.state.runs.idle()
                result = (await client.get(f"/api/runs/{run_id}")).json()
                assert result["execution_state"] == "COMPLETED"
                assert result["execution_error_code"] is None
                assert result["decision"]["outcome"] == CASES[case]["expected_decision"]
                codes = {f["code"] for f in result["decision"]["findings"]}
                assert set(CASES[case]["required_reason_codes"]) <= codes
                assert result["usage"] == {"model_calls": 1, "input_tokens": 10, "output_tokens": 20}
                assert all(s["state"] == "PASSED" and s["started_at"] and s["finished_at"] for s in result["stages"])
                assert all(s["finished_at"] >= s["started_at"] for s in result["stages"])
                assert {t["name"] for t in result["timings"]} == {"extraction", "matching", "evaluation", "total_processing"}
                if case == "SCAN_CONFLICT":
                    assert result["extracted_invoice"]["lines"][0]["net"] is None
                    assert result["extracted_invoice"]["total"] == "86200"
                    assert "SOURCE_EVIDENCE_MISSING" in codes
                if case == "OVERBILLED_PARTIAL":
                    assert result["candidates"][0]["po"]["id"] == "PO-3015"
                listing = (await client.get("/api/runs")).json()
                assert listing[0]["outcome"] == CASES[case]["expected_decision"]
                assert listing[0]["total"] == CASES[case]["gross"]
                assert (await client.get("/api/dashboard")).json()["completed"] == 1
                assert (await client.get("/api/policy")).json() == PolicyV1().model_dump(mode="json")
                pdf = await client.get(f"/api/runs/{run_id}/document")
                assert pdf.content == (ROOT/"tests/fixtures"/(case+".pdf")).read_bytes()
                assert pdf.headers["cache-control"] == "no-store" and pdf.headers["x-content-type-options"] == "nosniff"
                assert pdf.headers["content-type"] == "application/pdf"
                assert authority(app.state.engine) == before
                with Session(app.state.engine) as session:
                    assert session.get(InvoiceRun, run_id).payload["stages"] == []
        app2 = create_app(tmp_path/"db.sqlite", document_dir=tmp_path/"documents", extractor=extractor)
        async with app2.router.lifespan_context(app2):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app2), base_url="http://test") as client:
                assert (await client.get(f"/api/runs/{run_id}")).json() == result
                assert (await client.get(f"/api/runs/{run_id}/document")).content == pdf.content
                assert extractor.calls == 1
                assert authority(app2.state.engine) == before
    asyncio.run(scenario())


@pytest.mark.parametrize("error,code", [(ExtractionError("PROVIDER_TIMEOUT", calls=1), "PROVIDER_TIMEOUT"),
    (RuntimeError("SECRET_ACCOUNT_009999 API_KEY sensitive response"), "INTERNAL_ERROR"),
    (ExtractionError("NOT_ALLOWLISTED"), "INTERNAL_ERROR")])
def test_technical_failures_are_sanitized(tmp_path, caplog, error, code):
    async def scenario():
        app = create_app(tmp_path/"db", document_dir=tmp_path/"docs", extractor=Extractor(error=error))
        async with app.router.lifespan_context(app):
            before = authority(app.state.engine)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await upload(client)
                await app.state.runs.idle()
                result = (await client.get("/api/runs/"+response.json()["run_id"])).json()
                assert result["execution_state"] == "PROCESSING_FAILED" and result["decision"] is None
                assert result["execution_error_code"] == code
                assert [s["state"] for s in result["stages"]] == ["PASSED", "FAILED", "SKIPPED", "SKIPPED", "SKIPPED"]
                assert all(s["finished_at"] for s in result["stages"])
                assert "SECRET_ACCOUNT" not in json.dumps(result) + caplog.text
                assert "API_KEY" not in json.dumps(result) + caplog.text
                assert authority(app.state.engine) == before
    asyncio.run(scenario())


@pytest.mark.parametrize("data,mime,status", [(b"", "application/pdf", 400), (b"not pdf", "application/pdf", 400),
    (b"%PDF-1.7", "text/plain", 415), (b"%PDF-"+b"x"*(8*1024*1024), "application/pdf", 413)], ids=["empty", "signature", "mime", "oversized"])
def test_invalid_request_never_creates_work(tmp_path, data, mime, status):
    async def scenario():
        extractor = Extractor()
        app = create_app(tmp_path/"db", document_dir=tmp_path/"docs", extractor=extractor)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                assert (await upload(client, data=data, mime=mime)).status_code == status
                assert extractor.calls == 0
                assert (await client.get("/api/runs")).json() == []
                assert list((tmp_path/"docs").iterdir()) == []
    asyncio.run(scenario())


def test_live_progress_and_serial_capacity(tmp_path):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        extractor = Extractor(entered=entered, release=release)
        extractor.provider.replies *= 2
        app = create_app(tmp_path/"db", document_dir=tmp_path/"docs", extractor=extractor)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                first = (await upload(client)).json()["run_id"]
                await asyncio.wait_for(entered.wait(), 5)
                second = (await upload(client)).json()["run_id"]
                state = (await client.get("/api/runs/"+first)).json()
                assert state["execution_state"] == "RUNNING"
                assert state["stages"][1]["state"] == "RUNNING"
                assert state["stages"][1]["started_at"] and state["stages"][1]["finished_at"] is None
                assert (await client.get("/api/runs/"+second)).json()["execution_state"] == "QUEUED"
                assert extractor.calls == 1
                assert (await client.get("/api/dashboard")).json()["in_progress"] == 2
                release.set()
                await app.state.runs.idle()
                for identifier in (first, second):
                    assert (await client.get("/api/runs/"+identifier)).json()["execution_state"] == "COMPLETED"
                assert extractor.calls == 2
    asyncio.run(scenario())


@pytest.mark.parametrize("running", [False, True])
def test_restart_reconciles_stale_work_without_recall(tmp_path, running):
    async def scenario():
        extractor = Extractor()
        app = create_app(tmp_path/"db", document_dir=tmp_path/"docs", extractor=extractor)
        async with app.router.lifespan_context(app):
            repo = app.state.runs.repository
            run = repo.create(app.state.runs.documents.write(b"%PDF-stale"))
            if running:
                repo.update(run.id, execution_state="RUNNING", stages={"extracting_invoice": "RUNNING"})
        app = create_app(tmp_path/"db", document_dir=tmp_path/"docs", extractor=extractor)
        async with app.router.lifespan_context(app):
            result = app.state.runs.repository.load(run.id)
            assert result.execution_state == "INTERRUPTED" and result.execution_error_code == "SERVER_RESTART"
            assert result.decision is None and all(s.state not in ("RUNNING", "QUEUED") for s in result.stages)
            assert extractor.calls == 0
    asyncio.run(scenario())


@pytest.mark.parametrize("filename", ["../../stolen.pdf", "C:\\outside\\secret.pdf", "same.pdf", "发票💶.pdf"])
def test_filename_does_not_choose_storage(tmp_path, filename):
    async def scenario():
        extractor = Extractor()
        extractor.provider.replies *= 2
        app = create_app(tmp_path/"db", document_dir=tmp_path/"docs", extractor=extractor)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                ids = [(await upload(client, filename=filename)).json()["run_id"] for _ in range(2)]
                await app.state.runs.idle()
                documents = [app.state.runs.repository.load(identifier).document_id for identifier in ids]
                assert len(set(documents)) == 2
                assert {p.name for p in (tmp_path/"docs").iterdir()} == {d+".pdf" for d in documents}
                assert filename not in json.dumps((await client.get("/api/runs")).json(), ensure_ascii=False)
    asyncio.run(scenario())


def test_stage_rows_override_legacy_duplicate_and_writes_strip_it(tmp_path):
    async def scenario():
        app = create_app(tmp_path/"db", document_dir=tmp_path/"docs", extractor=Extractor())
        async with app.router.lifespan_context(app):
            repo = app.state.runs.repository
            run = repo.create("0"*32)
            with Session(app.state.engine) as session, session.begin():
                row = session.get(InvoiceRun, run.id)
                row.payload = {**row.payload, "stages": [{"name": "extracting_invoice", "state": "PASSED"}]}
            assert repo.load(run.id).stages[1].state == "QUEUED"
            repo.update(run.id, stages={"extracting_invoice": "RUNNING"}, execution_state="RUNNING")
            with Session(app.state.engine) as session:
                assert session.get(InvoiceRun, run.id).payload["stages"] == []
            assert repo.load(run.id).stages[1].state == "RUNNING"
    asyncio.run(scenario())


def test_policy_collision_never_overwrites_and_fails_run(tmp_path):
    async def scenario():
        app = create_app(tmp_path/"db", document_dir=tmp_path/"docs", extractor=Extractor())
        async with app.router.lifespan_context(app):
            repo = app.state.runs.repository
            original = repo.policy(PolicyV1())
            app.state.runs.current_policy = PolicyV1(price_tolerance_pct="0.05")
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                identifier = (await upload(client)).json()["run_id"]
                await app.state.runs.idle()
                result = repo.load(identifier)
                assert result.execution_error_code == "INTERNAL_ERROR" and result.decision is None
                assert [s.state for s in result.stages] == ["PASSED", "PASSED", "PASSED", "FAILED", "SKIPPED"]
            with Session(app.state.engine) as session:
                assert session.get(PolicySnapshot, original.version).payload == original.model_dump(mode="json")
    asyncio.run(scenario())


def test_missing_credentials_server_boots_run_fails(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    async def scenario():
        app = create_app(tmp_path/"db", document_dir=tmp_path/"docs")
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                assert (await client.get("/api/health")).status_code == 200
                identifier = (await upload(client)).json()["run_id"]
                await app.state.runs.idle()
                result = (await client.get("/api/runs/"+identifier)).json()
                assert result["execution_state"] == "PROCESSING_FAILED" and result["execution_error_code"] == "CONFIGURATION"
                assert result["decision"] is None
    asyncio.run(scenario())


def test_deep_malformed_pdf_fails_after_acceptance(tmp_path):
    async def scenario():
        app = create_app(tmp_path/"db", document_dir=tmp_path/"docs", extractor=Extractor())
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await upload(client, data=b"%PDF-broken")
                assert response.status_code == 202
                await app.state.runs.idle()
                run = (await client.get("/api/runs/"+response.json()["run_id"])).json()
                assert run["execution_state"] == "PROCESSING_FAILED" and run["execution_error_code"] == "INVALID_PDF"
                assert run["decision"] is None
    asyncio.run(scenario())


def test_list_is_one_query_and_limits_paths_errors(tmp_path):
    async def scenario():
        app = create_app(tmp_path/"db", document_dir=tmp_path/"docs", extractor=Extractor())
        async with app.router.lifespan_context(app):
            repo = app.state.runs.repository
            for _ in range(3):
                repo.create("0"*32)
            calls = []
            def track(*args): calls.append(args[2])
            event.listen(app.state.engine, "before_cursor_execute", track)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                result = await client.get("/api/runs?limit=2")
                assert result.status_code == 200 and len(result.json()) == 2
                assert len(calls) == 1
                assert (await client.get("/api/runs?limit=101")).status_code == 422
                assert (await client.get("/api/runs?limit=0")).status_code == 422
                assert (await client.get("/api/runs/missing")).status_code == 404
                assert (await client.get("/api/runs/missing/document")).status_code == 404
                assert (await client.get("/api/runs/..%2f..%2f.env/document")).status_code == 404
                response = await client.post("/api/runs", files=[("file", ("a.pdf", b"%PDF-", "application/pdf")), ("file", ("b.pdf", b"%PDF-", "application/pdf"))])
                assert response.status_code == 400
                assert (await client.post("/api/runs", data={"file": "x"})).status_code == 415
            event.remove(app.state.engine, "before_cursor_execute", track)
    asyncio.run(scenario())


@pytest.mark.parametrize("identifier", ["../.env", "C:\\secret.pdf", "/etc/passwd", "z"*32])
def test_document_store_rejects_untrusted_identifier(tmp_path, identifier):
    store = DocumentStore(tmp_path)
    with pytest.raises(FileNotFoundError):
        store.read(identifier)


@pytest.mark.parametrize("state", ["QUEUED", "RUNNING", "COMPLETED"])
def test_error_contract_rejects_nonfailure_state(state):
    from datetime import datetime, timezone
    with pytest.raises(ValidationError):
        RunSnapshotV1(id="a", document_id="b", execution_state=state, execution_error_code="INTERNAL_ERROR",
                      created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))


def test_historical_snapshot_default_and_allowlist():
    from datetime import datetime, timezone
    values = dict(id="a", document_id="b", execution_state="PROCESSING_FAILED", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    assert RunSnapshotV1(**values).execution_error_code is None
    with pytest.raises(ValidationError):
        RunSnapshotV1(**values, execution_error_code="secret-provider-message")


def test_runtime_generation_skips_metadata_and_closes_client(monkeypatch):
    from types import SimpleNamespace
    from app.ai import gemini
    calls = []
    async def generate(**kwargs):
        calls.append(kwargs['model'])
        return SimpleNamespace(text=json.dumps(wire()), model_version='gemini-3.5-flash-lite', usage_metadata=None, candidates=[])
    async def get(**kwargs):
        raise AssertionError('Production must not request model metadata')
    async def close(): calls.append('async_closed')
    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate, get=get), aclose=close), close=lambda: calls.append('closed'))
    monkeypatch.setattr(gemini, 'make_client', lambda settings: client)
    monkeypatch.setenv('GEMINI_API_KEY', 'TEST_ONLY_KEY')
    monkeypatch.setenv('GEMINI_ESCALATION_ENABLED', 'false')
    monkeypatch.setenv('GEMINI_PRIMARY_MODEL', 'gemini-3.5-flash-lite')
    result = asyncio.run(gemini.extract_runtime_pdf((ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes()))
    assert result.metadata.model_calls == 1
    assert calls == ['gemini-3.5-flash-lite', 'async_closed', 'closed']
    assert all(ref.evidence_state == 'NATIVE_VERIFIED' for ref in result.invoice.evidence)


def test_runtime_never_constructs_optional_model(monkeypatch):
    from app.ai import gemini
    monkeypatch.setenv('GEMINI_API_KEY', 'TEST_ONLY_KEY')
    monkeypatch.setenv('GEMINI_ESCALATION_ENABLED', 'true')
    monkeypatch.setattr(gemini, 'make_client', lambda settings: pytest.fail('No model client expected'))
    with pytest.raises(ExtractionError, match='CONFIGURATION'):
        asyncio.run(gemini.extract_runtime_pdf(b'%PDF-'))


def test_document_lookup_resolves_via_run_and_refuses_corrupt_path(tmp_path):
    async def scenario():
        app = create_app(tmp_path/'db', document_dir=tmp_path/'docs', extractor=Extractor())
        async with app.router.lifespan_context(app):
            repo = app.state.runs.repository
            run = repo.create('../.env')
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                result = await client.get('/api/runs/'+run.id+'/document')
                assert result.status_code == 404
                assert str(tmp_path) not in result.text
    asyncio.run(scenario())


def test_chunked_envelope_limit_and_malformed_multipart(tmp_path):
    async def scenario():
        extractor = Extractor()
        app = create_app(tmp_path/'db', document_dir=tmp_path/'docs', extractor=extractor)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                async def large_chunks():
                    for _ in range(10):
                        yield b'x'*(1024*1024)
                response = await client.post('/api/runs', headers={'Content-Type': 'multipart/form-data; boundary=safe'}, content=large_chunks())
                assert response.status_code == 413
                response = await client.post('/api/runs', headers={'Content-Type': 'multipart/form-data; boundary=safe'}, content=b'not-a-multipart-envelope')
                assert response.status_code == 400
                assert extractor.calls == 0 and app.state.runs.repository.all() == []
    asyncio.run(scenario())


def test_completed_error_contract_even_with_valid_decision():
    from datetime import datetime, timezone
    from app.contracts import DecisionV1
    with pytest.raises(ValidationError, match='Only technical terminal states'):
        RunSnapshotV1(id='a', document_id='b', execution_state='COMPLETED', execution_error_code='INTERNAL_ERROR',
            policy_snapshot=PolicyV1(), decision=DecisionV1(outcome='READY_FOR_AP', policy_version='policy-v1'),
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))


def test_detail_uses_one_atomic_read_for_snapshot_and_stage_rows(tmp_path):
    async def scenario():
        app = create_app(tmp_path/'db', document_dir=tmp_path/'docs', extractor=Extractor())
        async with app.router.lifespan_context(app):
            repo = app.state.runs.repository
            run = repo.create('0'*32)
            queries = []
            def track(*args): queries.append(args[2])
            event.listen(app.state.engine, 'before_cursor_execute', track)
            result = repo.load(run.id)
            event.remove(app.state.engine, 'before_cursor_execute', track)
            assert result.execution_state == 'QUEUED' and len(result.stages) == 5
            assert len(queries) == 1
    asyncio.run(scenario())


def test_failed_extraction_keeps_reported_usage_but_unknown_stays_null():
    from app.documents.types import ModelAttempt, TokenUsage
    from app.orchestration.service import usage_snapshot
    attempt = ModelAttempt(1, 'TEST', 10, 'INVALID_RESPONSE', 'TEST', TokenUsage(4, 6, None, 10))
    assert usage_snapshot(1, (attempt,)).model_dump() == dict(model_calls=1, input_tokens=4, output_tokens=6)
    unknown = replace(attempt, number=2, usage=TokenUsage())
    assert usage_snapshot(2, (attempt, unknown)).input_tokens is None
    assert usage_snapshot(0, ()).output_tokens is None

def test_failed_provider_http_status_is_logged_without_changing_snapshot(tmp_path, caplog):
    from app.documents.types import ExtractionError

    async def fail(_):
        raise ExtractionError("PROVIDER_UNAVAILABLE", provider_status=503, calls=1)

    async def scenario():
        app = create_app(tmp_path / "runs.db", document_dir=tmp_path / "docs", extractor=fail)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                posted = await upload(client, data=(ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes())
                assert posted.status_code == 202
                await app.state.runs.idle()
                snapshot = (await client.get("/api/runs/" + posted.json()["run_id"])).json()
                assert snapshot["execution_error_code"] == "PROVIDER_UNAVAILABLE"
                assert "provider_http_status" not in snapshot
                assert snapshot["decision"] is None
                assert snapshot["usage"]["model_calls"] == 1

    asyncio.run(scenario())
    assert "stage=extracting_invoice error=PROVIDER_UNAVAILABLE elapsed_ms=" in caplog.text
    assert "provider_http_status=503" in caplog.text
