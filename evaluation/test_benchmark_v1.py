from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

from jsonschema import Draft202012Validator, ValidationError
import pytest

from benchmark_v1 import EVAL, GOLDEN_PATH, ROOT, classification, execute, json_new
from benchmark_inputs import digest, read_json, registered_cases, relative_parts, unpack_archive
from benchmark_source import ControlledProvider, claims_for, printed_date
from app.documents.schema import parse_response


@pytest.mark.parametrize("path", ["../file.pdf", "C:/file.pdf", "a/../../file.pdf", "/file.pdf",
                                  "a\\file.pdf", "file.pdf:content", "NUL.pdf", "a//file.pdf"])
def test_relative_paths_reject_unsafe_inputs(path):
    with pytest.raises(ValueError):
        relative_parts(path)


def test_development_shared_action_is_one_submission():
    registry = read_json(GOLDEN_PATH)
    cases = registered_cases(registry, ROOT, split="development")
    assert len(cases) == 13 and len([case for case in cases.values() if case["pdf"]]) == 10
    assert cases["AMBIGUOUS_PO"]["human_action"]["expected_decision"] == "REVIEW_REQUIRED"
    registry["cases"].append(deepcopy(registry["cases"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        registered_cases(registry, ROOT, split="development")


@pytest.mark.parametrize("problem", ["hash", "suffix", "signature", "page limit"])
def test_reject_malformed_registry_asset(tmp_path, problem):
    registry = read_json(GOLDEN_PATH)
    registry["cases"] = registry["cases"][:1]
    meta = registry["cases"][0]["pdf"]
    raw = (ROOT / meta["path"]).read_bytes()
    meta["path"] = "one.pdf"
    if problem == "hash":
        meta["sha256"] = "0" * 64
    elif problem == "suffix":
        meta["path"] = "one.txt"
    elif problem == "signature":
        raw = b"this is not an invoice"
        meta.update(sha256=digest(raw), byte_count=len(raw))
    else:
        meta["page_count"] = 11
    (tmp_path / meta["path"]).write_bytes(raw)
    with pytest.raises(ValueError):
        registered_cases(registry, tmp_path, split="development")


def test_archive_refuses_escape_before_writing(tmp_path):
    source = tmp_path / "archive.zip"
    destination = tmp_path / "private"
    with ZipFile(source, "w") as archive:
        archive.writestr("../one.pdf", b"untrusted")
    with pytest.raises(ValueError):
        unpack_archive(source, destination, {"one.pdf"})
    assert not destination.exists()


def test_archive_preserves_registered_member_bytes(tmp_path):
    source = tmp_path / "archive.zip"
    destination = tmp_path / "private"
    with ZipFile(source, "w") as archive:
        archive.writestr("dataset/one.pdf", b"original bytes")
    unpack_archive(source, destination, {"one.pdf"})
    assert (destination / "one.pdf").read_bytes() == b"original bytes"
    with pytest.raises(FileExistsError):
        unpack_archive(source, destination, {"one.pdf"})


def test_controlled_wire_does_not_embed_trust_or_unprinted_scan_net():
    case = next(row for row in read_json(GOLDEN_PATH)["cases"] if row["case_id"] == "SCAN_CONFLICT")
    raw = (ROOT / case["pdf"]["path"]).read_bytes()
    annotation = read_json(EVAL / "development_scan_source.json")[case["case_id"]]
    claims = claims_for(case, raw, annotation)
    assert "lines[0].net" not in claims
    invoice, parsed_claims = parse_response(ControlledProvider(case, claims).reply)
    assert invoice.lines[0].net is None and invoice.evidence == ()
    assert len(parsed_claims) == 12 and all(claim.quote for claim in parsed_claims)


def test_first_result_cannot_be_overwritten(tmp_path):
    path = tmp_path / "first.json"
    json_new(path, {"original": True})
    with pytest.raises(FileExistsError):
        json_new(path, {"original": False})
    assert read_json(path) == {"original": True}


def test_input_sidecar_can_keep_the_original_printed_date():
    assert printed_date("ISSUED 07 Nov 2026", "2026-11-07") == "07 Nov 2026"
    assert printed_date("ISSUED 08 Nov 2026", "2026-11-07") is None


def test_typed_results_validate_against_schema(tmp_path):
    output = tmp_path / "facts"
    args = SimpleNamespace(layer="A", split="development", asset_root=ROOT, manifest=GOLDEN_PATH,
                           annotations=None, output=output, oracle_sha=None, allow_live=False)
    execute(args)
    report = read_json(output / "report.json")
    validator = Draft202012Validator(read_json(EVAL / "result_v1.schema.json"))
    validator.validate(report)
    assert report["metrics"]["exact_decisions"] == {"numerator": 13, "denominator": 13}
    invalid = deepcopy(report)
    row = invalid["attempts"][0]
    row["execution_state"] = "PROCESSING_FAILED"
    assert classification(row) == "Technical Failure"
    with pytest.raises(ValidationError):
        validator.validate(invalid)
