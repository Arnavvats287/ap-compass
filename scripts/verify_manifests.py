#!/usr/bin/env python3
"""Validate the static synthetic fixture oracle (not implementation or PDF tests)."""
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
seed = json.loads((ROOT / 'data/seed_manifest.json').read_text())
fixtures = json.loads((ROOT / 'data/fixture_manifest.json').read_text())
D = Decimal
assert len(seed['vendors']) == 6
assert len(seed['purchase_orders']) == 7
assert len(seed['prior_billed_invoices']) == 3
assert len(fixtures['fixture_cases']) == 10
vendor_ids = {v['id'] for v in seed['vendors']}
pos = {p['id']: p for p in seed['purchase_orders']}
assert len(pos) == len(seed['purchase_orders'])
for p in pos.values():
    assert p['vendor_id'] in vendor_ids
    assert sum(D(line['ordered_qty'])*D(line['unit_price_net']) for line in p['lines']) == D(p['authorized_net']), p['id']
    assert sum(D(line['authorized_net']) for line in p['lines']) == D(p['authorized_net']), p['id']
prior = {}
for b in seed['prior_billed_invoices']:
    assert b['po_id'] in pos
    assert pos[b['po_id']]['vendor_id'] == b['vendor_id']
    assert sum(D(line['qty'])*D(line['unit_price_net']) for line in b['lines']) == D(b['net']), b['id']
    assert D(b['net']) + D(b['tax']) == D(b['gross']), b['id']
    prior[b['po_id']] = prior.get(b['po_id'],D(0)) + D(b['net'])
remaining = {po_id: D(p['authorized_net']) - prior.get(po_id,D(0)) for po_id,p in pos.items()}
assert remaining['PO-1042'] == D('80000')
assert remaining['PO-3015'] == D('25000')
assert remaining['PO-2010'] == D('25000')
assert remaining['PO-6001'] == D('50000')
cases = {c['id']: c for c in fixtures['fixture_cases']}
assert len(cases) == len(fixtures['fixture_cases'])
for case in cases.values():
    if all(line.get('qty') is not None and line.get('unit_price_net') is not None for line in case.get('lines',[])):
        net_lines = sum(D(line['qty'])*D(line['unit_price_net']) for line in case['lines'])
        assert net_lines == D(case['net']), case['id']
    if case['id'] == 'SCAN_CONFLICT':
        assert D(case['net'])+D(case['tax']) != D(case['gross'])
    else:
        assert D(case['net'])+D(case['tax']) == D(case['gross']), case['id']
assert remaining['PO-3015'] - D(cases['OVERBILLED_PARTIAL']['net']) == D('-5000')
assert D(cases['HAPPY_PARTIAL']['net']) <= remaining['PO-1042']
assert D(cases['PRICE_3PCT']['net']) <= remaining['PO-2010']
assert (D(cases['PRICE_3PCT']['lines'][0]['unit_price_net']) / D('1000') - 1) == D('0.03')
print(f"STATIC ORACLE PASS: {len(seed['vendors'])} vendors, {len(pos)} POs, {len(seed['prior_billed_invoices'])} billed records, {len(cases)} cases")
for po_id in ['PO-1042','PO-3015','PO-2010','PO-6001']:
    print(f"  {po_id} remaining net: INR {remaining[po_id]}")
print('Note: no PDFs, Gemini calls, application tests, deployment or runtime behavior verified.')
