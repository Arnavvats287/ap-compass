"""Validate a supplied independent oracle and register a private local copy."""
import argparse
from decimal import Decimal
from pathlib import Path

from benchmark_v1 import ROOT, authority, json_new
from benchmark_inputs import digest, read_json, registered_cases, safe_path, unpack_archive
from app.domain.matching import resolve_vendor

NAMES = {
    "H01": "H01_CLEAN_INDEPENDENT.pdf", "H02": "H02_REPEATED_ITEM_CODE.pdf",
    "H03": "H03_STATEMENT_BALANCE.pdf", "H04": "H04_UNAUTHORIZED_SCOPE.pdf",
    "H05": "H05_IMAGE_ONLY_SCAN.pdf", "H06": "H06_MIXED_RASTER_TERMS.pdf",
}
ORACLE = "heldout_oracle_v1.json"
EXPECTED = {*NAMES.values(), ORACLE, "VALIDATION_REPORT.md", "DATASET_README.md"}
ROUTES = {"native_text_pdf": "native_text", "image_only_scanned_pdf": "image_only", "mixed_content_pdf": "mixed"}


def money(value):
    if not isinstance(value, str):
        raise ValueError("Expected exact decimal-string truth")
    return Decimal(value)


def check_truth(printed, business, vendors, orders, history):
    net, tax, gross = [money(printed[key]) for key in ("net", "tax", "gross")]
    if net + tax != gross or tax != net * money(printed["tax_rate_percent"]) / 100:
        raise ValueError("Inconsistent printed arithmetic")
    lines = printed["lines"]
    if sum(money(line["line_net"]) for line in lines) != net or any(
        not isinstance(line["quantity"], int) or line["quantity"] <= 0 or
        line["quantity"] * money(line["unit_net_price"]) != money(line["line_net"]) for line in lines
    ):
        raise ValueError("Inconsistent printed line arithmetic")
    vendor = resolve_vendor(printed["vendor_name"], vendors)
    po = next((row for row in orders if row.id == printed["po_reference"]), None)
    if not vendor or not vendor.approved or not po or po.vendor_id != vendor.id or po.currency != printed["currency"]:
        raise ValueError("Independent oracle disagrees with frozen authority identity")
    billed = [row for row in history if row.po_id == po.id]
    reconciliation = business["po_reconciliation"]
    prior = sum((row.net for row in billed), Decimal(0))
    if (not business["invoice_arithmetic_reconciles"] or reconciliation["balance_consumed_by_this_evaluation"]
            or prior != money(reconciliation["previously_billed_po_net"])
            or po.authorized_net - prior != money(reconciliation["pre_invoice_remaining_po_net"])
            or po.authorized_net != money(reconciliation["authorized_po_net"])
            or net != money(reconciliation["current_invoice_net"])
            or sorted(row.invoice_number for row in billed) != sorted(reconciliation["prior_billed_invoice_numbers"])):
        raise ValueError("Independent oracle disagrees with frozen authority amounts")
    mapped = {line.item_code: line for line in po.lines}
    unresolved = [line["item_code"] for line in lines if line["item_code"] not in mapped]
    if unresolved != [line["item_code"] for line in reconciliation["unmapped_invoice_lines"]]:
        raise ValueError("Independent oracle disagrees with authorized line scope")
    for code, order_line in mapped.items():
        matched = [line for line in lines if line["item_code"] == code]
        prior_qty = sum(line.qty for row in billed for line in row.lines if line.item_code == code)
        if (sum(line["quantity"] for line in matched) > order_line.ordered_qty - prior_qty
                or any(money(line["unit_net_price"]) != order_line.unit_price_net for line in matched)):
            raise ValueError("Independent oracle disagrees with authorized quantity or price")
    if summary := printed["account_summary"]:
        previous = money(summary["previous_account_balance"])
        if gross != money(summary["current_invoice_gross_repeated"]) or previous + gross != money(summary["combined_account_balance"]):
            raise ValueError("Inconsistent statement split")


def register(original, registry):
    rows = read_json(original / ORACLE)
    if not isinstance(rows, list) or len(rows) != len(NAMES) or {x["case_id"] for x in rows} != set(NAMES):
        raise ValueError("Independent oracle has an unexpected case set")
    masters = authority()
    cases = []
    for external in rows:
        code = external["case_id"]
        name = NAMES[code]
        if name != external["filename"]:
            raise ValueError("Independent dataset filename mismatch")
        printed, business, source = (external[name] for name in
            ("printed_document_truth", "financial_business_oracle", "source_verification"))
        check_truth(printed, business, *masters)
        route = ROUTES[external["document_type"]]
        if route != source["expected_document_route"] or printed["bank_instructions"]["print_status"] != "absent":
            raise ValueError("Independent trust labels do not match v1 inputs")
        findings = list(business["expected_reason_code_concepts"])
        target = business["expected_business_outcome_with_appropriate_evidence"]
        if route == "image_only":
            target, findings = "REVIEW_REQUIRED", ["SOURCE_EVIDENCE_MISSING"]
        elif route == "mixed":
            target, findings = "REVIEW_REQUIRED", ["DOCUMENT_CONTENT_UNVERIFIED"]
        path = safe_path(original, name)
        case = dict(case_id=code, group="heldout", expected_route=route, expected_execution_state="COMPLETED",
                    eligibility=["A", "B", "C"], expected_decision=target, required_findings=findings,
                    labelled_absent=["bank_instructions.account", "bank_instructions.ifsc"], bank_instructions=None,
                    pdf={"path":name, "sha256":external["sha256"], "page_count":1, "byte_count":path.stat().st_size},
                    **{key: printed[key] for key in ("vendor_name", "invoice_number", "invoice_date", "po_reference", "currency", "net", "tax", "gross")},
                    lines=[dict(item_code=line["item_code"], description=line["description"], qty=str(line["quantity"]),
                                unit_price_net=line["unit_net_price"], net=line["line_net"]) for line in printed["lines"]])
        if external["human_review"] and target == "REVIEW_REQUIRED":
            human = external["human_review"]
            case.update(expected_owner="AP" if human["owner"] == "AP invoice analyst" else human["owner"],
                        expected_next_action=human["next_action"])
            if route == "image_only":
                case["next_action_terms"] = [["scan", "source"], ["against the po", "native pdf", "supplier-issued"]]
            elif route == "mixed":
                case["expected_owner"] = "Accounts Payable"
                case["next_action_terms"] = [["rendered", "visual"], ["instruction", "terms", "content"]]
        cases.append(case)
    data = {"version":"heldout-v1", "cases":cases}
    registered_cases(data, original, split="heldout")
    json_new(registry, data)
    print("Independent oracle SHA-256:", digest((original / ORACLE).read_bytes()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--private-dir", required=True, type=Path)
    args = parser.parse_args()
    private = args.private_dir.resolve()
    if not private.is_relative_to((ROOT / "tmp").resolve()):
        raise ValueError("Private original files must stay under the ignored workspace tmp directory")
    if args.archive:
        unpack_archive(args.archive, private / "original", EXPECTED)
    register(private / "original", private / "registry.json")
