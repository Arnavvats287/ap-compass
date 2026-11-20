"""Audited review API, immutable storage and real PDF/fake-provider end-to-end tests."""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select,text,event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.contracts import PolicyV1
from app.db.models import InvoiceRun,RunStage,ReviewAction,PolicySnapshot,Base
from app.db.session import create_db_engine,initialize
from app.db.seed import seed
from app.main import create_app
from app.orchestration.reviews import ReviewService,ReviewConflict
from app.domain import build_context,evaluate
from test_finance_engine import facts
from test_human_resolution import missing_invoice
from test_orchestration_api import authority,upload
from test_policy_preview import rows
from review_fixtures import ROOT,ReviewExtractor


def complete(app,invoice=None,policy=None):
    repo=app.state.runs.repository; invoice=invoice or missing_invoice(); policy=policy or PolicyV1()
    repo.policy(policy); context=build_context(invoice,*repo.authority()); snapshot=repo.create('a'*32)
    repo.update(snapshot.id,execution_state='COMPLETED',extracted_invoice=invoice,policy_snapshot=policy,
                decision=evaluate(context,policy),candidates=context.candidates,
                stages={name:'PASSED' for name in ('extracting_invoice','matching_records','evaluating_controls','finalizing')})
    return snapshot.id


def body(po='PO-1042',**changes):
    return {'po_id':po,'reviewer_label':'Demo AP analyst','rationale':'Checked intended purchase order with Procurement.',
            'client_action_id':str(uuid4()),**changes}


@pytest.mark.parametrize('case,expected', [('MISSING_PO_VALID','READY_FOR_AP'),('AMBIGUOUS_PO','REVIEW_REQUIRED')])
def test_real_pdf_upload_review_restart_and_immutability(tmp_path,monkeypatch,case,expected):
    async def scenario():
        extractor=ReviewExtractor(); path=tmp_path/'db.sqlite'; docs=tmp_path/'docs'
        app=create_app(path,document_dir=docs,extractor=extractor)
        async with app.router.lifespan_context(app):
            baseline_authority=authority(app.state.engine)
            raw=(ROOT/'tests/fixtures/human_resolution'/f'{case}.pdf').read_bytes()
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                run_id=(await upload(client,data=raw)).json()['run_id']; await app.state.runs.idle()
                original=(await client.get('/api/runs/'+run_id)).json()
                assert original['decision']['outcome']=='REVIEW_REQUIRED'
                if case=='AMBIGUOUS_PO': assert 'PO_AMBIGUOUS' in {f['code'] for f in original['decision']['findings']}
                else: assert all(r['evidence_state']=='NATIVE_VERIFIED' for r in original['extracted_invoice']['evidence'] if r['normalized_value'] is not None)
                before=rows(app.state.engine); dashboard=(await client.get('/api/dashboard')).json()
                def forbidden(*args,**kwargs): pytest.fail('Reassessment must not parse or extract a PDF')
                monkeypatch.setattr('app.documents.inspection.inspect_pdf',forbidden)
                monkeypatch.setattr('pymupdf.open',forbidden)
                monkeypatch.setattr('app.ai.gemini.genai.Client',forbidden)
                app.state.runs.documents.read=forbidden
                writes=[]
                def sql_trace(conn,cursor,statement,parameters,context,many):
                    if statement.lstrip().upper().startswith(('INSERT','UPDATE','DELETE')): writes.append(statement)
                event.listen(app.state.engine,'before_cursor_execute',sql_trace)
                history=(await client.get(f'/api/runs/{run_id}/review-history')).json()
                assert history['confirmation_available'] and {c['po']['id'] for c in history['candidates']}=={'PO-1042','PO-1057'}
                request=body(); response=await client.post(f'/api/runs/{run_id}/po-confirmations',json=request)
                assert response.status_code==201,response.text
                action=response.json(); assert action['reassessment']['outcome']==expected
                assert action['reviewer_identity']=='Demo reviewer — identity not authenticated'
                assert action['policy_snapshot']==original['policy_snapshot']
                assert len(action['authority_fingerprint'])==64 and action['created_at'].endswith('Z')
                assert action['original_decision']==original['decision']
                codes={f['code'] for f in action['reassessment']['findings']}
                assert not {'PO_AMBIGUOUS','PO_REFERENCE_MISSING'} & codes
                if case=='AMBIGUOUS_PO': assert {'CRITICAL_FIELD_MISSING','LINE_MAPPING_UNRESOLVED'}<=codes
                duplicate=await client.post(f'/api/runs/{run_id}/po-confirmations',json=request)
                assert duplicate.status_code==200 and duplicate.json()==action
                assert (await client.get(f'/api/runs/{run_id}/review-history')).json()['actions']==[action]
                assert (await client.get('/api/runs/'+run_id)).json()==original
                assert (await client.get('/api/dashboard')).json()==dashboard
                # Existing price preview still uses original automated facts and no human override.
                preview=await client.post(f'/api/runs/{run_id}/policy-preview',json={'price_tolerance_pct':'0.05'})
                assert preview.status_code==200 and preview.json()['preview_decision']['outcome']=='REVIEW_REQUIRED'
                assert rows(app.state.engine)==before
                assert authority(app.state.engine)==baseline_authority
                assert writes and all('INSERT INTO review_action' in q for q in writes)
                assert extractor.calls==1
        app2=create_app(path,document_dir=docs,extractor=extractor)
        async with app2.router.lifespan_context(app2):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app2),base_url='http://test') as client:
                assert (await client.get('/api/runs/'+run_id)).json()==original
                assert (await client.get(f'/api/runs/{run_id}/review-history')).json()['actions']==[action]
                assert (await client.get(f'/api/runs/{run_id}/document')).content==raw
                assert extractor.calls==1
                assert authority(app2.state.engine)==baseline_authority
    asyncio.run(scenario())


@pytest.mark.parametrize('changes',[{'rationale':''},{'rationale':'short'},{'rationale':'x'*2001},
    {'reviewer_label':''},{'reviewer_label':123},{'reviewer_label':'x'*81},{'reviewer_label':'bad\x00label'},
    {'po_id':'../PO-1042'},{'client_action_id':'bad-key'},{'approved':True},{'po':{}}])
def test_invalid_inputs_no_action(tmp_path,changes):
    async def scenario():
        app=create_app(tmp_path/'db')
        async with app.router.lifespan_context(app):
            run_id=complete(app)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                response=await client.post(f'/api/runs/{run_id}/po-confirmations',json=body(**changes))
                assert response.status_code==422
                assert (await client.get(f'/api/runs/{run_id}/review-history')).json()['actions']==[]
    asyncio.run(scenario())


def test_unknown_explicit_incomplete_invalid_po_and_request_bounds(tmp_path):
    async def scenario():
        app=create_app(tmp_path/'db')
        async with app.router.lifespan_context(app):
            repo=app.state.runs.repository
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                assert (await client.get('/api/runs/unknown/review-history')).status_code==404
                assert (await client.post('/api/runs/unknown/po-confirmations',json=body())).status_code==404
                for state in ('QUEUED','RUNNING','PROCESSING_FAILED','INTERRUPTED'):
                    snapshot=repo.create('a'*32);repo.update(snapshot.id,execution_state=state)
                    assert (await client.post(f'/api/runs/{snapshot.id}/po-confirmations',json=body())).status_code==409
                explicit=complete(app,facts('HAPPY_PARTIAL'))
                assert (await client.post(f'/api/runs/{explicit}/po-confirmations',json=body())).status_code==409
                valid=complete(app)
                for po in ('PO-3015','PO-NONEXISTENT'):
                    assert (await client.post(f'/api/runs/{valid}/po-confirmations',json=body(po))).status_code==422
                url=f'/api/runs/{valid}/po-confirmations'
                assert (await client.post(url,content=b'x'*8193,headers={'Content-Type':'application/json'})).status_code==413
                assert (await client.post(url,content=b'bad',headers={'Content-Type':'application/json'})).status_code==422
                assert (await client.post(url,content=b'{}',headers={'Content-Type':'text/plain'})).status_code==415
    asyncio.run(scenario())


def test_conflicting_and_concurrent_confirmations_first_wins(tmp_path):
    async def scenario():
        app=create_app(tmp_path/'db')
        async with app.router.lifespan_context(app):
            run_id=complete(app,facts('AMBIGUOUS_PO'))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                a,b=body('PO-1042'),body('PO-1057')
                responses=await asyncio.gather(client.post(f'/api/runs/{run_id}/po-confirmations',json=a),client.post(f'/api/runs/{run_id}/po-confirmations',json=b))
                assert sorted(r.status_code for r in responses)==[201,409]
                winner=next(r for r in responses if r.status_code==201).json()
                chosen=a if winner['selected_po_id']==a['po_id'] else b
                assert (await client.post(f'/api/runs/{run_id}/po-confirmations',json={**chosen,'rationale':'Changed rationale under same action key.'})).status_code==409
                assert len((await client.get(f'/api/runs/{run_id}/review-history')).json()['actions'])==1
    asyncio.run(scenario())


def test_append_only_and_atomic_rollback_original_policy_current_authority(tmp_path,monkeypatch):
    async def scenario():
        app=create_app(tmp_path/'db')
        async with app.router.lifespan_context(app):
            run_id=complete(app,policy=PolicyV1(version='recorded-special',price_tolerance_pct='0.02'))
            service=ReviewService(app.state.engine); original=app.state.runs.repository.load(run_id)
            def failure(*a,**k): raise ValueError('DO_NOT_LEAK sensitive internal failure')
            with monkeypatch.context() as m:
                m.setattr('app.orchestration.reviews.evaluate_with_confirmed_po',failure)
                with pytest.raises(ValueError): service.confirm(run_id,**body())
            assert service.history(run_id).actions==()
            app.state.runs.current_policy=PolicyV1(version='new-active',price_tolerance_pct='0.05')
            action,_=service.confirm(run_id,**body())
            assert action.policy_snapshot==original.policy_snapshot
            assert action.reassessment.policy_version=='recorded-special'
            for statement in ('UPDATE review_action SET client_action_id=client_action_id','DELETE FROM review_action','INSERT OR REPLACE INTO review_action SELECT * FROM review_action'):
                with pytest.raises(IntegrityError):
                    with app.state.engine.begin() as c:c.execute(text(statement))
            assert service.history(run_id).actions==(action,)
    asyncio.run(scenario())


def test_additive_migration_on_populated_old_database(tmp_path):
    engine=create_db_engine(tmp_path/'old.db')
    Base.metadata.create_all(engine,tables=[t for t in Base.metadata.sorted_tables if t.name!='review_action'])
    seed(engine)
    from app.orchestration.repository import RunRepository
    repo=RunRepository(engine); run_id=repo.create('a'*32).id
    before=authority(engine),rows(engine)
    with engine.begin() as c:
        c.execute(text('ALTER TABLE invoice_run DROP COLUMN document_sha256'))
    initialize(engine);initialize(engine)
    assert (authority(engine),rows(engine))==before
    with engine.connect() as c:
        assert c.execute(text('SELECT version FROM schema_migration ORDER BY version')).scalars().all()==[
            '002-human-po-review', '003-upload-fingerprint',
        ]
        assert c.execute(text('SELECT document_sha256 FROM invoice_run WHERE id=:id'), {'id': run_id}).scalar() is None
        assert c.execute(text('SELECT COUNT(*) FROM review_action')).scalar()==0
    engine.dispose()


def test_current_authority_used_and_source_candidates_cannot_be_expanded(tmp_path):
    from app.db.models import PurchaseOrder,Vendor
    async def scenario():
        app=create_app(tmp_path/'db')
        async with app.router.lifespan_context(app):
            run_id=complete(app); before=app.state.runs.repository.load(run_id)
            # TEST ONLY authoritative status change after extraction. Review must use the current master.
            with Session(app.state.engine) as session,session.begin():
                row=session.get(PurchaseOrder,'PO-1042'); row.payload={**row.payload,'status':'CLOSED'}
            authority_before=authority(app.state.engine)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                result=await client.post(f'/api/runs/{run_id}/po-confirmations',json=body())
                assert result.status_code==201
                assert result.json()['reassessment']['outcome']=='BLOCKED'
                assert 'PO_CLOSED' in {f['code'] for f in result.json()['reassessment']['findings']}
                assert app.state.runs.repository.load(run_id)==before
                assert authority(app.state.engine)==authority_before
                limited=complete(app)
                source=app.state.runs.repository.load(limited)
                app.state.runs.repository.update(limited,candidates=tuple(c for c in source.candidates if c.po.id=='PO-1042'))
                assert (await client.post(f'/api/runs/{limited}/po-confirmations',json=body('PO-1057'))).status_code==422
                # A canonical but no-longer-approved vendor cannot be confirmed.
                unapproved=complete(app)
                with Session(app.state.engine) as session,session.begin():
                    row=session.get(Vendor,'V-MER');row.payload={**row.payload,'approved':False}
                assert (await client.post(f'/api/runs/{unapproved}/po-confirmations',json=body())).status_code==409
    asyncio.run(scenario())


def test_sensitive_input_and_internal_errors_not_echoed_or_logged(tmp_path,monkeypatch,caplog):
    async def scenario():
        app=create_app(tmp_path/'db')
        async with app.router.lifespan_context(app):
            run_id=complete(app)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                secret='SYNTHETIC_SECRET_ACCOUNT_999999'
                invalid=await client.post(f'/api/runs/{run_id}/po-confirmations',json=body(reviewer_label=secret+'\x00'))
                assert invalid.status_code==422 and secret not in invalid.text
                for error_type in (ValueError,RuntimeError):
                    def fail(*args,**kwargs):raise error_type(secret)
                    monkeypatch.setattr('app.orchestration.reviews.evaluate_with_confirmed_po',fail)
                    response=await client.post(f'/api/runs/{run_id}/po-confirmations',json=body())
                    assert response.status_code==503 and secret not in response.text+caplog.text
                    assert (await client.get(f'/api/runs/{run_id}/review-history')).json()['actions']==[]
    asyncio.run(scenario())
