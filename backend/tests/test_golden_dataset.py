"""Golden preparation checks. No extraction provider or benchmark execution."""
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

import pymupdf
import pytest

from app.contracts import ExtractedInvoiceV1, PolicyV1
from app.documents.inspection import inspect_pdf
from app.domain import build_context, evaluate
from app.domain.human_resolution import POConfirmation, evaluate_with_confirmed_po
from test_finance_engine import HISTORY, POS, VENDORS, codes, evidence_for

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_golden_fixtures import generate, money


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


DATA = read("data/golden_dataset_v1.json")
CASES = DATA["cases"]
BASELINE = [case for case in CASES if case["group"] == "A"]
HUMAN = [case for case in CASES if case["group"] == "B"]
NEW = [case for case in CASES if case["group"] == "C"]
SUBMISSIONS = {case["case_id"]: case for case in CASES}
ASSETS = {case["pdf"]["path"]: case for case in CASES if case["pdf"]}
POLICY = PolicyV1(**DATA["policy"])
DECIMAL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?\Z")


def test_dataset_composition_and_provenance():
    assert DATA["version"] == "golden-v1"
    assert [len(group) for group in (BASELINE, HUMAN, NEW)] == [10, 2, 2]
    assert len(CASES) == len({(c["group"], c["case_id"]) for c in CASES}) == 14
    assert len(SUBMISSIONS) == 13 and len(ASSETS) == 10
    for path, expected in DATA["source_hashes"].items():
        assert sha256((ROOT / path).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == expected
    targets = DATA["historical_targets"]
    assert targets["evaluation_eligibility"] == []
    historical = read(targets["source"])["cases"]
    assert targets["case_ids"] == [case["case_id"] for case in historical]
    assert all(case["current_observation"] is None for case in historical)
    assert {c["case_id"] for c in CASES if not c["pdf"]} == {"BANK_CHANGED", "INJECTION", "UNKNOWN_VENDOR"}
    for case in CASES:
        assert case["eligibility"] == (["A", "B", "C"] if case["pdf"] else ["A"])
    shared = next(c for c in BASELINE if c["case_id"] == "AMBIGUOUS_PO")
    assert {k: v for k, v in SUBMISSIONS["AMBIGUOUS_PO"].items() if k != "human_action"} == {**shared, "group": "B"}


@pytest.mark.parametrize("case", BASELINE, ids=lambda case: case["case_id"])
def test_original_oracle_values_unchanged(case):
    path, original_id = case["provenance"].split("#")
    original = next(row for row in read(path)["fixture_cases"] if row["id"] == original_id)
    for key in ("vendor_name", "invoice_number", "invoice_date", "po_reference", "currency", "net", "tax", "gross", "expected_execution_state", "expected_decision"):
        assert case[key] == original[key]
    assert [{k: v for k, v in line.items() if k != "net"} for line in case["lines"]] == original["lines"]
    assert case["required_findings"] == original["required_reason_codes"]
    assert case["expected_route"] == original["document_route"]
    assert case["bank_instructions"] == original.get("bank_instructions")


@pytest.mark.parametrize("path", ASSETS)
def test_frozen_asset_and_native_route(path):
    case = ASSETS[path]
    asset = case["pdf"]
    raw = (ROOT / path).read_bytes()
    assert len(raw) == asset["byte_count"]
    assert sha256(raw).hexdigest() == asset["sha256"]
    assert inspect_pdf(raw).route == case["expected_route"]
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        assert len(pdf) == asset["page_count"]
        extracted = "\n".join(page.get_text() for page in pdf)
    if case["expected_route"] == "image_only":
        assert not extracted.strip()
        assert all(line["net"] is None for line in case["lines"])
        return
    for name in ("vendor_name", "invoice_number", "invoice_date", "po_reference", "currency"):
        assert case[name] is None or case[name] in extracted
    for line in case["lines"]:
        assert line["description"] in extracted
        assert line["item_code"] is None or line["item_code"] in extracted
    if case["group"] == "C":
        for key in ("net", "tax", "gross"):
            assert money(case[key]) in extracted
        for line in case["lines"]:
            assert f"Quantity: {line['qty']}" in extracted
            assert f"Unit price (net): {money(line['unit_price_net'])}" in extracted
            assert f"Line net: {money(line['net'])}" in extracted
        if summary := case.get("account_summary"):
            assert f"Previous account balance: {money(summary['previous_balance'])}" in extracted
            assert f"Account balance including previous amount: {money(summary['combined_balance'])}" in extracted
            assert extracted.count(f"Invoice total: {money(case['gross'])}") == 1
            assert f"Current invoice total: {money(case['gross'])}" in extracted


def test_new_pdfs_reproduce_byte_for_byte(tmp_path):
    generate(tmp_path)
    assert len(list(tmp_path.glob("*.pdf"))) == len(NEW)
    for case in NEW:
        path = ROOT / case["pdf"]["path"]
        assert (tmp_path / path.name).read_bytes() == path.read_bytes()


def context_from_oracle(case):
    for amount in (case["net"], case["tax"], case["gross"],
                   *(line[key] for line in case["lines"] for key in ("net", "qty", "unit_price_net") if line[key] is not None)):
        assert isinstance(amount, str) and DECIMAL.fullmatch(amount)
    invoice = ExtractedInvoiceV1(
        vendor_name_raw=case["vendor_name"], invoice_number=case["invoice_number"],
        invoice_date=case["invoice_date"], po_reference=case["po_reference"],
        currency=case["currency"], net=case["net"], tax=case["tax"], total=case["gross"],
        lines=case["lines"], bank_instructions=case["bank_instructions"],
    )
    return build_context(evidence_for(invoice, unverified=case["expected_route"] == "image_only"), VENDORS, POS, HISTORY)


@pytest.mark.parametrize("case_id", SUBMISSIONS)
def test_trusted_facts_decisions(case_id):
    case = SUBMISSIONS[case_id]
    context = context_from_oracle(case)
    decision = evaluate(context, POLICY)
    assert decision.outcome == case["expected_decision"]
    assert decision.outcome not in case["forbidden_decisions"]
    assert set(case["required_findings"]) <= codes(decision)
    assert not set(case.get("forbidden_findings", [])) & codes(decision)
    if variant := case.get("policy_variant"):
        policy = PolicyV1(price_tolerance_pct=variant["price_tolerance_pct"])
        assert evaluate(context, policy).outcome == variant["expected_decision"]


@pytest.mark.parametrize("case", HUMAN, ids=lambda case: case["case_id"])
def test_human_action_oracle(case):
    context = context_from_oracle(case)
    before = context.model_dump_json()
    action = case["human_action"]
    result = evaluate_with_confirmed_po(context, POLICY, POConfirmation(action["po_id"], action["rationale"]))
    assert result.outcome == action["expected_decision"]
    assert set(action["required_findings"]) <= codes(result)
    assert not set(action["forbidden_findings"]) & codes(result)
    assert context.model_dump_json() == before


@pytest.mark.parametrize("case", NEW, ids=lambda case: case["case_id"])
def test_new_case_arithmetic_and_authority(case):
    context = context_from_oracle(case)
    invoice = context.invoice
    assert sum(line.net for line in invoice.lines) == invoice.net
    assert invoice.net * Decimal("0.18") == invoice.tax
    assert invoice.net + invoice.tax == invoice.total
    assert all(line.qty * line.unit_price_net == line.net for line in invoice.lines)
    po = context.selected_po
    assert po.id == invoice.po_reference and po.currency == invoice.currency
    assert context.canonical_vendor.id == po.vendor_id and context.canonical_vendor.approved
    prior = [entry for entry in HISTORY if entry.po_id == po.id]
    assert not any(entry.vendor_id == po.vendor_id and entry.invoice_number == invoice.invoice_number for entry in HISTORY)
    billed = sum((entry.net for entry in prior), Decimal(0))
    assert invoice.net <= po.authorized_net - billed
    allowed = {line.item_code: line for line in po.lines}
    matched, unmatched = [], []
    for line in invoice.lines:
        if line.item_code not in allowed:
            unmatched.append(line.item_code)
            continue
        matched.append(line.item_code)
        po_line = allowed[line.item_code]
        billed_qty = sum(hist_line.qty for entry in prior for hist_line in entry.lines if hist_line.item_code == line.item_code)
        assert line.qty <= po_line.ordered_qty - billed_qty
        assert line.unit_price_net == po_line.unit_price_net
    if expected := case.get("authority_expectations"):
        assert (po.authorized_net, billed, po.authorized_net - billed) == tuple(
            Decimal(expected[key]) for key in ("authorized_net", "previously_billed_net", "remaining_net")
        )
        assert matched == expected["authorized_invoice_line_codes"]
        assert unmatched == expected["unmatched_invoice_line_codes"]
    if summary := case.get("account_summary"):
        previous, current, combined = (Decimal(summary[key]) for key in ("previous_balance", "current_invoice_total", "combined_balance"))
        assert current == invoice.total and previous + current == combined


def test_scope_finding_identifies_only_the_unmapped_line():
    case = SUBMISSIONS["SCOPE_UNAUTHORIZED_LINE"]
    decision = evaluate(context_from_oracle(case), POLICY)
    finding = next(item for item in decision.findings if item.code == "LINE_MAPPING_UNRESOLVED")
    assert finding.explanation.endswith(": 2")
    assert finding.next_action


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Known routing gap: mapping defaults to AP and omits the PO amendment or correction step")
def test_scope_routing_matches_frozen_business_oracle():
    case = SUBMISSIONS["SCOPE_UNAUTHORIZED_LINE"]
    decision = evaluate(context_from_oracle(case), POLICY)
    finding = next(item for item in decision.findings if item.code == "LINE_MAPPING_UNRESOLVED")
    assert finding.owner == case["expected_owner"]


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="Known remediation gap: action requests generic item clarification instead of an amendment or corrected invoice")
def test_scope_action_matches_frozen_business_oracle():
    case = SUBMISSIONS["SCOPE_UNAUTHORIZED_LINE"]
    decision = evaluate(context_from_oracle(case), POLICY)
    finding = next(item for item in decision.findings if item.code == "LINE_MAPPING_UNRESOLVED")
    action = finding.next_action.casefold()
    assert "verif" in action and ("amend" in action or "correct" in action)
