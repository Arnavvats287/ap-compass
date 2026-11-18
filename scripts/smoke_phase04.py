"""Explicit, bounded manual live check through POST /api/runs, never a unit test.

Run once after offline tests pass. Synthetic fixtures only; no raw provider replies,
PDF text, quotes, bank values or credentials are written to the report.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import httpx
from dotenv import load_dotenv
from sqlalchemy import select
from app.ai import gemini
from app.db.models import Vendor, PurchaseOrder, POLine, PriorBilledInvoice
from app.main import create_app


def authority_hash(engine):
    with engine.connect() as connection:
        rows = {model.__tablename__: [dict(row._mapping) for row in connection.execute(
            select(model.__table__).order_by(model.id))]
            for model in (Vendor, PurchaseOrder, POLine, PriorBilledInvoice)}
    return sha256(json.dumps(rows, default=str, sort_keys=True).encode()).hexdigest()


async def main(output):
    load_dotenv(ROOT / ".env", override=False)
    settings = gemini.GeminiSettings.from_environment()
    if settings.escalation_enabled or settings.primary_model != "gemini-3.5-flash-lite":
        raise SystemExit("Use primary Flash-Lite with escalation disabled")
    directory = ROOT / "runtime" / ("phase04-smoke-" + uuid4().hex)
    directory.mkdir(parents=True)
    requests = []
    original = gemini.make_client

    def instrument(settings):
        client = original(settings)
        generate = client.aio.models.generate_content
        async def forbidden_metadata(**kwargs):
            raise AssertionError("No runtime metadata lookup allowed")
        async def tracked(**kwargs):
            if kwargs["model"] != "gemini-3.5-flash-lite" or len(requests) >= 3:
                raise AssertionError("Live smoke request bound exceeded")
            requests.append({"kind": "generation", "model": kwargs["model"]})
            return await generate(**kwargs)
        client.aio.models.get = forbidden_metadata
        client.aio.models.generate_content = tracked
        return client

    gemini.make_client = instrument
    cases = {case["id"]: case for case in json.loads((ROOT/"data/fixture_manifest.json").read_text())["fixture_cases"]}
    snapshots = {}
    results = []
    app = create_app(directory/"runs.db", document_dir=directory/"documents")
    try:
        async with app.router.lifespan_context(app):
            before = authority_hash(app.state.engine)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://phase04") as client:
                health = (await client.get("/api/health")).json()
                for name in ("HAPPY_CLEAN", "OVERBILLED_PARTIAL", "SCAN_CONFLICT"):
                    raw = (ROOT/"tests/fixtures"/(name+".pdf")).read_bytes()
                    created = await client.post("/api/runs", files={"file": (name+".pdf", raw, "application/pdf")})
                    assert created.status_code == 202
                    run_id = created.json()["run_id"]
                    await app.state.runs.idle()
                    snapshot = (await client.get("/api/runs/"+run_id)).json()
                    snapshots[run_id] = (snapshot, sha256(raw).hexdigest())
                    invoice = snapshot["extracted_invoice"] or {}
                    expected = {"vendor_name_raw": cases[name]["vendor_name"], "invoice_number": cases[name]["invoice_number"],
                                "invoice_date": cases[name]["invoice_date"], "po_reference": cases[name]["po_reference"],
                                "currency": cases[name]["currency"], "net": cases[name]["net"],
                                "tax": cases[name]["tax"], "total": cases[name]["gross"]}
                    fields = {key: {"expected": value, "extracted": invoice.get(key), "match": invoice.get(key) == value}
                              for key, value in expected.items()}
                    results.append({"filename": name+".pdf", "run_id": run_id,
                        "execution_state": snapshot["execution_state"], "execution_error_code": snapshot["execution_error_code"],
                        "model_id": snapshot["model_id"], "route": snapshot["source_route"], "critical_header_fields": fields,
                        "lines": invoice.get("lines"),
                        "evidence_states": {ref["field"]: ref["evidence_state"] for ref in invoice.get("evidence", [])},
                        "expected_outcome": cases[name]["expected_decision"],
                        "decision": snapshot["decision"], "candidates": [c["po"]["id"] for c in snapshot["candidates"]],
                        "timings": snapshot["timings"], "usage": snapshot["usage"], "stages": snapshot["stages"]})
                after = authority_hash(app.state.engine)
                dashboard = (await client.get("/api/dashboard")).json()
        calls_before_reload = len(requests)
        app = create_app(directory/"runs.db", document_dir=directory/"documents")
        reloads = []
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://phase04") as client:
                for identifier, (snapshot, pdf_hash) in snapshots.items():
                    detail = (await client.get("/api/runs/"+identifier)).json()
                    document = await client.get("/api/runs/"+identifier+"/document")
                    reloads.append({"run_id": identifier, "identical_snapshot": detail == snapshot,
                                    "identical_document": sha256(document.content).hexdigest() == pdf_hash})
        report = {"live": True, "observed_at": datetime.now(timezone.utc).isoformat(),
                  "transport": "real FastAPI ASGI endpoints and lifespan, in-process HTTP client",
                  "health": health, "requests": requests, "results": results, "dashboard": dashboard,
                  "authority_before_sha256": before, "authority_after_sha256": after, "ledger_unchanged": before == after,
                  "reloads": reloads, "model_calls_on_reload": len(requests)-calls_before_reload}
        # Decision evidence_refs contain source quotes; keep reports to codes/owners/actions only.
        for result in results:
            if result["decision"]:
                decision = result["decision"]
                result["decision"] = {"outcome": decision["outcome"], "primary_reason_code": decision["primary_reason_code"],
                    "owner": decision["owner"], "next_action": decision["next_action"],
                    "reason_codes": [f["code"] for f in decision["findings"]]}
        output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({"results": [{"filename": r["filename"], "state": r["execution_state"],
            "outcome": r["decision"]["outcome"] if r["decision"] else None, "usage": r["usage"]} for r in results],
            "calls": len(requests), "ledger_unchanged": before == after, "reloads": reloads}, indent=2))
    finally:
        gemini.make_client = original


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--output", type=Path, default=ROOT/"tmp/phase04-live-results.json")
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(main(arguments.output))
