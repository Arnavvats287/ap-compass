"""Operational controls exercised with disposable storage and controlled providers."""
import asyncio
import secrets
from types import SimpleNamespace

from fastapi.testclient import TestClient
from google.genai import errors
import httpx2
import pytest
from sqlalchemy import event

from app.ai.gemini import GeminiProvider
from app.documents.pipeline import extract_pdf
from app.main import create_app
from test_document_engine import ROOT
from test_orchestration_api import Extractor, authority, upload
from test_review_api import body, complete

ORIGIN = "http://127.0.0.1:8080"


@pytest.fixture
def private(monkeypatch):
    credentials = ("demo-reviewer", secrets.token_urlsafe(32))
    monkeypatch.setenv("AP_COMPASS_MODE", "private")
    monkeypatch.setenv("AP_COMPASS_PRIVATE_ORIGIN", ORIGIN)
    monkeypatch.setenv("AP_COMPASS_PRIVATE_USERNAME", credentials[0])
    monkeypatch.setenv("AP_COMPASS_PRIVATE_PASSWORD", credentials[1])
    return credentials


def test_auth_covers_shell_api_documents_and_unknown_identifiers(tmp_path, private, monkeypatch):
    monkeypatch.setenv("AP_COMPASS_UPLOADS_ENABLED", "true")
    app = create_app(tmp_path / "db", document_dir=tmp_path / "documents", extractor=Extractor())
    with TestClient(app, base_url=ORIGIN) as client:
        for method, path in (("GET", "/"), ("GET", "/runs/example"), ("GET", "/api/health"),
                             ("GET", "/api/runs"), ("POST", "/api/runs"), ("GET", "/api/runs/missing"),
                             ("GET", "/api/runs/missing/document"), ("GET", "/api/dashboard"),
                             ("GET", "/api/runs/missing/review-history"),
                             ("POST", "/api/runs/missing/po-confirmations"),
                             ("POST", "/api/runs/missing/policy-preview"), ("GET", "/docs")):
            response = client.request(method, path)
            assert response.status_code == 401 and response.headers["www-authenticate"].startswith("Basic ")
            assert response.headers["cache-control"] == "no-store"
        for header in ("Basic !invalid", "Bearer anything"):
            assert client.get("/api/runs", headers={"Authorization": header}).status_code == 401
        assert client.get("/api/health", auth=private).status_code == 200
        assert client.get("/api/health", auth=private, headers={"Host": "testserver"}).status_code == 403
        raw = (ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes()
        file = {"file": ("original.pdf", raw, "application/pdf")}
        assert client.post("/api/runs", auth=private, files=file).status_code == 403
        assert client.post("/api/runs", auth=private, headers={"Origin": "https://different.invalid"}, files=file).status_code == 403
        accepted = client.post("/api/runs", auth=private, headers={"Origin": ORIGIN}, files=file)
        assert accepted.status_code == 202
        client.portal.call(app.state.runs.idle)
        base = "/api/runs/" + accepted.json()["run_id"]
        assert client.get(base + "/document").json() == client.get("/api/runs/missing/document").json()
        pdf = client.get(base + "/document", auth=private)
        assert pdf.content == raw and pdf.headers["content-type"] == "application/pdf"
        assert pdf.headers["cache-control"] == "no-store" and pdf.headers["x-content-type-options"] == "nosniff"
        assert pdf.headers["x-frame-options"] == "SAMEORIGIN"
        assert "frame-ancestors 'self'" in pdf.headers["content-security-policy"]


@pytest.mark.parametrize("name", ["ORIGIN", "USERNAME", "PASSWORD"])
def test_missing_private_configuration_fails_closed(tmp_path, private, monkeypatch, name):
    monkeypatch.delenv("AP_COMPASS_PRIVATE_" + name)
    with pytest.raises(RuntimeError, match="Private"):
        create_app(tmp_path / "db")
    assert not (tmp_path / "db").exists()


@pytest.mark.parametrize("value", ["http://demo.example", "https://demo.example/path", "https://demo.example?x=1", "http://127.0.0.1:0"])
def test_invalid_private_origin_is_rejected(tmp_path, private, monkeypatch, value):
    monkeypatch.setenv("AP_COMPASS_PRIVATE_ORIGIN", value)
    with pytest.raises(RuntimeError, match="origin"):
        create_app(tmp_path / "db")


def test_https_origin_does_not_challenge_plaintext_or_trust_forwarded_headers(tmp_path, private, monkeypatch):
    monkeypatch.setenv("AP_COMPASS_PRIVATE_ORIGIN", "https://demo.example")
    with TestClient(create_app(tmp_path / "db", document_dir=tmp_path / "docs"), base_url="http://demo.example") as client:
        response = client.get("/api/health", auth=private, headers={"X-Forwarded-Proto": "https"})
        assert response.status_code == 403 and "www-authenticate" not in response.headers
        assert client.get("https://demo.example/api/health", auth=private).status_code == 200


def test_private_uploads_disabled_by_default_without_blocking_history(tmp_path, private, monkeypatch):
    monkeypatch.delenv("AP_COMPASS_UPLOADS_ENABLED", raising=False)
    app = create_app(tmp_path / "db", document_dir=tmp_path / "docs", extractor=Extractor())
    with TestClient(app, base_url=ORIGIN) as client:
        run_id = complete(app)
        response = client.post("/api/runs", auth=private, headers={"Origin": ORIGIN})
        assert response.status_code == 403 and "uploads are disabled" in response.json()["detail"]
        assert client.get(f"/api/runs/{run_id}", auth=private).status_code == 200
        assert not list((tmp_path / "docs").iterdir())
        assert len(client.get("/api/runs", auth=private).json()) == 1


def test_concurrent_admission_keeps_reads_and_review_writes_available(tmp_path, private, monkeypatch):
    import httpx

    monkeypatch.setenv("AP_COMPASS_UPLOAD_CAPACITY", "2")
    monkeypatch.setenv("AP_COMPASS_UPLOADS_ENABLED", "true")

    async def scenario():
        slow = Extractor()
        slow.entered, slow.release = asyncio.Event(), asyncio.Event()
        slow.provider.replies *= 2
        app = create_app(tmp_path / "db", document_dir=tmp_path / "docs", extractor=slow)
        async with app.router.lifespan_context(app):
            before = authority(app.state.engine)
            historical = complete(app)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN, auth=private,
                                         headers={"Origin": ORIGIN}) as client:
                responses = await asyncio.gather(*(upload(client) for _ in range(7)))
                assert sorted(r.status_code for r in responses) == [202] * 2 + [429] * 5
                await asyncio.wait_for(slow.entered.wait(), 3)
                assert slow.calls == 1 and len(app.state.runs.tasks) == 2
                assert len(list((tmp_path / "docs").glob("*.pdf"))) == 2
                listing = (await client.get("/api/runs")).json()
                assert sorted(r["execution_state"] for r in listing) == ["COMPLETED", "QUEUED", "RUNNING"]
                url = f"/api/runs/{historical}/po-confirmations"
                attempts = await asyncio.gather(client.post(url, json=body()), client.post(url, json=body()))
                assert sorted(r.status_code for r in attempts) == [201, 409]
                slow.release.set()
                await app.state.runs.idle()
                assert app.state.runs.admitted == 0 and slow.calls == 2
                assert authority(app.state.engine) == before

    asyncio.run(scenario())


def test_exhausted_admission_never_consumes_request_body(tmp_path, private, monkeypatch):
    import httpx

    monkeypatch.setenv("AP_COMPASS_UPLOADS_ENABLED", "true")
    monkeypatch.setenv("AP_COMPASS_UPLOAD_CAPACITY", "1")

    async def scenario():
        started, finish = asyncio.Event(), asyncio.Event()
        app = create_app(tmp_path / "db", document_dir=tmp_path / "docs", extractor=Extractor())

        async def first():
            started.set()
            await finish.wait()
            yield b"invalid multipart content"

        async def excess():
            pytest.fail("Rejected upload consumed its request body")
            yield b""

        headers = {"Origin": ORIGIN, "Content-Type": "multipart/form-data; boundary=invoice"}
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN, auth=private) as client:
                pending = asyncio.create_task(client.post("/api/runs", headers=headers, content=first()))
                try:
                    await asyncio.wait_for(started.wait(), 3)
                    rejected = await client.post("/api/runs", headers=headers, content=excess())
                    assert rejected.status_code == 429
                    assert (await client.get("/api/runs")).json() == []
                    assert list((tmp_path / "docs").iterdir()) == []
                finally:
                    finish.set()
                    result = await pending
                assert result.status_code == 400 and app.state.runs.admitted == 0

    asyncio.run(scenario())


def test_failed_creation_rolls_back_rows_and_discards_only_new_document(tmp_path):
    app = create_app(tmp_path / "db", document_dir=tmp_path / "docs", extractor=Extractor())
    raw = (ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes()
    upload_data = {"file": ("file.pdf", raw, "application/pdf")}
    with TestClient(app) as client:
        first = client.post("/api/runs", files=upload_data)
        assert first.status_code == 202
        client.portal.call(app.state.runs.idle)
        old = client.get("/api/runs").json()
        saved = next((tmp_path / "docs").glob("*.pdf"))

        def fail_stages(conn, cursor, statement, *args):
            if statement.startswith("INSERT INTO run_stage"):
                raise RuntimeError("Private injected storage failure detail")

        event.listen(app.state.engine, "before_cursor_execute", fail_stages)
        failed = client.post("/api/runs", files=upload_data)
        client.portal.call(app.state.runs.idle)
        assert failed.status_code == 503 and "injected" not in failed.text
        assert list((tmp_path / "docs").iterdir()) == [saved] and saved.read_bytes() == raw
        assert client.get("/api/runs").json() == old and app.state.runs.admitted == 0


@pytest.mark.parametrize("status", [503, 504, "transport"])
def test_gateway_and_transport_failure_retry_twice_then_persist_technical_state(tmp_path, status):
    calls = []

    async def generate(**options):
        calls.append(options["model"])
        if status == "transport":
            raise httpx2.ConnectError("Controlled connection failure")
        raise errors.ServerError(status, {"error": {"message": "Controlled gateway detail"}}, None)

    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    provider = GeminiProvider(client, "gemini-3.5-flash-lite")

    async def controlled(raw):
        return await extract_pdf(raw, provider)

    db, docs = tmp_path / "db", tmp_path / "docs"
    app = create_app(db, document_dir=docs, extractor=controlled)
    with TestClient(app) as http:
        old = "/api/runs/" + complete(app)
        baseline = http.get(old).json()
        response = http.post("/api/runs", files={"file": ("invoice.pdf", (ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes(), "application/pdf")})
        assert response.status_code == 202
        app_url = "/api/runs/" + response.json()["run_id"]
        http.portal.call(app.state.runs.idle)
        snapshot = http.get(app_url).json()
        assert (snapshot["execution_state"], snapshot["execution_error_code"], snapshot["decision"]) == (
            "PROCESSING_FAILED", "PROVIDER_UNAVAILABLE", None)
        assert snapshot["usage"]["model_calls"] == 2
        assert [s["state"] for s in snapshot["stages"]] == ["PASSED", "FAILED", "SKIPPED", "SKIPPED", "SKIPPED"]
    with TestClient(create_app(db, document_dir=docs, extractor=controlled)) as http:
        assert http.get(app_url).json() == snapshot and http.get(old).json() == baseline
        assert http.get(app_url + "/document").status_code == 200
    assert calls == ["gemini-3.5-flash-lite"] * 2


def test_second_application_cannot_reconcile_owned_database(tmp_path):
    db, docs = tmp_path / "db", tmp_path / "docs"
    with TestClient(create_app(db, document_dir=docs)) as client:
        with pytest.raises(RuntimeError, match="database already in use"):
            with TestClient(create_app(db, document_dir=docs)):
                pytest.fail("Second app unexpectedly started")
        assert client.get("/api/health").status_code == 200
    with TestClient(create_app(db, document_dir=docs)) as client:
        assert client.get("/api/health").status_code == 200
