"""Use the actual bounded parser and strict provider wire format."""
from copy import deepcopy
import json

import pytest

from app.contracts import PolicyV1
from app.domain import build_context, evaluate
from source_layout_fixtures import source_layout
from test_document_engine import FakeProvider, ROOT, run, wire
from test_finance_engine import HISTORY, POS, VENDORS, codes, context_for, evidence_for


def extract(pdf, reply):
    return run(pdf, FakeProvider([json.dumps(reply)]), max_attempts=1).invoice


def evidence(invoice):
    return {ref.field: ref.evidence_state for ref in invoice.evidence}


@pytest.mark.parametrize("statement", [False, True])
def test_original_native_source_layout_verifies(statement):
    pdf, reply = source_layout(statement=statement)
    invoice = extract(pdf, reply)
    assert set(evidence(invoice).values()) == {"NATIVE_VERIFIED"}
    assert [line.description for line in invoice.lines] == ["Stationery kits", "Archive packs"]
    assert [str(line.qty) for line in invoice.lines] == ["3", "2"]
    decision = evaluate(build_context(invoice, VENDORS, POS, HISTORY), PolicyV1())
    assert decision.outcome == "READY_FOR_AP"
    assert not {"EXACT_DUPLICATE", "LINE_MAPPING_UNRESOLVED"} & codes(decision)


@pytest.mark.parametrize("conflict", ["same_page", "next_page"])
def test_split_authoritative_total_conflict_withholds_verification(conflict):
    pdf, reply = source_layout(statement=True, conflict=conflict)
    invoice = extract(pdf, reply)
    assert evidence(invoice)["net"] == "NATIVE_VERIFIED"
    assert evidence(invoice)["total"] == "SOURCE_LOCATED_UNVERIFIED"
    assert str(invoice.total) == "5900"


def test_ambiguous_right_and_below_amounts_withhold_verification():
    pdf, reply = source_layout(ambiguity=True)
    invoice = extract(pdf, reply)
    assert evidence(invoice)["total"] != "NATIVE_VERIFIED"


def test_competing_purchase_reference_on_appendix_withholds_verification():
    pdf, reply = source_layout(conflict="other_po")
    invoice = extract(pdf, reply)
    assert evidence(invoice)["po_reference"] == "SOURCE_LOCATED_UNVERIFIED"
    assert invoice.po_reference == "PO-6001"


@pytest.mark.parametrize("target,replacement,raw,quote", [
    ("vendor_name_raw", "West Yard Workshop", "West Yard Workshop", "Bill to West Yard Workshop"),
    ("total", "7700", "7,700.00", "Combined account balance INR 7,700.00"),
    ("invoice_number", "PO-6001", "PO-6001", "PO No PO-6001"),
    ("lines[0].qty", "2", "2", "OR-SUPPLY-01 Archive packs 2 1,000.00 2,000.00"),
    ("lines[0].unit_price_net", "1000", "1,000.00", "OR-SUPPLY-01 Archive packs 2 1,000.00 2,000.00"),
    ("lines[0].qty", "3", "3", "3"),
])
def test_other_real_cells_do_not_support_the_claimed_field(target, replacement, raw, quote):
    pdf, reply = source_layout(statement=True)
    if target.startswith("lines"):
        reply["lines"][0][target.split(".")[1]] = replacement
    else:
        reply[target] = replacement
    next(claim for claim in reply["evidence"] if claim["field"] == target).update(raw_value=raw, quote=quote)
    assert evidence(extract(pdf, reply))[target] != "NATIVE_VERIFIED"


def test_missing_item_code_and_reordered_repeated_rows_are_uncertain():
    pdf, reply = source_layout(missing_code=True)
    invoice = extract(pdf, reply)
    assert evidence(invoice)["lines[1].qty"] != "NATIVE_VERIFIED"
    pdf, reply = source_layout()
    reply["lines"].reverse()
    for claim in reply["evidence"]:
        if claim["field"].startswith("lines["):
            index = int(claim["field"][6])
            claim["field"] = f"lines[{1 - index}]" + claim["field"][8:]
    invoice = extract(pdf, reply)
    assert evidence(invoice)["lines[0].qty"] != "NATIVE_VERIFIED"


@pytest.mark.parametrize("variant", ["overlapping", "identical"])
def test_overlapping_or_identical_row_quotes_do_not_verify(variant):
    pdf, reply = source_layout(**{variant: True})
    assert all(evidence(extract(pdf, reply))[field] != "NATIVE_VERIFIED"
               for field in ("lines[0].qty", "lines[1].qty"))


def test_printed_service_periods_separate_otherwise_identical_rows():
    pdf, reply = source_layout(identical=True, periods=True)
    invoice = extract(pdf, reply)
    refs = [ref for ref in invoice.evidence if ref.field.endswith(".qty")]
    assert [ref.evidence_state for ref in refs] == ["NATIVE_VERIFIED"] * 2
    assert [next(month for month in ("Aug", "Sep") if month in ref.quote) for ref in refs] == ["Aug", "Sep"]


def test_optional_net_without_a_printed_cell_is_not_verified():
    pdf, reply = source_layout(omit_line_net=True)
    states = evidence(extract(pdf, reply))
    assert states["lines[1].qty"] == "NATIVE_VERIFIED"
    assert states["lines[1].net"] != "NATIVE_VERIFIED"


def test_competing_inline_and_split_invoice_labels_remain_uncertain():
    pdf, reply = source_layout(competing_label=True)
    assert evidence(extract(pdf, reply))["invoice_number"] == "SOURCE_LOCATED_UNVERIFIED"


def test_vertical_label_does_not_capture_adjacent_buyers_name():
    pdf, reply = source_layout(buyer_below=True)
    reply["vendor_name_raw"] = "West Yard Workshop"
    claim = next(ref for ref in reply["evidence"] if ref["field"] == "vendor_name_raw")
    claim.update(raw_value="West Yard Workshop", quote="Supplier West Yard Workshop")
    assert evidence(extract(pdf, reply))["vendor_name_raw"] != "NATIVE_VERIFIED"


def test_table_net_column_does_not_substitute_an_invoice_subtotal():
    pdf, reply = source_layout(column_net_only=True)
    reply["net"] = "3000"
    claim = next(ref for ref in reply["evidence"] if ref["field"] == "net")
    claim.update(raw_value="3,000.00", quote="Net amount 3,000.00")
    states = evidence(extract(pdf, reply))
    assert states["lines[0].net"] == "NATIVE_VERIFIED"
    assert states["net"] != "NATIVE_VERIFIED"


def test_development_statement_fixture_repeated_reference():
    manifest = json.loads((ROOT / "data/golden_dataset_v1.json").read_text())
    case = next(case for case in manifest["cases"] if case["case_id"] == "STATEMENT_PRIOR_BALANCE")
    reply = wire()
    reply.update(invoice_number=case["invoice_number"], invoice_date=case["invoice_date"],
                 total=case["gross"], net=case["net"], tax=case["tax"], lines=deepcopy(case["lines"]))
    claim = next(ref for ref in reply["evidence"] if ref["field"] == "total")
    claim.update(raw_value="4,720.00", quote="Invoice total: INR 4,720.00")
    invoice = extract((ROOT / case["pdf"]["path"]).read_bytes(), reply)
    assert evidence(invoice)["total"] == "NATIVE_VERIFIED"


@pytest.mark.parametrize("item,trusted,owner", [(None, False, "AP"), ("DEV-UNKNOWN", False, "AP"),
                                              ("DEV-UNKNOWN", True, "Procurement")])
def test_scope_owner_requires_a_supported_explicit_item(item, trusted, owner):
    context = context_for("HAPPY_CLEAN")
    line = context.invoice.lines[0].model_copy(update={"item_code": item})
    invoice = context.invoice.model_copy(update={"lines": (line,)})
    if trusted:
        invoice = evidence_for(invoice)
    context = build_context(invoice, VENDORS, POS, HISTORY)
    findings = evaluate(context, PolicyV1()).findings
    mapping = next(f for f in findings if f.code == "LINE_MAPPING_UNRESOLVED")
    assert mapping.owner == owner
    if trusted:
        assert "authorized PO amendment" in mapping.next_action
    else:
        assert mapping.title == "Item or PO details need verification"
        assert "rendered invoice" in mapping.next_action and "intended PO" in mapping.next_action


def test_supported_native_extra_item_routes_to_procurement():
    pdf, reply = source_layout(extra_item=True)
    invoice = extract(pdf, reply)
    assert evidence(invoice)["lines[1].item_code"] == "NATIVE_VERIFIED"
    decision = evaluate(build_context(invoice, VENDORS, POS, HISTORY), PolicyV1())
    assert decision.outcome == "REVIEW_REQUIRED"
    assert decision.primary_reason_code == "LINE_MAPPING_UNRESOLVED" and decision.owner == "Procurement"
    assert next(f for f in decision.findings if f.code == "LINE_MAPPING_UNRESOLVED").explanation.endswith(": 2")


def test_image_only_review_has_scan_specific_guidance():
    pdf = (ROOT / "tests/fixtures/SCAN_CONFLICT.pdf").read_bytes()
    invoice = extract(pdf, wire("SCAN_CONFLICT", line_net=False))
    assert "NATIVE_VERIFIED" not in evidence(invoice).values()
    decision = evaluate(build_context(invoice, VENDORS, POS, HISTORY), PolicyV1())
    source = next(finding for finding in decision.findings if finding.code == "SOURCE_EVIDENCE_MISSING")
    assert decision.outcome == "REVIEW_REQUIRED"
    assert "billed history" in source.next_action and "native PDF" in source.next_action
