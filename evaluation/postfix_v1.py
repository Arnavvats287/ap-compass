"""Post-remediation comparison using the frozen v1 cases and scoring."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import os
from pathlib import Path, PurePosixPath
import re
from zipfile import ZipFile

import benchmark_v1 as v1
from benchmark_inputs import digest, read_json, registered_cases, relative_parts, safe_path
from benchmark_score import classification, metrics
from benchmark_source import claims_for
from import_heldout_v1 import EXPECTED, NAMES, ORACLE, check_truth
from app.documents.consistency import disputed_headers
from app.documents.evidence import LINE_FIELD, flat, layout_support, local_support, values
from app.documents.inspection import inspect_pdf
from app.documents.schema import SourceClaim
from app.documents.source_layout import rows_for, split_headers, table_rows, unique_quotes
from app.documents.types import ExtractionError

LABEL = "POST-REMEDIATION REGRESSION COMPARISON — NOT A NEW UNSEEN BASELINE"
BASE = "9c2e795a3090f340696e6aaf9be65cde45d3d33f"
ORDER = (("heldout", "H04"), ("development", "OVERBILLED_PARTIAL"), ("heldout", "H01"),
         ("heldout", "H05"), ("heldout", "H03"), ("heldout", "H06"))
BUDGET = 8
MAX_ATTEMPTS = 2  # Ordinary runtime extraction path.
ARCHIVE_HASH = "f3467c2ab7cdf687b1a646d4ae21668d6f88808b1c5ee4911c4dc1f2329880b7"
ORACLE_HASH = "30e8850f67dec06662d7fc1843ab0600e01ccebb4a4a704db8cbbbca2ae0ca73"
REGISTRY_HASH = "100534567bcecdacf2303fbe87b8db260fb6c9138aa693fc586b34c4540e5255"
ANNOTATIONS_HASH = "358c92130fc959d4e6372758dfaf7aa87e0ec48c04bfe64514f788c15de1e369"
GOLDEN_HASH = "b8397f5f6b58fcc8f46b264ebd589e111555497b32b80e14e9936f01d8fbb353"
HISTORY = {
    "development-a.json": "d88367a59def4dac27b2cf850ff4898b67bc3e701f5468b19726dbf4fb474e1c",
    "development-b.json": "0c6ca257a51a5300b49154976e2398b88053f0cd85f9268fcf6db7b4d449476f",
    "heldout-b.json": "323e77d7d49ab7b22c61f04dbd9a34abd669a1883b80ce5548b270fe8e50470d",
    "heldout-c.json": "da27bddd54ba6109373853b766e41aee4e36e2b7adb328bfe43c02cace28c8ac",
}
METRIC_VALUES = {"authorized_net", "prior_billed_net", "remaining_net", "requested_net", "excess_net",
                 "remaining_qty", "requested_qty", "excess_qty", "stated_total", "computed_total", "difference"}


def require_hash(path, expected):
    if digest(path.read_bytes()) != expected:
        raise ValueError(f"Frozen hash mismatch: {path.name}")


def input_integrity(archive, private):
    if not private.resolve().is_relative_to((v1.ROOT / "tmp").resolve()):
        raise ValueError("The held-out inputs must stay in private ignored tmp storage")
    require_hash(archive, ARCHIVE_HASH)
    original = private / "original"
    require_hash(original / ORACLE, ORACLE_HASH)
    require_hash(private / "registry.json", REGISTRY_HASH)
    require_hash(private / "annotations.json", ANNOTATIONS_HASH)
    with ZipFile(archive) as package:
        files = {}
        for entry in package.infolist():
            name = PurePosixPath(*relative_parts(entry.filename.rstrip("/"))).name
            if not entry.is_dir():
                if name not in EXPECTED or name in files:
                    raise ValueError("Unexpected or duplicate private member")
                files[name] = entry
        if set(files) != EXPECTED:
            raise ValueError("Missing private inputs")
        for name, entry in files.items():
            if package.read(entry) != safe_path(original, name).read_bytes():
                raise ValueError(f"Private member bytes differ: {name}")
    masters = v1.authority()
    for row in read_json(original / ORACLE):
        if NAMES[row["case_id"]] != row["filename"]:
            raise ValueError("Frozen invoice filename mismatch")
        require_hash(safe_path(original, row["filename"]), row["sha256"])
        check_truth(row["printed_document_truth"], row["financial_business_oracle"], *masters)


def load_inputs(private):
    paths = {"development": (v1.GOLDEN_PATH, v1.ROOT, v1.EVAL / "development_scan_source.json", GOLDEN_HASH),
             "heldout": (private / "registry.json", private / "original", private / "annotations.json", ORACLE_HASH)}
    data = {}
    for split, (manifest, root, annotations, oracle) in paths.items():
        registry = read_json(manifest)
        data[split] = dict(version=registry["version"], root=root, oracle=oracle, registry_sha256=digest(manifest.read_bytes()),
                           annotations=read_json(annotations), annotation_sha256=digest(annotations.read_bytes()),
                           cases=registered_cases(registry, root, split=split))
    return data


def native_candidates(raw):
    inspection = inspect_pdf(raw)
    pages = {page.number: page for page in inspection.pages}
    rows = {n: rows_for(page) for n, page in pages.items() if page.route == "native_text"}
    headers = {n: split_headers(layout) for n, layout in rows.items()}
    tables = {n: table_rows(layout) for n, layout in rows.items()}
    return pages, headers, tables, disputed_headers(inspection.pages, headers.values())


def diagnostic_reasons(row, ref, oracle_claim, invoice, context):
    field = row["field"]
    reasons = []
    relation = row["comparison"]
    if relation in {"wrong", "hallucinated"}:
        return ["incorrect_field_value" if relation == "wrong" else "unsupported_extra_value_or_line"]
    if relation == "correct_absence":
        return ["printed_source_absent"]
    if relation == "unlabelled":
        return ["outside_frozen_field_judgment"]
    if not ref or not ref.quote or not ref.raw_value:
        return ["missing_claim_quote_or_raw_value"] if relation != "missing" else ["missing_extracted_field_and_claim"]
    if ref.evidence_state == "NATIVE_VERIFIED":
        if row["evidence"] == "incorrect":
            return ["verified_by_application_but_v1_span_not_matched"]
        return ["application_verified"]
    pages, headers, tables, disputed = context
    page = pages.get(ref.page)
    if not page:
        return ["missing_or_incorrect_page_reference"]
    if page.route != "native_text":
        return ["unsupported_document_route", "unverified_optional_amount_withheld"] if relation == "missing" else ["unsupported_document_route"]
    if field in disputed or (field in headers[page.number] and len(headers[page.number][field]) != 1):
        reasons.append("ambiguous_competing_native_associations")
    if oracle_claim and flat(ref.quote) != flat(oracle_claim.quote):
        reasons.append("strict_v1_quote_span_differs")
    if ref.evidence_state == "MISSING" and flat(ref.quote) not in flat(page.native_text):
        reasons.append("quote_not_locatable_in_application_reading_order")
    claim = SourceClaim(field=field, page=ref.page, raw_value=ref.raw_value, quote=ref.quote)
    value = values(invoice).get(field)
    table = tables[page.number]
    if value is not None:
        local_headers = headers[page.number]
        if field in local_headers or (table and LINE_FIELD.fullmatch(field)):
            index = int(LINE_FIELD.fullmatch(field)[1]) if LINE_FIELD.fullmatch(field) else 0
            table = table if index < len(table) else ()
            supported = layout_support(invoice, field, value, claim, local_headers, table, unique_quotes(table))
        else:
            supported = local_support(invoice, field, value, page, claim)
        if not supported:
            reasons.append("row_or_cell_association_unsupported" if LINE_FIELD.fullmatch(field) else "field_label_value_association_unsupported")
    return reasons or ["local_candidate_present_but_application_withheld_verification"]


def diagnostics(snapshot, row, raw, claims, budget):
    result = {"case_id": row["case_id"], "fields": [], "findings": [], "trust_regressions": [], "integrity_flags": []}
    if decision := snapshot.decision:
        for f in decision.findings:
            entry = {"code": f.code, "severity": f.severity, "owner": f.owner, "next_action": f.next_action}
            numbers = {v.name: v.value for v in f.values if v.name in METRIC_VALUES and v.value is not None
                       and re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", v.value)}
            if numbers:
                entry["financial_values"] = numbers
            result["findings"].append(entry)
    if invoice := snapshot.extracted_invoice:
        context = native_candidates(raw)
        result["integrity_flags"] = list(invoice.document_integrity_flags or ())
        refs = {ref.field: ref for ref in invoice.evidence}
        for field_row in row["fields"]:
            name = field_row["field"]
            ref = refs.get(name)
            reasons = diagnostic_reasons(field_row, ref, claims.get(name), invoice, context)
            result["fields"].append({"field": name, "page": ref.page if ref else None,
                                     "route": ref.route if ref else None, "state": field_row.get("actual_evidence_state"),
                                     "comparison": field_row["comparison"], "diagnostic": reasons})
            if ref and ref.evidence_state == "NATIVE_VERIFIED" and (
                ref.route != "native_text" or field_row["comparison"] in {"wrong", "hallucinated", "missing"}
            ):
                result["trust_regressions"].append(name)
    if budget:
        count = row["model_calls"]
        result["generations"] = [{"attempt": a.number, "http_status": a.provider_http_status, "error_code": a.error_code,
                                  "elapsed_ms": a.elapsed_ms, "usage": asdict(a.usage)}
                                 for a in (budget.attempts[-count:] if count else ()) if a.inference_called]
    return result


def skip_reason(eligible, budget, live):
    if not eligible:
        return "ineligible", "Outside the preselected sample" if live else "No frozen PDF"
    if live and not budget:
        return "not_executed", "Configured primary credentials or model unavailable"
    if live and budget.limit - budget.calls < MAX_ATTEMPTS:
        return "not_executed", "Insufficient remaining budget for a full ordinary retry policy"
    return None


def run(archive, private, root, *, live=False):
    v1.git("merge-base", "--is-ancestor", BASE, "HEAD")
    if v1.git("status", "--porcelain", "--", "backend/app", "frontend", "data", "tests/fixtures") or v1.git(
        "diff", "--name-only", BASE, "HEAD", "--", "backend/app", "frontend", "data", "tests/fixtures"
    ):
        raise ValueError("Benchmark requires the exact clean production and fixture revision")
    require_hash(v1.GOLDEN_PATH, GOLDEN_HASH)
    golden = read_json(v1.GOLDEN_PATH)
    for name, expected in golden["source_hashes"].items():
        if digest(safe_path(v1.ROOT, name).read_bytes().replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Frozen oracle or authority source diverged")
    for name, expected in HISTORY.items():
        require_hash(v1.EVAL / "results/v1" / name, expected)
    input_integrity(archive, private)
    data = load_inputs(private)
    policy = v1.PolicyV1(**golden["policy"])
    validator = v1.Draft202012Validator(read_json(v1.EVAL / "result_v1.schema.json"))
    validator.check_schema(validator.schema)
    layer = "C" if live else "B"
    offline_hashes = {}
    if live:
        for split in data:
            path = root / "offline" / f"{split}-b.json"
            offline = read_json(path)
            validator.validate(offline)
            expected = sum("B" in case["eligibility"] for case in data[split]["cases"].values())
            if (offline["code_commit"] != BASE or offline["dataset_sha256"] != data[split]["oracle"]
                    or offline["metrics"]["executed_count"]["numerator"] != expected
                    or not offline["provenance"].get("restart_verified")):
                raise ValueError("Complete offline results must be sealed before live validation")
            if (v1.EVAL / "results/postfix-v1" / path.name).read_bytes() != path.read_bytes():
                raise ValueError("Offline publication copy differs from the sealed report")
            offline_hashes[split] = digest(path.read_bytes())
    out = root / ("live" if live else "offline")
    out.mkdir(parents=True, exist_ok=False)
    budget = None
    if live:
        v1.load_dotenv(v1.ROOT / ".env", override=False)
        os.environ["GEMINI_ESCALATION_ENABLED"] = "false"
        try:
            settings = v1.GeminiSettings.from_environment()
        except ExtractionError:
            settings = None
        if settings and settings.primary_model == v1.PRIMARY:
            budget = v1.GenerationBudget(settings, limit=BUDGET)
    reports, diagnostic_rows = {}, []
    started = datetime.now(timezone.utc).isoformat()
    for split, source in data.items():
        reports[split] = dict(dataset_version=source["version"], dataset_sha256=source["oracle"], code_commit=BASE,
                              layer=layer, split=split, attempts=[], metrics={}, provenance={
                                  "label": LABEL, "harness_git_head": v1.git("rev-parse", "HEAD"),
                                  "started_utc": started, "authority_fingerprint": v1.authority_hash(v1.authority()),
                                  "seed_sha256": golden["source_hashes"]["data/seed_manifest.json"],
                                  "policy": policy.model_dump(mode="json"), "registry_sha256": source["registry_sha256"],
                                  "annotation_sha256": source["annotation_sha256"], "archive_sha256": ARCHIVE_HASH,
                                  "latency_scope": "ASGI POST start through terminal persisted GET response",
                                  "selection": [list(pair) for pair in ORDER] if live else [],
                                  "sealed_offline_sha256": offline_hashes,
                                  "shared_generation_budget": BUDGET if live else 0})
    all_cases = [(split, case_id) for split, source in data.items() for case_id in source["cases"]]
    order = [*ORDER, *(key for key in all_cases if key not in ORDER)] if live else all_cases
    for split, case_id in order:
        source = data[split]
        case = source["cases"][case_id]
        eligible = (split, case_id) in ORDER if live else "B" in case["eligibility"]
        skipped = skip_reason(eligible, budget, live)
        if skipped:
            rows = [dict(v1.start_row(case, case), status=skipped[0], notes=skipped[1])]
        else:
            raw = safe_path(source["root"], case["pdf"]["path"]).read_bytes()
            if digest(raw) != case["pdf"]["sha256"]:
                raise ValueError("PDF changed since preflight")
            claims = claims_for(case, raw, source["annotations"].get(case_id, {}))

            def observe(snapshot, row):
                row_diagnostics = diagnostics(snapshot, row, raw, claims, budget)
                row_diagnostics["split"] = split
                diagnostic_rows.append(row_diagnostics)
                v1.json_new(out / f"{case_id}-diagnostics.json", row_diagnostics)

            rows = v1.pdf_attempt(case, raw, claims, budget, policy, observe=observe, verify_restart=True)
        for row in rows:
            row["classification"] = classification(row)
            reports[split]["attempts"].append(row)
            v1.json_new(out / f"{case_id}-{row['track']}-001.json", row)
            print(case_id, row["track"], row["classification"], row["model_calls"], flush=True)
    finished = datetime.now(timezone.utc).isoformat()
    for split, report in reports.items():
        report["metrics"] = metrics(report["attempts"], layer)
        report["provenance"].update(finished_utc=finished, restart_verified=True,
                                    actual_generations_in_split=sum(r["model_calls"] or 0 for r in report["attempts"]))
        validator.validate(report)
        v1.json_new(out / f"{split}-{layer.lower()}.json", report)
    v1.json_new(out / "diagnostics.json", {"label": LABEL, "layer": layer, "observations": diagnostic_rows})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--private", type=Path, default=v1.ROOT / "tmp/evaluation-heldout-v1")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-live", action="store_true")
    args = parser.parse_args()
    run(args.archive, args.private, args.output, live=args.allow_live)
