"""Measure isolated parsing and in-process grounding on offline development inputs."""
import argparse
import json
from pathlib import Path
from statistics import median
import sys
from time import perf_counter_ns


ROOT = Path(__file__).resolve().parents[1]


def measure(backend, parse_repeats, ground_repeats):
    sys.path[:0] = [str(backend.resolve()), str(ROOT / "backend/tests")]
    import pymupdf
    from app.documents.evidence import ground_evidence
    from app.documents.inspection import inspect_pdf
    from app.documents.schema import parse_response
    from source_layout_fixtures import source_layout
    from test_document_engine import wire
    from test_mixed_document_review import with_logo

    fixtures = ROOT / "tests/fixtures"
    clean = (fixtures / "HAPPY_CLEAN.pdf").read_bytes()
    with pymupdf.open(stream=clean, filetype="pdf") as pdf:
        pdf.new_page().insert_text((52, 65), "Supplementary invoice information. No additional charges are listed on this page.")
        two_pages = pdf.tobytes(no_new_id=True)
    table, table_wire = source_layout()
    scan = (fixtures / "SCAN_CONFLICT.pdf").read_bytes()
    workloads = (
        ("native", clean, wire()), ("two-page native", two_pages, wire()),
        ("table native", table, table_wire), ("image-only", scan, wire("SCAN_CONFLICT", line_net=False)),
        ("mixed", with_logo(clean), wire()),
    )
    cases = {}
    for label, raw, reply in workloads:
        invoice, claims = parse_response(json.dumps(reply))
        inspected = inspect_pdf(raw)
        ground_evidence(invoice, claims, inspected)
        parsing = []
        for _ in range(parse_repeats):
            start = perf_counter_ns()
            inspected = inspect_pdf(raw)
            parsing.append((perf_counter_ns() - start) / 1_000_000)
        grounding = []
        for _ in range(7):
            start = perf_counter_ns()
            for _ in range(ground_repeats):
                result = ground_evidence(invoice, claims, inspected)
            grounding.append((perf_counter_ns() - start) / ground_repeats / 1_000)
        cases[label] = {"route": inspected.route, "pages": len(inspected.pages),
                        "parser_ms": round(median(parsing), 3),
                        "grounding_us": round(median(grounding), 3),
                        "native_verified": sum(ref.evidence_state == "NATIVE_VERIFIED" for ref in result.evidence)}
    return cases


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", type=Path, default=ROOT / "backend")
    args = parser.parse_args()
    print(json.dumps(measure(args.backend, parse_repeats=11, ground_repeats=300), indent=2))
