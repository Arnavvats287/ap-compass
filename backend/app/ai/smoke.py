"""Explicit live fixture benchmark; never runs during offline tests or server import."""
import argparse
import asyncio
from dataclasses import asdict
from decimal import Decimal
import json
from pathlib import Path

from dotenv import load_dotenv

from app.documents.evidence import values
from app.documents.pipeline import extract_pdf
from app.documents.types import ExtractionError
from .gemini import GeminiProvider, GeminiSettings, make_client, verify_model

ROOT = Path(__file__).resolve().parents[3]


def comparison(case, invoice):
    expected = {"vendor_name_raw": case["vendor_name"], "invoice_number": case["invoice_number"],
                "invoice_date": case["invoice_date"], "po_reference": case["po_reference"],
                "currency": case["currency"], "net": case["net"], "tax": case["tax"], "total": case["gross"]}
    for i, line in enumerate(case["lines"]):
        for key in ("description", "item_code", "qty", "unit_price_net"):
            expected[f"lines[{i}].{key}"] = line[key]
        expected[f"lines[{i}].net"] = None if case["id"] == "SCAN_CONFLICT" else str(Decimal(line["qty"]) * Decimal(line["unit_price_net"]))
    actual = values(invoice)
    evidence = {ref.field: ref.evidence_state for ref in invoice.evidence}
    numeric = {"net", "tax", "total", "qty", "unit_price_net"}
    fields = {}
    for name, wanted in expected.items():
        found = actual.get(name)
        if found is None or wanted is None:
            equal = found is None and wanted is None
        elif name.split(".")[-1] in numeric:
            equal = Decimal(str(found)) == Decimal(wanted)
        else:
            equal = str(found) == wanted
        fields[name] = {"expected": wanted, "extracted": None if found is None else str(found),
                        "match": equal, "evidence": evidence.get(name, "MISSING")}
    return fields


async def run(benchmark=False, only_model=None, only_case=None):
    load_dotenv(ROOT / ".env", override=False)
    settings = GeminiSettings.from_environment()
    client = make_client(settings)
    results = {"live": True, "models": [], "documents": []}
    try:
        for model in dict.fromkeys((settings.primary_model, settings.escalation_model)):
            results["models"].append(await verify_model(client, model))
        cases = {case["id"]: case for case in json.loads((ROOT / "data/fixture_manifest.json").read_text())["fixture_cases"]}
        jobs = [(case_id, model) for model in (settings.primary_model, settings.escalation_model)
                for case_id in ("HAPPY_CLEAN", "SCAN_CONFLICT")] if benchmark else [
                    ("HAPPY_CLEAN", settings.primary_model), ("OVERBILLED_PARTIAL", settings.primary_model),
                    ("SCAN_CONFLICT", settings.scan_model or settings.primary_model)]
        if only_model:
            if only_model not in (settings.primary_model, settings.escalation_model):
                raise ExtractionError("CONFIGURATION")
            jobs = [job for job in jobs if job[1] == only_model]
        if only_case:
            jobs = [job for job in jobs if job[0] == only_case]
        for case_id, model in jobs:
            case = cases[case_id]
            item = {"fixture": case_id, "requested_model": model}
            try:
                # Benchmark isolation: one inference per model/document, no silent retry/escalation.
                result = await extract_pdf((ROOT / "tests/fixtures" / case["filename"]).read_bytes(),
                                           GeminiProvider(client, model, thinking_level=settings.escalation_thinking_level if model == settings.escalation_model else None),
                                           max_attempts=1)
                fields = comparison(case, result.invoice)
                item.update(metadata=asdict(result.metadata), fields=fields,
                            exact_matches=sum(field["match"] for field in fields.values()),
                            missing=[key for key, field in fields.items() if field["expected"] is not None and field["extracted"] is None],
                            incorrect=[key for key, field in fields.items() if not field["match"] and field["extracted"] is not None])
            except ExtractionError as error:
                item.update(error=error.code, model_calls=error.calls, elapsed_ms=error.elapsed_ms,
                            attempts=[asdict(attempt) for attempt in error.attempts])
            results["documents"].append(item)
            print(json.dumps({k: v for k, v in item.items() if k != "fields"}), flush=True)
            await asyncio.sleep(.5)
        return results
    finally:
        await client.aio.aclose()
        client.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--model", help="One of the two configured model IDs only")
    parser.add_argument("--case", choices=["HAPPY_CLEAN", "OVERBILLED_PARTIAL", "SCAN_CONFLICT"])
    options = parser.parse_args()
    try:
        result = asyncio.run(run(options.benchmark, options.model, options.case))
    except ExtractionError as error:
        print(json.dumps({"live": False, "error": error.code}))
        raise SystemExit(1) from None
    if options.report:
        # This explicit development command persists sanitized synthetic fixture comparisons only.
        options.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if any("error" in item for item in result["documents"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
