import copy
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest
import pymupdf
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.contracts import (ExtractedInvoiceV1, PolicyV1, EvaluationContextV1, FindingV1,
    DecisionV1, RunSnapshotV1, VendorV1, PurchaseOrderV1, PriorBilledInvoiceV1, EvidenceRefV1)
from app.db.models import Vendor, PurchaseOrder, POLine, PriorBilledInvoice, InvoiceRun, RunStage, PolicySnapshot
from app.db.seed import seed, MANIFEST
from app.db.session import create_db_engine, initialize
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
SOURCE = json.loads(MANIFEST.read_text())
CASES = {c['id']: c for c in json.loads((ROOT / 'data/fixture_manifest.json').read_text())['fixture_cases']}

@pytest.fixture
def engine(tmp_path):
    db = create_db_engine(tmp_path / 'test.db')
    initialize(db)
    seed(db)
    yield db
    db.dispose()

def snapshot(engine):
    with Session(engine) as s:
        return {m.__tablename__: [dict(r._mapping) for r in s.execute(select(m.__table__).order_by(m.id))]
                for m in [Vendor, PurchaseOrder, POLine, PriorBilledInvoice]}

def test_exact_manifest_and_decimal_storage(engine):
    with Session(engine) as s:
        for model, contract, key in [(Vendor, VendorV1, 'vendors'), (PurchaseOrder, PurchaseOrderV1, 'purchase_orders'), (PriorBilledInvoice, PriorBilledInvoiceV1, 'prior_billed_invoices')]:
            actual = {r.id: contract.model_validate(r.payload) for r in s.scalars(select(model))}
            assert actual == {r['id']: contract.model_validate(r) for r in SOURCE[key]}
        assert len(list(s.scalars(select(POLine)))) == 7
        for record in SOURCE['purchase_orders']:
            po = s.get(PurchaseOrder, record['id'])
            assert po.vendor_id == record['vendor_id']
            assert po.authorized_net == Decimal(record['authorized_net'])
            assert isinstance(po.authorized_net, Decimal)
            for line in record['lines']:
                row = s.get(POLine, record['id'] + ':' + line['item_code'])
                for name in ['ordered_qty','unit_price_net','authorized_net']:
                    assert getattr(row, name) == Decimal(line[name])
        for record in SOURCE['prior_billed_invoices']:
            assert s.get(PriorBilledInvoice, record['id']).net == Decimal(record['net'])
        assert s.execute(text('SELECT typeof(authorized_net) FROM purchase_order')).scalars().all() == ['text'] * 7
        assert s.get(Vendor, 'V-MER').payload['aliases'] == ['Meridian Cloud Ltd.']

@pytest.mark.parametrize('po_id,net,qty', [('PO-1042','80000','16'),('PO-1057','180000','30'),('PO-2010','25000','25'),('PO-3015','25000','5'),('PO-4002','100000','10'),('PO-5001','80000','8'),('PO-6001','50000','50')])
def test_authoritative_remaining_values(engine, po_id, net, qty):
    # Oracle arithmetic, not a Phase 2 eligibility engine.
    with Session(engine) as s:
        po = PurchaseOrderV1.model_validate(s.get(PurchaseOrder, po_id).payload)
        history = [PriorBilledInvoiceV1.model_validate(b.payload) for b in s.scalars(select(PriorBilledInvoice).where(PriorBilledInvoice.po_id == po_id))]
        assert po.authorized_net - sum((b.net for b in history), Decimal(0)) == Decimal(net)
        for line in po.lines:
            prior_qty = sum((bl.qty for b in history for bl in b.lines if bl.item_code == line.item_code), Decimal(0))
            assert line.ordered_qty - prior_qty == Decimal(qty)

def test_repeated_seed_unchanged(engine):
    before = snapshot(engine)
    assert seed(engine) == seed(engine) == {'vendors':6,'purchase_orders':7,'prior_billed_invoices':3}
    assert snapshot(engine) == before

def test_seed_drift_rejected_atomically(engine, tmp_path):
    altered = copy.deepcopy(SOURCE)
    altered['vendors'].insert(0, {'id':'V-NEW','name':'Synthetic rollback test','aliases':[],'approved':True})
    altered['purchase_orders'][0]['authorized_net'] = '1'
    manifest = tmp_path / 'drift.json'
    manifest.write_text(json.dumps(altered))
    before = snapshot(engine)
    with pytest.raises(ValueError, match='Authoritative seed drift'):
        seed(engine, manifest)
    assert snapshot(engine) == before

def test_analysis_lifecycle_has_no_ledger_side_effects(engine):
    before = snapshot(engine)
    now = datetime.now(timezone.utc)
    run = RunSnapshotV1(id='test-run', execution_state='QUEUED', document_id='synthetic-doc', created_at=now, updated_at=now)
    policy = PolicyV1()
    with Session(engine) as s, s.begin():
        s.add(PolicySnapshot(version=policy.version, payload=policy.model_dump(mode='json')))
        s.add(InvoiceRun(id=run.id, payload=run.model_dump(mode='json')))
        s.flush()
        s.add(RunStage(id='stage', run_id=run.id, payload={'name':'Received','state':'PASSED'}))
    assert snapshot(engine) == before
    with Session(engine) as s, s.begin():
        row = s.get(InvoiceRun, run.id)
        row.payload = RunSnapshotV1.model_validate({**row.payload,'execution_state':'PROCESSING_FAILED'}).model_dump(mode='json')
    assert snapshot(engine) == before
    with Session(engine) as s, s.begin():
        s.delete(s.get(RunStage, 'stage')); s.flush()
        s.delete(s.get(InvoiceRun, run.id))
    assert snapshot(engine) == before
    for model in [InvoiceRun, RunStage, PolicySnapshot]:
        assert not {f.column.table.name for f in model.__table__.foreign_keys} & {'prior_billed_invoice','purchase_order','po_line'}

def test_contracts_nulls_policy_and_unknown_findings():
    invoice = ExtractedInvoiceV1()
    assert invoice.net is None and invoice.tax is None and invoice.total is None
    policy = PolicyV1()
    assert policy.price_tolerance_pct == Decimal('0.02')
    assert policy.amount_rounding_allowance == Decimal('1.00')
    assert policy.commitment_overrun_allowance == Decimal('0.00')
    with pytest.raises(ValidationError):
        policy.price_tolerance_pct = Decimal('0.05')
    context = EvaluationContextV1(invoice=invoice)
    assert context.canonical_vendor is None and context.selected_po is None
    finding = FindingV1(code='FUTURE_CODE', severity='REVIEW', title='Review', explanation='New rule', source_type='policy')
    decision = DecisionV1(outcome='REVIEW_REQUIRED', findings=(finding,), policy_version=policy.version)
    now = datetime.now(timezone.utc)
    run = RunSnapshotV1(id='r', document_id='d', execution_state='COMPLETED', decision=decision, policy_snapshot=policy, created_at=now, updated_at=now)
    assert RunSnapshotV1.model_validate_json(run.model_dump_json()) == run
    assert EvidenceRefV1(field='net').evidence_state == 'MISSING'

@pytest.mark.parametrize('value', [0.1, True, 'NaN', 'Infinity'])
def test_invalid_financial_values_rejected(value):
    with pytest.raises(ValidationError):
        ExtractedInvoiceV1(net=value)

@pytest.mark.parametrize('state', ['QUEUED','RUNNING','PROCESSING_FAILED','INTERRUPTED'])
def test_incomplete_or_failed_run_cannot_hold_decision(state):
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        RunSnapshotV1(id='r', document_id='d', execution_state=state, decision=DecisionV1(outcome='BLOCKED', policy_version='policy-v1'), created_at=now, updated_at=now)

def test_completed_run_requires_decision_and_policy():
    now = datetime.now(timezone.utc)
    fields = dict(id='r', document_id='d', execution_state='COMPLETED', created_at=now, updated_at=now)
    with pytest.raises(ValidationError):
        RunSnapshotV1(**fields)
    with pytest.raises(ValidationError):
        RunSnapshotV1(**fields, decision=DecisionV1(outcome='BLOCKED', policy_version='missing'))

@pytest.mark.parametrize('case_id', ['HAPPY_CLEAN','HAPPY_PARTIAL','OVERBILLED_PARTIAL','DUPLICATE_REISSUED'])
def test_real_native_text_pdf_matches_oracle(case_id):
    case = CASES[case_id]
    path = ROOT / 'tests/fixtures' / case['filename']
    assert path.read_bytes().startswith(b'%PDF-')
    with pymupdf.open(path) as pdf:
        assert len(pdf) == 1 and not pdf.is_encrypted
        assert not pdf[0].get_images()
        txt = ' '.join(pdf[0].get_text().split())
        expected = ['SYNTHETIC DEMO',case['vendor_name'],case['invoice_number'],case['invoice_date'],case['po_reference'],case['currency'],'Net subtotal: INR ' + case['net'],'Tax (synthetic GST): INR ' + case['tax'],'Invoice total: INR ' + case['gross']]
        for line in case['lines']:
            expected += [line['description'],line['item_code'],'Quantity: ' + line['qty'],'Unit price (net): INR ' + line['unit_price_net']]
        for token in expected:
            assert token in txt

def test_health_and_repeat_startup(tmp_path):
    path = tmp_path / 'startup.db'
    for _ in range(2):
        with TestClient(create_app(path)) as client:
            response = client.get('/api/health')
            assert response.status_code == 200
            assert response.json() == {'status':'ok','service':'ap-compass','version':'0.1.0','database':'ok'}
            # Phase 4 adds uploads; a request without multipart content is rejected.
            assert client.post('/api/runs').status_code == 415
    engine = create_db_engine(path)
    try:
        assert len(snapshot(engine)['prior_billed_invoice']) == 3
    finally:
        engine.dispose()

@pytest.mark.parametrize('case_id', ['HAPPY_CLEAN','HAPPY_PARTIAL','OVERBILLED_PARTIAL','DUPLICATE_REISSUED'])
def test_representative_extracted_contract(case_id):
    case = CASES[case_id]
    invoice = ExtractedInvoiceV1(vendor_name_raw=case['vendor_name'], invoice_number=case['invoice_number'], invoice_date=case['invoice_date'], po_reference=case['po_reference'], currency=case['currency'], net=case['net'], tax=case['tax'], total=case['gross'], lines=case['lines'])
    assert invoice.net == Decimal(case['net'])
    assert invoice.total == Decimal(case['gross'])
    assert invoice.lines[0].net is None  # Never infer a missing extracted amount.
    assert ExtractedInvoiceV1.model_validate_json(invoice.model_dump_json()) == invoice
