"""TEST_ONLY provider facts for human-resolution PDF integration; not live Gemini results."""
from decimal import Decimal
import json
from pathlib import Path
from app.documents.pipeline import extract_pdf
from test_document_engine import FakeProvider

ROOT=Path(__file__).resolve().parents[2]
CASES={c['id']:c for c in json.loads((ROOT/'data/human_resolution_manifest.json').read_text())['fixture_cases']}
CASES.update({c['id']:c for c in json.loads((ROOT/'data/fixture_manifest.json').read_text())['fixture_cases'] if c['id']=='AMBIGUOUS_PO'})


def wire(case_id):
    case=CASES[case_id]
    out={k:case[k] for k in ('invoice_number','invoice_date','po_reference','currency','net','tax')}
    out.update(vendor_name_raw=case['vendor_name'],total=case['gross'],bank_instructions=None,
               lines=[{**line,'net':None} for line in case['lines']],evidence=[])
    labels={'vendor_name_raw':None,'invoice_number':'Invoice number:', 'invoice_date':'Invoice date:',
            'po_reference':'Purchase order:','currency':'Currency:', 'net':'Net subtotal: INR',
            'tax':'Tax (synthetic GST): INR','total':'Invoice total: INR'}
    for key,label in labels.items():
        value=out[key]
        if value is not None: out['evidence'].append({'field':key,'raw_value':value,'page':1,'quote':value if label is None else f'{label} {value}'})
    for index,line in enumerate(out['lines']):
        for key,label in (('description',None),('item_code','Item code:'),('qty','Quantity:'),('unit_price_net','Unit price (net): INR')):
            if line[key] is not None: out['evidence'].append({'field':f'lines[{index}].{key}','raw_value':line[key],'page':1,'quote':line[key] if label is None else f'{label} {line[key]}'})
    return out


class ReviewExtractor:
    def __init__(self): self.calls=0
    async def __call__(self,raw):
        import pymupdf
        with pymupdf.open(stream=raw,filetype='pdf') as pdf: text=''.join(p.get_text() for p in pdf)
        name=next(name for name in CASES if CASES[name]['invoice_number'] in text)
        self.calls+=1
        return await extract_pdf(raw,FakeProvider([json.dumps(wire(name))],model='TEST_ONLY-review-provider'),max_attempts=1)
