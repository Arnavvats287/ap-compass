"""Phase 6B.2A benign controls. Provider claims are synthetic test data."""
import asyncio
import json

import httpx
import pymupdf
import pytest

from app.documents.pipeline import extract_pdf
from app.main import create_app
from test_document_engine import FakeProvider, ROOT, wire
from test_orchestration_api import authority, upload


def control(kind):
    raw = (ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes()
    if kind == "visible":
        return raw
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        if kind == "repeated_summary":
            lines = [line for line in pdf[0].get_text().splitlines()
                     if line.startswith(("Net subtotal:", "Tax (", "Invoice total:"))]
            assert len(lines) == 3
            page = pdf.new_page()
            page.insert_text((48, 80), "Synthetic invoice continuation")
            page.insert_text((48, 110), "\n".join(lines))
        else:
            # A solid-color decorative swatch has no instruction or financial content.
            icon = pymupdf.Pixmap(pymupdf.csRGB, 12, 12, bytes([34, 86, 70] * 144), False)
            pdf[0].insert_image(pymupdf.Rect(510, 100, 534, 124), pixmap=icon)
        return pdf.tobytes(no_new_id=True)


@pytest.mark.parametrize("kind, pages", [("visible", 1), ("repeated_summary", 2), ("decorative_image", 1)])
def test_benign_source_remains_ready(kind, pages, tmp_path):
    async def scenario():
        raw = control(kind)
        assert raw == control(kind)
        provider = FakeProvider([json.dumps(wire())], model="TEST_ONLY-benign-control")

        async def extract(source):
            return await extract_pdf(source, provider, max_attempts=1)

        app = create_app(tmp_path / "runs.db", document_dir=tmp_path / "documents", extractor=extract)
        async with app.router.lifespan_context(app):
            before = authority(app.state.engine)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                current_policy = (await client.get("/api/policy")).json()
                uploaded = await upload(client, data=raw)
                assert uploaded.status_code == 202
                await app.state.runs.idle()
                response = await client.get("/api/runs/" + uploaded.json()["run_id"])
                assert response.status_code == 200
                run = response.json()
                assert run["execution_state"] == "COMPLETED"
                assert run["decision"]["outcome"] == "READY_FOR_AP"
                assert run["model_id"] == "TEST_ONLY-benign-control"
                assert run["extracted_invoice"]["bank_instructions"] is None
                assert all(ref["evidence_state"] == "NATIVE_VERIFIED"
                           for ref in run["extracted_invoice"]["evidence"])
                assert run["policy_snapshot"] == current_policy == (await client.get("/api/policy")).json()
                assert authority(app.state.engine) == before
            assert len(provider.calls) == 1
            inspection = provider.calls[0]
            assert inspection.route == "native_text" and len(inspection.pages) == pages
            assert all(page.native_text for page in inspection.pages)
            with pymupdf.open(stream=raw, filetype="pdf") as pdf:
                assert not pdf[0].get_pixmap().is_unicolor
                assert len(pdf[0].get_image_info()) == (1 if kind == "decorative_image" else 0)

    asyncio.run(scenario())
