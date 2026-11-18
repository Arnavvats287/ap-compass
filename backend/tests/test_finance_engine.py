"""Synthetic facts from the immutable oracle, NOT Gemini/PDF extraction results."""
import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.contracts import (
    EvidenceRefV1, ExtractedInvoiceV1, InvoiceLineV1, PolicyV1,
    PriorBilledInvoiceV1, PurchaseOrderV1, VendorV1,
)
from app.domain.matching import build_context, resolve_vendor
from app.domain.decisions import evaluate

ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / "data/seed_manifest.json").read_text())
CASES = {c["id"]: c for c in json.loads((ROOT / "data/fixture_manifest.json").read_text())["fixture_cases"]}
VENDORS = tuple(VendorV1.model_validate(v) for v in SEED["vendors"])
POS = tuple(PurchaseOrderV1.model_validate(p) for p in SEED["purchase_orders"])
HISTORY = tuple(PriorBilledInvoiceV1.model_validate(b) for b in SEED["prior_billed_invoices"])


def evidence_for(invoice, *, unverified=False):
    """Explicit test oracle assertion. Production adapters must verify real sources."""
    fields = {
        "vendor_name_raw": invoice.vendor_name_raw,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date,
        "po_reference": invoice.po_reference,
        "currency": invoice.currency,
        "net": invoice.net, "tax": invoice.tax, "total": invoice.total,
    }
    for index, line in enumerate(invoice.lines):
        for name in ("item_code", "qty", "unit_price_net", "net"):
            fields[f"lines[{index}].{name}"] = getattr(line, name)
    if invoice.bank_instructions is not None:
        for name in ("account", "ifsc"):
            fields[f"bank_instructions.{name}"] = getattr(invoice.bank_instructions, name)
    evidence = tuple(EvidenceRefV1(
        field=name, raw_value=str(value), normalized_value=str(value), page=1,
        quote=f"SYNTHETIC ORACLE: {name}: {value}",
        route="image_only" if unverified else "native_text",
        evidence_state="SOURCE_LOCATED_UNVERIFIED" if unverified else "NATIVE_VERIFIED",
    ) for name, value in fields.items() if value is not None)
    return invoice.model_copy(update={"evidence": evidence})


def facts(case_id):
    case = CASES[case_id]
    invoice = ExtractedInvoiceV1(
        vendor_name_raw=case["vendor_name"], invoice_number=case["invoice_number"],
        invoice_date=case["invoice_date"], po_reference=case["po_reference"],
        currency=case["currency"], net=case["net"], tax=case["tax"], total=case["gross"],
        lines=tuple(InvoiceLineV1.model_validate(line) for line in case["lines"]),
        bank_instructions=case.get("bank_instructions"),
    )
    return evidence_for(invoice, unverified=case["document_route"] == "image_only")


def context_for(case_id, **kwargs):
    return build_context(facts(case_id), kwargs.get("vendors", VENDORS),
                         kwargs.get("pos", POS), kwargs.get("history", HISTORY))


def codes(decision):
    return {f.code for f in decision.findings}


@pytest.mark.parametrize("case_id", CASES)
def test_fixture_oracle(case_id):
    context = context_for(case_id)
    decision = evaluate(context, PolicyV1())
    assert decision.outcome == CASES[case_id]["expected_decision"]
    assert set(CASES[case_id]["required_reason_codes"]) <= codes(decision)
    for finding in decision.findings:
        if finding.severity in ("BLOCK", "REVIEW"):
            assert finding.owner and finding.next_action
    assert decision == evaluate(context, PolicyV1())


def test_price_policy_change_only():
    context = context_for("PRICE_3PCT")
    strict = evaluate(context, PolicyV1())
    relaxed = evaluate(context, PolicyV1(version="policy-v2", price_tolerance_pct="0.05"))
    assert strict.outcome == "REVIEW_REQUIRED"
    assert relaxed.outcome == "READY_FOR_AP"
    assert codes(strict) - codes(relaxed) == {"PRICE_VARIANCE"}


def test_explicit_overbilled_po_is_retained():
    context = context_for("OVERBILLED_PARTIAL")
    assert context.selected_po.id == "PO-3015"
    assert "explicit" in context.selection_provenance.lower()
    decision = evaluate(context, PolicyV1(price_tolerance_pct="0.05"))
    assert {"PO_BALANCE_EXCEEDED", "PO_QUANTITY_EXCEEDED"} <= codes(decision)
    assert "PO_NOT_FOUND" not in codes(decision)
    balance = next(f for f in decision.findings if f.code == "PO_BALANCE_EXCEEDED")
    assert dict((v.name, v.value) for v in balance.values)["excess_net"] == "5000"


def test_ambiguity_is_not_arbitrary():
    context = context_for("AMBIGUOUS_PO")
    assert context.selected_po is None
    assert {c.po.id for c in context.candidates} == {"PO-1042", "PO-1057"}
    assert all(c.selection_provenance for c in context.candidates)
    assert evaluate(context, PolicyV1(require_explicit_po=False)).outcome == "REVIEW_REQUIRED"


def test_vendor_alias_but_not_fuzzy_similarity():
    assert resolve_vendor(" Meridian Cloud Ltd. ", VENDORS).id == "V-MER"
    assert resolve_vendor("Meridian Clouds Ltd.", VENDORS) is None


def context_from(invoice, *, vendors=VENDORS, pos=POS, history=HISTORY):
    return build_context(invoice, vendors, pos, history)


@pytest.mark.parametrize("field", ["net", "tax", "total", "invoice_number", "invoice_date", "currency", "vendor_name_raw"])
def test_missing_critical_fact_never_ready_or_zero(field):
    invoice = evidence_for(facts("HAPPY_CLEAN").model_copy(update={field: None}))
    before = invoice.model_dump_json()
    decision = evaluate(context_from(invoice), PolicyV1())
    assert decision.outcome != "READY_FOR_AP"
    assert "CRITICAL_FIELD_MISSING" in codes(decision)
    assert getattr(invoice, field) is None
    assert invoice.model_dump_json() == before


@pytest.mark.parametrize("field", ["qty", "unit_price_net"])
def test_missing_line_financial_fact_never_becomes_zero(field):
    invoice = facts("HAPPY_CLEAN")
    line = invoice.lines[0].model_copy(update={field: None})
    invoice = evidence_for(invoice.model_copy(update={"lines": (line,)}))
    assert evaluate(context_from(invoice), PolicyV1()).outcome == "REVIEW_REQUIRED"
    assert getattr(invoice.lines[0], field) is None


def test_known_po_is_independent_of_balance_and_tolerance():
    context = context_for("OVERBILLED_PARTIAL")
    original = evaluate(context, PolicyV1())
    for qty in ("36", "39", "40", "41"):
        billed = HISTORY[1]
        line = billed.lines[0].model_copy(update={"qty": Decimal(qty), "line_net": Decimal(qty) * 5000})
        net = line.line_net
        updated = billed.model_copy(update={"lines": (line,), "net": net, "tax": net * Decimal("0.18"), "gross": net * Decimal("1.18")})
        history = tuple(updated if b.id == billed.id else b for b in HISTORY)
        lowered = context_for("OVERBILLED_PARTIAL", history=history)
        assert lowered.selected_po == context.selected_po
        result = evaluate(lowered, PolicyV1(price_tolerance_pct="1.00"))
        assert result.outcome == original.outcome == "BLOCKED"
        assert "PO_BALANCE_EXCEEDED" in codes(result)


@pytest.mark.parametrize("tolerance", ["0.00", "0.02", "0.05", "1.00"])
def test_exact_duplicate_survives_every_tolerance(tolerance):
    assert evaluate(context_for("DUPLICATE_REISSUED"), PolicyV1(price_tolerance_pct=tolerance)).outcome == "BLOCKED"


def test_vendor_po_contradiction_cannot_be_ranked_away():
    invoice = evidence_for(facts("HAPPY_CLEAN").model_copy(update={"vendor_name_raw": "Aster Systems"}))
    context = context_from(invoice)
    assert context.selected_po.id == "PO-6001"
    decision = evaluate(context, PolicyV1(price_tolerance_pct="1.00"))
    assert decision.outcome == "BLOCKED"
    assert "VENDOR_PO_CONFLICT" in codes(decision)


def test_supplied_normalized_vendor_name_cannot_override_source_identity():
    invoice = facts("UNKNOWN_VENDOR").model_copy(update={"vendor_name_normalized": "Orion Office Products"})
    assert "VENDOR_UNVERIFIED" in codes(evaluate(context_from(invoice), PolicyV1()))


def test_alias_collisions_require_review():
    other = VENDORS[-1].model_copy(update={"aliases": ("Meridian Cloud Ltd.",)})
    vendors = (*VENDORS[:-1], other)
    assert resolve_vendor("Meridian Cloud Ltd.", vendors) is None
    assert evaluate(context_for("HAPPY_PARTIAL", vendors=vendors), PolicyV1()).outcome == "REVIEW_REQUIRED"


def test_unapproved_vendor_is_not_ready():
    vendors = tuple(v.model_copy(update={"approved": False}) if v.id == "V-ORI" else v for v in VENDORS)
    decision = evaluate(context_for("HAPPY_CLEAN", vendors=vendors), PolicyV1())
    assert decision.outcome == "REVIEW_REQUIRED"
    assert "VENDOR_UNVERIFIED" in codes(decision)


@pytest.mark.parametrize("status", ["CLOSED", "CANCELLED", "UNKNOWN", ""])
def test_nonopen_po_is_identified_then_blocked(status):
    pos = tuple(p.model_copy(update={"status": status}) if p.id == "PO-6001" else p for p in POS)
    context = context_for("HAPPY_CLEAN", pos=pos)
    assert context.selected_po.id == "PO-6001"
    assert "PO_CLOSED" in codes(evaluate(context, PolicyV1()))


def test_currency_conflict_blocks_without_cross_currency_money_comparison():
    invoice = evidence_for(facts("HAPPY_CLEAN").model_copy(update={"currency": "USD"}))
    decision = evaluate(context_from(invoice), PolicyV1())
    assert decision.outcome == "BLOCKED"
    assert "CURRENCY_MISMATCH" in codes(decision)
    assert "PO_BALANCE_EXCEEDED" not in codes(decision)


@pytest.mark.parametrize("code", [None, "", "NOT-AN-AUTHORIZED-ITEM"])
def test_unmapped_line_cannot_pass(code):
    invoice = facts("HAPPY_CLEAN")
    line = invoice.lines[0].model_copy(update={"item_code": code})
    invoice = evidence_for(invoice.model_copy(update={"lines": (line,)}))
    decision = evaluate(context_from(invoice), PolicyV1())
    assert decision.outcome != "READY_FOR_AP"
    assert "LINE_MAPPING_UNRESOLVED" in codes(decision)


def test_split_lines_are_aggregated_for_quantity_and_commitment():
    invoice = facts("OVERBILLED_PARTIAL")
    line = invoice.lines[0].model_copy(update={"qty": Decimal("3")})
    invoice = evidence_for(invoice.model_copy(update={"lines": (line, line)}))
    decision = evaluate(context_from(invoice), PolicyV1())
    assert {"PO_QUANTITY_EXCEEDED", "PO_BALANCE_EXCEEDED", "PO_LINE_BALANCE_EXCEEDED"} <= codes(decision)
    qty = next(f for f in decision.findings if f.code == "PO_QUANTITY_EXCEEDED")
    assert {v.name: v.value for v in qty.values}["excess_qty"] == "1"


@pytest.mark.parametrize("unit_price,outcome", [("1020", "READY_FOR_AP"), ("1020.0001", "REVIEW_REQUIRED"), ("980", "READY_FOR_AP"), ("979.9999", "REVIEW_REQUIRED")])
def test_price_tolerance_boundary_is_inclusive(unit_price, outcome):
    invoice = facts("PRICE_3PCT")
    price = Decimal(unit_price)
    net = invoice.lines[0].qty * price
    line = invoice.lines[0].model_copy(update={"unit_price_net": price})
    invoice = evidence_for(invoice.model_copy(update={"lines": (line,), "net": net, "tax": net * Decimal("0.18"), "total": net * Decimal("1.18")}))
    assert evaluate(context_from(invoice), PolicyV1()).outcome == outcome


@pytest.mark.parametrize("difference,outcome", [("1.00", "READY_FOR_AP"), ("1.01", "REVIEW_REQUIRED"), ("-1.00", "READY_FOR_AP"), ("-1.01", "REVIEW_REQUIRED")])
def test_header_rounding_allowance_boundary(difference, outcome):
    invoice = facts("HAPPY_CLEAN")
    invoice = evidence_for(invoice.model_copy(update={"total": invoice.total + Decimal(difference)}))
    assert evaluate(context_from(invoice), PolicyV1()).outcome == outcome


def test_policy_cannot_allow_commitment_overrun():
    with pytest.raises(ValueError, match="hard ceiling"):
        evaluate(context_for("OVERBILLED_PARTIAL"), PolicyV1(commitment_overrun_allowance="5000"))


@pytest.mark.parametrize("changes", [{"evidence": ()}, {"lines": ()}])
def test_empty_evidence_or_lines_requires_review(changes):
    invoice = facts("HAPPY_CLEAN").model_copy(update=changes)
    assert evaluate(context_from(invoice), PolicyV1()).outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("change", [{"evidence_state": "MISSING"}, {"evidence_state": "SOURCE_LOCATED_UNVERIFIED"}, {"quote": None}, {"page": None}, {"raw_value": None}, {"normalized_value": "999"}, {"route": "image_only"}])
def test_untrustworthy_critical_evidence_not_promoted(change):
    invoice = facts("HAPPY_CLEAN")
    refs = tuple(e.model_copy(update=change) if e.field == "net" else e for e in invoice.evidence)
    invoice = invoice.model_copy(update={"evidence": refs})
    assert "SOURCE_EVIDENCE_MISSING" in codes(evaluate(context_from(invoice), PolicyV1()))
    assert invoice.evidence == refs


def test_conflicting_duplicate_evidence_refs_require_review():
    invoice = facts("HAPPY_CLEAN")
    ref = next(e for e in invoice.evidence if e.field == "net")
    invoice = invoice.model_copy(update={"evidence": (*invoice.evidence, ref)})
    assert evaluate(context_from(invoice), PolicyV1()).outcome == "REVIEW_REQUIRED"


def test_scan_remains_review_even_with_arithmetic_corrected():
    invoice = facts("SCAN_CONFLICT")
    invoice = evidence_for(invoice.model_copy(update={"total": invoice.net + invoice.tax}), unverified=True)
    decision = evaluate(context_from(invoice), PolicyV1())
    assert decision.outcome == "REVIEW_REQUIRED"
    assert "SOURCE_EVIDENCE_MISSING" in codes(decision)
    assert "TOTAL_RECONCILIATION_FAILED" not in codes(decision)


def test_no_bank_instructions_is_not_mismatch():
    decision = evaluate(context_for("HAPPY_CLEAN"), PolicyV1())
    assert "BANK_DETAILS_NOT_PROVIDED" in codes(decision)
    assert "BANK_DETAILS_MISMATCH" not in codes(decision)
    assert decision.outcome == "READY_FOR_AP"


def test_matching_verified_bank_details_pass_without_leaking_account():
    invoice = facts("BANK_CHANGED")
    vendor = next(v for v in VENDORS if v.id == "V-BRI")
    invoice = evidence_for(invoice.model_copy(update={"bank_instructions": vendor.verified_bank}))
    result = evaluate(context_from(invoice), PolicyV1())
    assert result.outcome == "READY_FOR_AP"
    assert vendor.verified_bank.account not in result.model_dump_json()


def test_uncertain_bank_details_are_not_a_verified_contradiction():
    invoice = facts("BANK_CHANGED")
    refs = tuple(e.model_copy(update={"evidence_state": "SOURCE_LOCATED_UNVERIFIED"}) if e.field.startswith("bank_instructions.") else e for e in invoice.evidence)
    invoice = invoice.model_copy(update={"evidence": refs})
    result = evaluate(context_from(invoice), PolicyV1())
    assert result.outcome == "REVIEW_REQUIRED"
    assert "BANK_DETAILS_UNVERIFIED" in codes(result)
    assert "BANK_DETAILS_MISMATCH" not in codes(result)


def test_payment_instructions_without_verified_master_require_review():
    vendors = tuple(v.model_copy(update={"verified_bank": None}) if v.id == "V-BRI" else v for v in VENDORS)
    result = evaluate(context_for("BANK_CHANGED", vendors=vendors), PolicyV1())
    assert result.outcome == "REVIEW_REQUIRED"
    assert "BANK_MASTER_UNVERIFIED" in codes(result)


def test_possible_duplicate_number_variant_requires_review():
    invoice = evidence_for(facts("DUPLICATE_REISSUED").model_copy(update={"invoice_number": "NS20260318"}))
    decision = evaluate(context_from(invoice), PolicyV1())
    assert decision.outcome == "REVIEW_REQUIRED"
    assert "POSSIBLE_DUPLICATE" in codes(decision)
    assert "EXACT_DUPLICATE" not in codes(decision)


def test_possible_duplicate_business_facts_requires_review():
    from datetime import date
    invoice = evidence_for(facts("DUPLICATE_REISSUED").model_copy(update={"invoice_number": "NEW-DISTINCT-NUMBER", "invoice_date": date(2026, 10, 16)}))
    decision = evaluate(context_from(invoice), PolicyV1())
    assert decision.outcome == "REVIEW_REQUIRED"
    assert "POSSIBLE_DUPLICATE" in codes(decision)


def test_unknown_rule_code_needs_no_aggregator_rewrite():
    from app.domain.common import finding
    from app.domain.decisions import evaluate_with_rules
    def new_rule(context, policy):
        return (finding("FUTURE_REVIEW_CODE", "REVIEW", "New control", "Additional review is needed."),)
    context = context_for("HAPPY_CLEAN")
    base = evaluate(context, PolicyV1())
    result = evaluate_with_rules(context, PolicyV1(), (new_rule,))
    assert result.outcome == "REVIEW_REQUIRED"
    assert result.primary_reason_code == "FUTURE_REVIEW_CODE"
    assert result.findings[:-1] == base.findings


def test_rule_failure_propagates_without_business_decision():
    from app.domain.decisions import evaluate_with_rules
    def broken_rule(context, policy):
        raise RuntimeError("Synthetic rule failure")
    with pytest.raises(RuntimeError, match="Synthetic rule failure"):
        evaluate_with_rules(context_for("HAPPY_CLEAN"), PolicyV1(), (broken_rule,))


def test_forged_selected_po_cannot_increase_authorization():
    from app.domain.validation import InvalidEvaluationContext
    context = context_for("OVERBILLED_PARTIAL")
    forged = context.selected_po.model_copy(update={"authorized_net": Decimal("9999999")})
    with pytest.raises(InvalidEvaluationContext):
        evaluate(context.model_copy(update={"selected_po": forged}), PolicyV1())


def test_supplied_selection_cannot_hide_ambiguous_po():
    from app.contracts import POCandidateV1
    context = context_for("AMBIGUOUS_PO")
    po = next(p for p in POS if p.id == "PO-1042")
    context = context.model_copy(update={"selected_po": po, "candidates": (POCandidateV1(po=po, selection_provenance="unsupported claim", rank=1),), "selection_provenance": "claimed confirmation"})
    assert "PO_AMBIGUOUS" in codes(evaluate(context, PolicyV1(require_explicit_po=False)))


def test_missing_explicit_po_cannot_fall_back_to_another_vendor_po():
    invoice = evidence_for(facts("HAPPY_PARTIAL").model_copy(update={"po_reference": "PO-DOES-NOT-EXIST"}))
    context = context_from(invoice)
    assert context.selected_po is None
    assert "PO_NOT_FOUND" in codes(evaluate(context, PolicyV1()))


def test_missing_po_unique_scope_requires_review_under_initial_policy():
    invoice = evidence_for(facts("HAPPY_PARTIAL").model_copy(update={"po_reference": None}))
    context = context_from(invoice)
    assert context.selected_po.id == "PO-1042"
    assert {c.po.id for c in context.candidates} == {"PO-1042", "PO-1057"}
    assert evaluate(context, PolicyV1()).outcome == "REVIEW_REQUIRED"
    assert evaluate(context, PolicyV1(require_explicit_po=False)).outcome == "READY_FOR_AP"


def test_input_order_and_ambient_decimal_context_do_not_change_decision():
    from decimal import localcontext
    invoice = facts("PRICE_3PCT")
    a = context_from(invoice)
    b = context_from(invoice, pos=tuple(reversed(POS)), history=tuple(reversed(HISTORY)), vendors=tuple(reversed(VENDORS)))
    expected = evaluate(a, PolicyV1())
    with localcontext() as caller:
        caller.prec = 2
        assert evaluate(b, PolicyV1()) == expected


def test_snapshots_unchanged_across_repeated_evaluation():
    contexts = tuple(context_for(case_id) for case_id in CASES)
    before = tuple(c.model_dump_json() for c in contexts)
    ledger_before = tuple(b.model_dump_json() for b in HISTORY)
    for context in contexts:
        for tolerance in ("0.02", "0.05"):
            evaluate(context, PolicyV1(price_tolerance_pct=tolerance))
    assert tuple(c.model_dump_json() for c in contexts) == before
    assert tuple(b.model_dump_json() for b in HISTORY) == ledger_before


def test_engine_has_no_io_dependencies():
    import ast
    prohibited = {"sqlalchemy", "fastapi", "httpx", "requests", "socket", "subprocess", "pathlib", "os", "google", "pymupdf", "app.db", "app.ai", "app.documents"}
    for path in (ROOT / "backend/app/domain").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(name == banned or name.startswith(banned + ".") for name in names for banned in prohibited)


def test_price_boundary_preserves_all_supplied_decimal_digits():
    from decimal import localcontext
    invoice = facts("PRICE_3PCT")
    price = Decimal("1020." + "0" * 60 + "1")
    with localcontext() as precision:
        precision.prec = 150
        net = invoice.lines[0].qty * price
        line = invoice.lines[0].model_copy(update={"unit_price_net": price})
        invoice = evidence_for(invoice.model_copy(update={"lines": (line,), "net": net, "tax": net * Decimal("0.18"), "total": net * Decimal("1.18")}))
    decision = evaluate(context_from(invoice), PolicyV1())
    assert "PRICE_VARIANCE" in codes(decision)
    assert decision.outcome == "REVIEW_REQUIRED"


def test_engine_preserves_seeded_sqlite_and_snapshot_history(tmp_path, monkeypatch):
    import hashlib
    import socket
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.db.models import Vendor, PurchaseOrder, POLine, PriorBilledInvoice
    from app.db.session import create_db_engine, initialize
    from app.db.seed import seed
    path = tmp_path / "finance-isolation.db"
    db = create_db_engine(path)
    try:
        initialize(db)
        seed(db)
        models = (Vendor, PurchaseOrder, POLine, PriorBilledInvoice)
        def rows():
            with Session(db) as session:
                return {m.__tablename__: [dict(r._mapping) for r in session.execute(select(m.__table__).order_by(m.id))] for m in models}
        before = rows()
        with Session(db) as session:
            vendors = tuple(VendorV1.model_validate(v.payload) for v in session.scalars(select(Vendor)))
            pos = tuple(PurchaseOrderV1.model_validate(p.payload) for p in session.scalars(select(PurchaseOrder)))
            history = tuple(PriorBilledInvoiceV1.model_validate(b.payload) for b in session.scalars(select(PriorBilledInvoice)))
        contexts = tuple(build_context(facts(case_id), vendors, pos, history) for case_id in CASES)
        snapshots = tuple(c.model_dump_json() for c in contexts)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        def forbidden(*args, **kwargs):
            raise AssertionError("Financial evaluation attempted database or network access")
        with monkeypatch.context() as patch:
            patch.setattr(Session, "execute", forbidden)
            patch.setattr(socket, "socket", forbidden)
            for context in contexts:
                for tolerance in ("0.02", "0.05"):
                    evaluate(context, PolicyV1(price_tolerance_pct=tolerance))
        assert rows() == before
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        assert tuple(c.model_dump_json() for c in contexts) == snapshots
        print("LEDGER ISOLATION PASS: 20 evaluations; 6 vendors, 7 POs/lines, 3 billed rows unchanged; SQLite SHA256=" + digest)
    finally:
        db.dispose()


@pytest.mark.parametrize("change", [{"net": Decimal("-1")}, {"tax": Decimal("-1")}, {"total": Decimal("0")}])
def test_invalid_header_amounts_require_review(change):
    invoice = evidence_for(facts("HAPPY_CLEAN").model_copy(update=change))
    result = evaluate(context_from(invoice), PolicyV1())
    assert result.outcome != "READY_FOR_AP"
    assert "FINANCIAL_VALUE_INVALID" in codes(result)


@pytest.mark.parametrize("change", [{"qty": Decimal("0")}, {"qty": Decimal("-1")}, {"unit_price_net": Decimal("-1")}, {"net": Decimal("-1")}])
def test_invalid_line_amounts_require_review(change):
    invoice = facts("HAPPY_CLEAN")
    line = invoice.lines[0].model_copy(update=change)
    invoice = evidence_for(invoice.model_copy(update={"lines": (line,)}))
    assert "FINANCIAL_VALUE_INVALID" in codes(evaluate(context_from(invoice), PolicyV1()))


def test_stated_line_net_must_reconcile_to_qty_price_and_invoice_net():
    invoice = facts("HAPPY_CLEAN")
    line = invoice.lines[0].model_copy(update={"net": Decimal("47900")})
    invoice = evidence_for(invoice.model_copy(update={"lines": (line,)}))
    decision = evaluate(context_from(invoice), PolicyV1())
    assert decision.outcome == "REVIEW_REQUIRED"
    assert "LINE_TOTAL_RECONCILIATION_FAILED" in codes(decision)


def test_exact_invoice_number_is_scoped_to_canonical_vendor():
    invoice = evidence_for(facts("HAPPY_CLEAN").model_copy(update={"invoice_number": "NS-2026-0318"}))
    decision = evaluate(context_from(invoice), PolicyV1())
    assert decision.outcome == "READY_FOR_AP"
    assert "EXACT_DUPLICATE" not in codes(decision)


@pytest.mark.parametrize("days,outcome", [(7, "REVIEW_REQUIRED"), (8, "READY_FOR_AP")])
def test_possible_duplicate_window_boundary(days, outcome):
    from datetime import timedelta
    invoice = facts("DUPLICATE_REISSUED")
    prior = next(b for b in HISTORY if b.vendor_id == "V-NOR")
    invoice = evidence_for(invoice.model_copy(update={"invoice_number": "DISTINCT-NUMBER", "invoice_date": prior.invoice_date + timedelta(days=days)}))
    assert evaluate(context_from(invoice), PolicyV1()).outcome == outcome


@pytest.mark.parametrize("qty,outcome", [("16", "READY_FOR_AP"), ("16.0000001", "BLOCKED")])
def test_remaining_quantity_and_net_hard_boundary(qty, outcome):
    invoice = facts("HAPPY_PARTIAL")
    qty = Decimal(qty)
    line = invoice.lines[0].model_copy(update={"qty": qty})
    net = qty * line.unit_price_net
    invoice = evidence_for(invoice.model_copy(update={"lines": (line,), "net": net, "tax": net * Decimal("0.18"), "total": net * Decimal("1.18")}))
    result = evaluate(context_from(invoice), PolicyV1())
    assert result.outcome == outcome
    if outcome == "BLOCKED":
        assert {"PO_BALANCE_EXCEEDED", "PO_QUANTITY_EXCEEDED"} <= codes(result)


def test_five_percent_price_policy_cannot_bypass_net_commitment():
    # Explicit regression projection of seed history, never a seed/master edit.
    billed = next(b for b in HISTORY if b.vendor_id == "V-NOR")
    line = billed.lines[0].model_copy(update={"qty": Decimal("20"), "line_net": Decimal("20000")})
    billed = billed.model_copy(update={"lines": (line,), "net": Decimal("20000"), "tax": Decimal("3600"), "gross": Decimal("23600")})
    history = tuple(billed if b.id == billed.id else b for b in HISTORY)
    result = evaluate(context_for("PRICE_3PCT", history=history), PolicyV1(price_tolerance_pct="0.05"))
    assert result.outcome == "BLOCKED"
    assert "PO_BALANCE_EXCEEDED" in codes(result)
    assert "PRICE_VARIANCE" not in codes(result)


def test_direct_independent_reconciliation_rules():
    from app.domain.reconciliation import remaining_commitment, remaining_quantities, unit_price_tolerance
    from app.domain.evidence import source_evidence
    context = context_for("OVERBILLED_PARTIAL")
    assert [f.code for f in remaining_commitment(context, PolicyV1())] == ["PO_BALANCE_EXCEEDED"]
    assert [f.code for f in remaining_quantities(context, PolicyV1())] == ["PO_QUANTITY_EXCEEDED"]
    price = context_for("PRICE_3PCT")
    assert [f.code for f in unit_price_tolerance(price, PolicyV1())] == ["PRICE_VARIANCE"]
    assert unit_price_tolerance(price, PolicyV1(price_tolerance_pct="0.05")) == ()
    assert source_evidence(context_for("HAPPY_CLEAN"), PolicyV1()) == ()


@pytest.mark.parametrize("broken", ["duplicate_po", "duplicate_billed_id", "billed_vendor", "billed_currency", "billed_arithmetic", "po_arithmetic"])
def test_invalid_authority_raises_no_business_decision(broken):
    from app.domain.validation import InvalidEvaluationContext
    context = context_for("HAPPY_CLEAN")
    if broken == "duplicate_po":
        context = context.model_copy(update={"procurement_records": (*context.procurement_records, context.procurement_records[0])})
    elif broken == "duplicate_billed_id":
        context = context.model_copy(update={"prior_billed_records": (*HISTORY, HISTORY[0])})
    elif broken.startswith("billed_"):
        field, value = {"billed_vendor": ("vendor_id", "V-ORI"), "billed_currency": ("currency", "USD"), "billed_arithmetic": ("gross", Decimal("1"))}[broken]
        history = (HISTORY[0].model_copy(update={field: value}), *HISTORY[1:])
        context = context.model_copy(update={"prior_billed_records": history})
    else:
        pos = tuple(p.model_copy(update={"authorized_net": Decimal("1")}) if p.id == "PO-1042" else p for p in POS)
        context = context_for("HAPPY_CLEAN", pos=pos)
    with pytest.raises(InvalidEvaluationContext):
        evaluate(context, PolicyV1())
