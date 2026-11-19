"""AP Compass evaluation v1. No changes to production decisions or evidence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
from jsonschema import Draft202012Validator
from starlette.testclient import TestClient

from app.ai.gemini import GeminiProvider, GeminiSettings, make_client
from app.contracts import DecisionV1, EvidenceRefV1, PolicyV1, PriorBilledInvoiceV1, PurchaseOrderV1, RunSnapshotV1, VendorV1
from app.documents.pipeline import extract_pdf
from app.documents.schema import parse_response
from app.domain import build_context, evaluate
from app.domain.human_resolution import POConfirmation, evaluate_with_confirmed_po
from app.main import create_app
from app.orchestration.reviews import fingerprint
from benchmark_inputs import digest, read_json, registered_cases, safe_path, wire_facts
from benchmark_score import attach_decision, classification, field_rows, metrics
from benchmark_source import ControlledProvider, claims_for

EVAL = ROOT / "evaluation"
SEED_PATH = ROOT / "data/seed_manifest.json"
GOLDEN_PATH = ROOT / "data/golden_dataset_v1.json"
PRIMARY = "gemini-3.5-flash-lite"
LIVE_SELECTION = ("H01", "H03", "H04", "H05")
LIVE_BUDGET = 4


def json_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def authority():
    s = read_json(SEED_PATH)
    return tuple(tuple(contract.model_validate(row) for row in sorted(s[key], key=lambda row: row["id"]))
                 for key, contract in (("vendors", VendorV1), ("purchase_orders", PurchaseOrderV1),
                                       ("prior_billed_invoices", PriorBilledInvoiceV1)))


def authority_hash(records):
    return fingerprint([[row.model_dump(mode="json") for row in group] for group in records])


def start_row(case, target, track="submission"):
    row = dict(case_id=case["case_id"], track=track, attempt=1, status="executed", execution_state=None,
               decision=None, target_decision=target["expected_decision"], finding_codes=[], fields=[],
               model_calls=None, latency_ms=None, required_findings=target.get("required_findings", []))
    if case["pdf"]:
        row["pdf_sha256"] = case["pdf"]["sha256"]
    if target.get("expected_owner"):
        row["owner_match"] = False
    if target.get("expected_next_action"):
        row["next_action_match"] = False
    return row


def trusted_facts(case, policy):
    wire = wire_facts(case)
    invoice, _ = parse_response(wire.model_dump_json())
    refs = []
    if case["expected_route"] != "image_only":
        from app.documents.evidence import values
        for field, value in values(invoice).items():
            if value is not None:
                refs.append(EvidenceRefV1(field=field, raw_value=str(value), normalized_value=str(value),
                                          quote="Layer A typed-fact assumption", page=1,
                                          route="native_text", evidence_state="NATIVE_VERIFIED"))
    invoice = invoice.model_copy(update={"evidence": tuple(refs)})
    context = build_context(invoice, *authority())
    row = start_row(case, case)
    attach_decision(row, evaluate(context, policy), case)
    row["model_calls"] = 0
    yield row
    if target := case.get("human_action"):
        action = start_row(case, target, "po_confirmation")
        attach_decision(action, evaluate_with_confirmed_po(context, policy,
                        POConfirmation(target["po_id"], target["rationale"])), target)
        yield action
    if target := case.get("policy_variant"):
        variant = start_row(case, target, "policy_variant")
        attach_decision(variant, evaluate(context, policy.model_copy(update={
            "price_tolerance_pct": PolicyV1(price_tolerance_pct=target["price_tolerance_pct"]).price_tolerance_pct})), target)
        yield variant


class GenerationBudget:
    def __init__(self, settings):
        self.settings = settings
        self.calls = 0
        self.attempts = []

    async def extract(self, raw):
        remaining = LIVE_BUDGET - self.calls
        if remaining <= 0:
            raise RuntimeError("Generation budget exhausted")
        client = make_client(self.settings)
        primary = GeminiProvider(client, self.settings.primary_model)
        budget = self

        class MeteredProvider:
            model_id = primary.model_id

            async def generate(self, document, timeout_seconds):
                if budget.calls >= LIVE_BUDGET:
                    raise RuntimeError("Generation budget exhausted")
                budget.calls += 1
                return await primary.generate(document, timeout_seconds)

        try:
            result = await extract_pdf(raw, MeteredProvider(), max_attempts=min(2, remaining))
            self.attempts.extend(result.metadata.attempts)
            return result
        except Exception as error:
            self.attempts.extend(getattr(error, "attempts", ()))
            raise
        finally:
            await client.aio.aclose()
            client.close()


def pdf_attempt(case, raw, claims, budget, policy):
    fake = None if budget else ControlledProvider(case, claims)

    async def controlled(data):
        return await extract_pdf(data, fake)

    before_calls = budget.calls if budget else 0
    before_attempts = len(budget.attempts) if budget else 0
    with TemporaryDirectory(prefix="ap-benchmark-") as temp:
        root = Path(temp)
        app = create_app(root / "isolated.sqlite", document_dir=root / "documents",
                         extractor=budget.extract if budget else controlled)
        with TestClient(app) as client:
            repository = app.state.runs.repository
            seeded_hash = authority_hash(repository.authority())
            if seeded_hash != authority_hash(authority()) or app.state.runs.current_policy != policy:
                raise RuntimeError("Default authority or policy differs from frozen inputs")
            began = perf_counter()
            upload = client.post("/api/runs", files={"file": ("invoice.pdf", raw, "application/pdf")})
            row = start_row(case, case)
            if upload.status_code != 202:
                if upload.status_code >= 500:
                    raise RuntimeError(f"Unexpected upload HTTP {upload.status_code}")
                row.update(execution_state="PROCESSING_FAILED", error_code=f"UPLOAD_HTTP_{upload.status_code}",
                           model_calls=0, latency_ms=round((perf_counter() - began) * 1000, 3))
                yield row
                return
            run_id = upload.json()["run_id"]
            client.portal.call(app.state.runs.idle)
            url = f"/api/runs/{run_id}"
            state = client.get(url).json()
            row["latency_ms"] = round((perf_counter() - began) * 1000, 3)
            snapshot = RunSnapshotV1.model_validate(state)
            if snapshot.execution_state not in {"COMPLETED", "PROCESSING_FAILED", "INTERRUPTED"}:
                raise RuntimeError("The run did not reach a terminal state")
            persisted = repository.load(run_id)
            document = client.get(url + "/document")
            if persisted != snapshot or document.status_code != 200 or digest(document.content) != case["pdf"]["sha256"]:
                raise RuntimeError("Persisted snapshot or source document mismatch")
            row.update(execution_state=snapshot.execution_state, run_reference=run_id,
                       model_calls=budget.calls - before_calls if budget else 0,
                       input_tokens=snapshot.usage.input_tokens if snapshot.usage else None,
                       output_tokens=snapshot.usage.output_tokens if snapshot.usage else None,
                       error_code=snapshot.execution_error_code,
                       route=snapshot.source_route, model_id=snapshot.model_id or (PRIMARY if budget else fake.model_id))
            if budget:
                attempts = budget.attempts[before_attempts:]
                row["notes"] = ", ".join(f"generation {a.number}: {a.error_code or 'valid response'}"
                                         + (f" (HTTP {a.provider_http_status})" if a.provider_http_status else "")
                                         for a in attempts)
            else:
                row["controlled_calls"] = fake.calls
            if snapshot.extracted_invoice:
                row["fields"] = field_rows(case, snapshot.extracted_invoice, claims)
            if snapshot.decision:
                attach_decision(row, snapshot.decision, case)
            # Journal the submission before running any separate workflow track.
            if authority_hash(repository.authority()) != seeded_hash:
                raise RuntimeError("Authoritative records changed")
            yield row
            if budget:
                return
            for key, track in (("human_action", "po_confirmation"), ("policy_variant", "policy_variant")):
                if not (target := case.get(key)):
                    continue
                action = start_row(case, target, track)
                action["model_calls"] = 0
                if track == "po_confirmation":
                    result = client.post(url + "/po-confirmations", json={
                        "po_id": target["po_id"], "rationale": target["rationale"],
                        "reviewer_label": "Benchmark demo reviewer", "client_action_id": str(uuid4())})
                    if result.status_code == 201:
                        history = client.get(url + "/review-history").json()
                        if history["actions"] != [result.json()] or result.json()["authority_fingerprint"] != seeded_hash:
                            raise RuntimeError("The stored confirmation does not match the observed action")
                        attach_decision(action, DecisionV1.model_validate(result.json()["reassessment"]), target)
                else:
                    result = client.post(url + "/policy-preview", json={"price_tolerance_pct": target["price_tolerance_pct"]})
                    if result.status_code == 200:
                        attach_decision(action, DecisionV1.model_validate(result.json()["preview_decision"]), target)
                action["notes"] = f"HTTP {result.status_code}"
                if action["decision"] is None:
                    action["status"] = "inconclusive"
                if client.get(url).json() != state or authority_hash(repository.authority()) != seeded_hash:
                    raise RuntimeError("Workflow changed source assessment or authority")
                yield action


def execute(args):
    manifest = read_json(args.manifest)
    annotations = read_json(args.annotations) if args.annotations else {}
    cases = registered_cases(manifest, args.asset_root, split=args.split)
    golden = read_json(GOLDEN_PATH)
    for name, expected in golden["source_hashes"].items():
        if digest(safe_path(ROOT, name).read_bytes().replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Frozen authority or oracle reference changed")
    policy = PolicyV1(**golden["policy"])
    code = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--", "backend/app", "frontend", "data", "tests/fixtures"):
        raise ValueError("Benchmark requires clean production, seed and frozen inputs")
    validator = Draft202012Validator(read_json(EVAL / "result_v1.schema.json"))
    Draft202012Validator.check_schema(validator.schema)
    raw_files, claims = {}, {}
    if args.layer != "A":
        for case_id, case in cases.items():
            if case["pdf"]:
                raw = safe_path(args.asset_root, case["pdf"]["path"]).read_bytes()
                if digest(raw) != case["pdf"]["sha256"]:
                    raise ValueError("Asset changed after registration")
                raw_files[case_id] = raw
                claims[case_id] = claims_for(case, raw, annotations.get(case_id, {}))
    budget = None
    live_reason = ""
    if args.layer == "C":
        if args.split != "heldout" or not args.allow_live or any(case_id not in cases for case_id in LIVE_SELECTION):
            raise ValueError("Layer C requires explicit approval and the preselected independent cases")
        load_dotenv(ROOT / ".env", override=False)
        os.environ["GEMINI_ESCALATION_ENABLED"] = "false"
        try:
            settings = GeminiSettings.from_environment()
        except Exception:
            live_reason = "No usable configured credential or primary provider configuration"
        else:
            if settings.primary_model != PRIMARY:
                live_reason = "Configured primary is not the verified benchmark model"
            else:
                budget = GenerationBudget(settings)
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    provenance = dict(started_utc=datetime.now(timezone.utc).isoformat(), authority_fingerprint=authority_hash(authority()),
                      seed_sha256=golden["source_hashes"]["data/seed_manifest.json"], policy=policy.model_dump(mode="json"),
                      registry_sha256=digest(args.manifest.read_bytes()),
                      annotation_sha256=digest(args.annotations.read_bytes()) if args.annotations else None,
                      latency_scope="ASGI POST start through terminal persisted GET response" if args.layer != "A" else None,
                      requested_primary=PRIMARY if args.layer == "C" else None,
                      live_selection=list(LIVE_SELECTION) if args.layer == "C" else [],
                      live_budget=LIVE_BUDGET if args.layer == "C" else 0)
    report = dict(dataset_version=manifest["version"], dataset_sha256=args.oracle_sha or provenance["registry_sha256"],
                  code_commit=code, layer=args.layer, split=args.split, attempts=[], metrics={}, provenance=provenance)
    json_new(output / "run-start.json", {key: value for key, value in report.items() if key not in {"attempts", "metrics"}})
    ordered = list(cases)
    if args.layer == "C":
        ordered = [*LIVE_SELECTION, *(key for key in cases if key not in LIVE_SELECTION)]
    for case_id in ordered:
        case = cases[case_id]
        reason = None
        status = "ineligible"
        if args.layer not in case["eligibility"]:
            reason = "No frozen PDF"
        elif args.layer == "C" and case_id not in LIVE_SELECTION:
            reason = "Offline-only for this capped sample"
        elif args.layer == "C" and (not budget or budget.calls >= LIVE_BUDGET):
            status = "not_executed"
            reason = live_reason or "Generation budget consumed by earlier attempts"
        if reason:
            rows = [dict(start_row(case, case), status=status, notes=reason)]
        elif args.layer == "A":
            rows = trusted_facts(case, policy)
        else:
            rows = pdf_attempt(case, raw_files[case_id], claims[case_id], budget, policy)
        for row in rows:
            row["classification"] = classification(row)
            report["attempts"].append(row)
            json_new(output / f"{case_id}-{row['track']}-001.json", row)
            print(case_id, row["track"], row["classification"], flush=True)
    provenance["finished_utc"] = datetime.now(timezone.utc).isoformat()
    provenance["actual_generation_attempts"] = budget.calls if budget else 0
    report["metrics"] = metrics(report["attempts"], args.layer)
    validator.validate(report)
    json_new(output / "report.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layer", required=True, choices=("A", "B", "C"))
    parser.add_argument("--split", default="development", choices=("development", "heldout"))
    parser.add_argument("--manifest", type=Path, default=GOLDEN_PATH)
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--oracle-sha", help="Raw independent oracle SHA-256 when using a normalized registry")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-live", action="store_true")
    args = parser.parse_args()
    if args.split == "development" and not args.annotations:
        args.annotations = EVAL / "development_scan_source.json"
    execute(args)
