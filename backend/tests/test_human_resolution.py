"""Trusted human identity override only; invoice facts/evidence are synthetic oracle test data."""
from datetime import date
from decimal import Decimal
import pytest
from app.contracts import PolicyV1
from app.domain import build_context, evaluate
from app.domain.human_resolution import POConfirmation, InvalidConfirmation, evaluate_with_confirmed_po
from test_finance_engine import facts, evidence_for, VENDORS, POS, HISTORY, codes


def missing_invoice():
    return evidence_for(facts('HAPPY_PARTIAL').model_copy(update={
        'invoice_number':'MISSING_PO_VALID-2026', 'invoice_date':date(2026,11,18),
        'po_reference':None, 'net':Decimal('10000'),
        'tax':Decimal('1800'), 'total':Decimal('11800'),
        'lines':(facts('HAPPY_PARTIAL').lines[0].model_copy(update={'qty':Decimal('2'), 'net':None}),),
    }))


def ctx(invoice):
    return build_context(invoice, VENDORS, POS, HISTORY)


def test_complete_missing_po_ready_only_after_confirmation():
    context=ctx(missing_invoice()); policy=PolicyV1(); original=evaluate(context,policy)
    assert original.outcome=='REVIEW_REQUIRED' and 'PO_REFERENCE_MISSING' in codes(original)
    result=evaluate_with_confirmed_po(context,policy,POConfirmation('PO-1042','Checked the vendor order and agreed service scope.'))
    assert result.outcome=='READY_FOR_AP'
    assert evaluate(context,policy)==original
    assert context.invoice.po_reference is None
    assert result==evaluate_with_confirmed_po(context,policy,POConfirmation('PO-1042','Checked the vendor order and agreed service scope.'))


def test_ambiguous_po_missing_line_facts_remain_review():
    context=ctx(facts('AMBIGUOUS_PO')); before=context.model_dump()
    result=evaluate_with_confirmed_po(context,PolicyV1(),POConfirmation('PO-1042','Verified intended order with Procurement.'))
    assert result.outcome=='REVIEW_REQUIRED'
    assert {'CRITICAL_FIELD_MISSING','LINE_MAPPING_UNRESOLVED'} <= codes(result)
    assert not {'PO_AMBIGUOUS','PO_REFERENCE_MISSING'} & codes(result)
    assert context.model_dump()==before


@pytest.mark.parametrize('po', ['PO-3015','DOES-NOT-EXIST'])
def test_cross_vendor_or_nonexistent_po_rejected(po):
    with pytest.raises(InvalidConfirmation):
        evaluate_with_confirmed_po(ctx(missing_invoice()),PolicyV1(),POConfirmation(po,'Valid analyst rationale.'))


def test_explicit_po_cannot_be_overridden_even_by_same_po():
    with pytest.raises(InvalidConfirmation):
        evaluate_with_confirmed_po(ctx(facts('HAPPY_PARTIAL')),PolicyV1(),POConfirmation('PO-1042','Valid analyst rationale.'))


@pytest.mark.parametrize('case,po,required', [
    ('OVERBILLED_PARTIAL','PO-3015',{'PO_BALANCE_EXCEEDED','PO_QUANTITY_EXCEEDED'}),
    ('DUPLICATE_REISSUED','PO-2010',{'EXACT_DUPLICATE'}),
])
def test_human_identity_never_bypasses_hard_controls(case,po,required):
    invoice=evidence_for(facts(case).model_copy(update={'po_reference':None}))
    result=evaluate_with_confirmed_po(ctx(invoice),PolicyV1(),POConfirmation(po,'Verified invoice relates to this order.'))
    assert result.outcome=='BLOCKED' and required<=codes(result)


def test_uncertain_evidence_not_promoted():
    invoice=missing_invoice(); invoice=invoice.model_copy(update={'evidence':tuple(r.model_copy(update={'evidence_state':'SOURCE_LOCATED_UNVERIFIED'}) for r in invoice.evidence)})
    before=invoice.model_dump()
    result=evaluate_with_confirmed_po(ctx(invoice),PolicyV1(),POConfirmation('PO-1042','Verified order identity only.'))
    assert result.outcome=='REVIEW_REQUIRED' and 'SOURCE_EVIDENCE_MISSING' in codes(result)
    assert invoice.model_dump()==before


def test_unapproved_vendor_and_missing_rationale_rejected():
    context=ctx(missing_invoice())
    for invalid in ('', '   ', None):
        with pytest.raises(InvalidConfirmation):
            evaluate_with_confirmed_po(context,PolicyV1(),POConfirmation('PO-1042',invalid))
    context=context.model_copy(update={'canonical_vendor':context.canonical_vendor.model_copy(update={'approved':False})})
    with pytest.raises(InvalidConfirmation):
        evaluate_with_confirmed_po(context,PolicyV1(),POConfirmation('PO-1042','Valid rationale.'))


def test_forged_candidate_set_is_rederived():
    context=ctx(missing_invoice()).model_copy(update={'candidates':()})
    assert evaluate_with_confirmed_po(context,PolicyV1(),POConfirmation('PO-1042','Checked authoritative candidate.')).outcome=='READY_FOR_AP'
    # Forged candidate cannot add a cross-vendor PO.
    context=context.model_copy(update={'candidates':(build_context(facts('OVERBILLED_PARTIAL'),VENDORS,POS,HISTORY).candidates[0],)})
    with pytest.raises(InvalidConfirmation):
        evaluate_with_confirmed_po(context,PolicyV1(),POConfirmation('PO-3015','Valid rationale.'))
