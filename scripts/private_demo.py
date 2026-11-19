"""Opt-in, loopback-only controlled demo setup. Excluded from the runtime image."""
import argparse
import asyncio
from pathlib import Path
import sys
from time import monotonic
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation"))
from benchmark_inputs import digest, read_json, safe_path
from benchmark_source import ControlledProvider, claims_for
from app.api.private_access import OperatingSettings
from app.documents.pipeline import extract_pdf
from app.documents.types import ExtractionError
from app.main import create_app

DEMO_CASES = ("HAPPY_CLEAN", "OVERBILLED_PARTIAL", "MISSING_PO_VALID", "PRICE_3PCT")


class DemoProvider(ControlledProvider):
    model_id = "TEST_ONLY-controlled-demo"


def demo_inputs(names=DEMO_CASES):
    cases = {case["case_id"]: case for case in read_json(ROOT / "data/golden_dataset_v1.json")["cases"]
             if case["case_id"] in names}
    for name in names:
        case = cases[name]
        asset = case["pdf"]
        path = safe_path(ROOT, asset["path"])
        raw = path.read_bytes()
        if digest(raw) != asset["sha256"]:
            raise RuntimeError(f"Fixture hash mismatch for {name}")
        yield case, path.name, raw


def require_loopback(origin):
    if not origin or urlsplit(origin).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("The controlled demo harness requires a private loopback origin")


def create_demo():
    require_loopback(OperatingSettings.from_environment().origin)
    replies = {digest(raw): DemoProvider(case, claims_for(case, raw, {}))
               for case, _, raw in demo_inputs((*DEMO_CASES, "HAPPY_PARTIAL"))}

    async def controlled(raw):
        provider = replies.get(digest(raw))
        if provider is None:
            raise ExtractionError("UNSUPPORTED_PDF")
        return await extract_pdf(raw, provider)

    application = create_app(extractor=controlled)

    @application.middleware("http")
    async def identify_harness(request, call_next):
        response = await call_next(request)
        if request.url.path == "/api/health" and response.status_code == 200:
            response.headers["X-AP-Compass-Demo"] = DemoProvider.model_id
        return response

    return application


async def prepare(env_file):
    import httpx
    from dotenv import dotenv_values

    values = dotenv_values(env_file, interpolate=False)
    origin = values.get("AP_COMPASS_PRIVATE_ORIGIN")
    require_loopback(origin)
    credentials = (values["AP_COMPASS_PRIVATE_USERNAME"], values["AP_COMPASS_PRIVATE_PASSWORD"])
    async with httpx.AsyncClient(base_url=origin, auth=credentials, headers={"Origin": origin},
                                 trust_env=False, timeout=10) as client:
        health = (await client.get("/api/health")).raise_for_status()
        if health.headers.get("X-AP-Compass-Demo") != DemoProvider.model_id:
            raise RuntimeError("Prepare requires the controlled harness; no files were submitted")
        existing = (await client.get("/api/runs")).raise_for_status().json()
        if existing:
            raise RuntimeError("Use a fresh disposable demo store")
        for case, filename, raw in demo_inputs():
            accepted = (await client.post("/api/runs", files={"file": (filename, raw, "application/pdf")})).raise_for_status()
            run_id = accepted.json()["run_id"]
            deadline = monotonic() + 30
            while monotonic() < deadline:
                run = (await client.get(f"/api/runs/{run_id}")).raise_for_status().json()
                state = run["execution_state"]
                if state not in {"QUEUED", "RUNNING"}:
                    break
                await asyncio.sleep(0.2)
            else:
                raise RuntimeError("Timed out waiting for the controlled demo run")
            outcome = (run["decision"] or {}).get("outcome")
            if state != "COMPLETED" or outcome != case["expected_decision"] or run["model_id"] != DemoProvider.model_id:
                raise RuntimeError(f"{case['case_id']}: unexpected controlled result {state} / {outcome}")
            print(f"{case['case_id']} {state} {outcome} {run_id}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(prepare(args.env_file))
