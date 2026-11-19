"""Deep-link reload support, preserving API/asset request boundaries."""
from fastapi.testclient import TestClient
import pytest

import app.main as main


@pytest.fixture
def client(tmp_path, monkeypatch):
    static = tmp_path / "frontend/dist"
    static.mkdir(parents=True)
    (static/"index.html").write_text("<!doctype html><title>AP Compass test entry</title>")
    (static/"assets").mkdir()
    (static/"assets/app.js").write_text("/* test asset */")
    monkeypatch.setattr(main, "ROOT", tmp_path)
    with TestClient(main.create_app(tmp_path/"db", document_dir=tmp_path/"documents")) as value:
        yield value


@pytest.mark.parametrize("path", ["/", "/runs", "/runs/example-id"])
def test_frontend_routes_load_entry_on_direct_navigation(client, path):
    response = client.get(path)
    assert response.status_code == 200 and "AP Compass test entry" in response.text


@pytest.mark.parametrize("path", ["/api/unknown", "/api/runs/missing", "/assets/missing.js", "/.env", "/unknown"])
def test_frontend_fallback_does_not_swallow_api_asset_or_unknown_paths(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert "AP Compass test entry" not in response.text


def test_assets_and_health_remain_real(client):
    assert client.get("/assets/app.js").text == "/* test asset */"
    assert client.get("/api/health").json()["database"] == "ok"
