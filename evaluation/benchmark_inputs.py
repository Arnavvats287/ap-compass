"""Evaluation-only registry and archive boundaries."""
from datetime import date
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import stat
from zipfile import ZipFile

from app.documents.limits import MAX_INPUT_BYTES, MAX_PAGES
from app.documents.schema import WireInvoice

HEADER = {"vendor_name_raw": "vendor_name", "invoice_number": "invoice_number",
          "invoice_date": "invoice_date", "po_reference": "po_reference", "currency": "currency",
          "net": "net", "tax": "tax", "total": "gross"}
LINE_FIELDS = ("description", "item_code", "qty", "unit_price_net", "net")
SHA = re.compile(r"[0-9a-f]{64}\Z")
KEY = re.compile(r"[A-Za-z0-9_-]{1,90}\Z")
OUTCOMES = {"READY_FOR_AP", "REVIEW_REQUIRED", "BLOCKED"}


def digest(raw):
    return sha256(raw).hexdigest()


def read_json(path):
    def unique(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError("Duplicate JSON property")
        return result

    def reject_constant(_):
        raise ValueError("Non-finite JSON constant")

    return json.loads(path.read_bytes(), object_pairs_hook=unique, parse_constant=reject_constant)


def relative_parts(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_. /-]+", name):
        raise ValueError("Unsupported relative path")
    parts = name.split("/")
    if any(part in {"", ".", ".."} or part.endswith((".", " ")) or
           re.match(r"(?:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)", part, re.I) for part in parts):
        raise ValueError("Unsafe relative path")
    return PurePosixPath(name).parts


def safe_path(root, name):
    path = root.joinpath(*relative_parts(name)).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path escapes its input root")
    return path


def wire_facts(case):
    return WireInvoice.model_validate({
        **{key: case[source] for key, source in HEADER.items()},
        "lines": [{key: line[key] for key in LINE_FIELDS} for line in case["lines"]],
        "bank_instructions": case.get("bank_instructions"), "evidence": [],
    })


def registered_cases(registry, root, *, split):
    if not isinstance(registry.get("version"), str) or not KEY.fullmatch(registry["version"]):
        raise ValueError("Unsupported registry version")
    if split == "development" and registry["version"] != "golden-v1":
        raise ValueError("Unsupported development registry version")
    cases = registry["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 100:
        raise ValueError("Unsupported registry size")
    groups, unique, files, invoices = set(), {}, set(), set()
    for case in cases:
        code, group = case["case_id"], case["group"]
        if not KEY.fullmatch(code) or (group, code) in groups:
            raise ValueError("Invalid or duplicate registry identifier")
        groups.add((group, code))
        if code in unique:
            first = unique[code]
            shared = (split == "development" and first["group"] == "A" and group == "B"
                      and "human_action" in case and "human_action" not in first
                      and {k: v for k, v in case.items() if k not in {"group", "human_action"}}
                      == {k: v for k, v in first.items() if k != "group"})
            if not shared:
                raise ValueError("Conflicting duplicate case identifier")
            unique[code] = {**first, "human_action": case["human_action"]}
            continue
        wire = wire_facts(case)
        date.fromisoformat(wire.invoice_date)
        identity = wire.invoice_number.casefold()
        if identity in invoices:
            raise ValueError("Duplicate invoice identifier")
        invoices.add(identity)
        if (case["expected_decision"] not in OUTCOMES or case["expected_execution_state"] != "COMPLETED"
                or case["expected_route"] not in {"native_text", "image_only", "mixed"}
                or case["eligibility"] != (["A", "B", "C"] if case["pdf"] else ["A"])
                or any(not KEY.fullmatch(code) for code in case["required_findings"])):
            raise ValueError("Unsupported case expectation")
        if asset := case["pdf"]:
            path = safe_path(root, asset["path"])
            if path.suffix.lower() != ".pdf" or path in files:
                raise ValueError("Unsupported or duplicate PDF input")
            files.add(path)
            size = path.stat().st_size
            if (not 0 < size <= MAX_INPUT_BYTES or size != asset["byte_count"] or
                    not 1 <= asset["page_count"] <= MAX_PAGES or not SHA.fullmatch(asset["sha256"])):
                raise ValueError("Unsupported PDF asset metadata")
            raw = path.read_bytes()
            if digest(raw) != asset["sha256"]:
                raise ValueError("PDF SHA-256 mismatch")
            if not raw.startswith(b"%PDF-") or not raw.rstrip().endswith(b"%%EOF"):
                raise ValueError("Unsupported PDF signature")
        unique[code] = case
    return unique


def unpack_archive(source: Path, destination: Path, expected: set[str]):
    """Copy only the expected regular files into a fresh private directory."""
    with ZipFile(source) as archive:
        entries = {}
        seen = set()
        for item in archive.infolist():
            parts = relative_parts(item.filename.rstrip("/") if item.is_dir() else item.filename)
            mode = stat.S_IFMT(item.external_attr >> 16)
            if mode not in {0, stat.S_IFDIR if item.is_dir() else stat.S_IFREG} or item.flag_bits & 1:
                raise ValueError("Unsupported ZIP entry")
            folded = tuple(part.casefold() for part in parts)
            if folded in seen:
                raise ValueError("Duplicate ZIP path")
            seen.add(folded)
            if item.is_dir():
                continue
            name = parts[-1]
            limit = MAX_INPUT_BYTES if name.endswith(".pdf") else 256 * 1024
            if name not in expected or name in entries or not 0 < item.file_size <= limit:
                raise ValueError("Unexpected, oversized or duplicate ZIP member")
            entries[name] = (item, limit)
        if set(entries) != expected:
            raise ValueError("Missing ZIP inputs")
        destination.mkdir(parents=True, exist_ok=False)
        for name, (item, limit) in entries.items():
            with archive.open(item) as stream:
                raw = stream.read(limit + 1)
            if len(raw) != item.file_size or len(raw) > limit:
                raise ValueError("ZIP size mismatch")
            with safe_path(destination, name).open("xb") as file:
                file.write(raw)
