"""Read-only policy API tests. Oracle invoice facts are explicitly synthetic test data."""
import asyncio
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select, event

from app.contracts import PolicyV1
from app.db.models import InvoiceRun, RunStage, PolicySnapshot
from app.domain import build_context, evaluate
from app.main import create_app
from test_finance_engine import facts
from test_orchestration_api import authority, Extractor, upload


def rows(engine):
    with engine.connect() as connection:
        return {model.__tablename__: tuple(tuple(row) for row in connection.execute(
            select(model.__table__).order_by(list(model.__table__.primary_key)[0])))
            for model in (InvoiceRun, RunStage, PolicySnapshot)}


def completed(app, case):
    repo = app.state.runs.repository
    invoice = facts(case)  # TEST oracle evidence, not a production extraction.
    policy = repo.policy(PolicyV1())
    context = build_context(invoice, *repo.authority())
    decision = evaluate(context, policy)
    snapshot = repo.create('a' * 32)
    repo.update(snapshot.id, execution_state='COMPLETED', extracted_invoice=invoice,
                policy_snapshot=policy, decision=decision, candidates=context.candidates,
                stages={name: 'PASSED' for name in ('extracting_invoice', 'matching_records',
                        'evaluating_controls', 'finalizing')})
    return snapshot.id


@pytest.mark.parametrize('case,expected,code', [
    ('PRICE_3PCT', 'READY_FOR_AP', None),
    ('OVERBILLED_PARTIAL', 'BLOCKED', 'PO_BALANCE_EXCEEDED'),
    ('DUPLICATE_REISSUED', 'BLOCKED', 'EXACT_DUPLICATE'),
])
def test_preview_policy_and_no_writes_or_model_calls(tmp_path, case, expected, code):
    async def scenario():
        async def forbidden(*args, **kwargs):
            pytest.fail('Policy preview must never extract a document')
        app = create_app(tmp_path/'db.sqlite', document_dir=tmp_path/'docs', extractor=forbidden)
        async with app.router.lifespan_context(app):
            run_id = completed(app, case)
            before, history = rows(app.state.engine), authority(app.state.engine)
            def read_only(connection, cursor, statement, parameters, context, many):
                assert statement.lstrip().upper().startswith('SELECT'), 'Preview attempted a SQL write'
            event.listen(app.state.engine, 'before_cursor_execute', read_only)
            app.state.runs.documents.read = lambda *_: pytest.fail('Preview read a PDF')
            original = app.state.runs.repository.load(run_id).model_dump(mode='json')
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                current = (await client.get('/api/policy')).json()
                strict = await client.post(f'/api/runs/{run_id}/policy-preview', json={'price_tolerance_pct':'0.02'})
                relaxed = await client.post(f'/api/runs/{run_id}/policy-preview', json={'price_tolerance_pct':'0.05'})
                assert strict.status_code == relaxed.status_code == 200
                a, b = strict.json(), relaxed.json()
                assert a['original_decision'] == b['original_decision'] == original['decision']
                assert a['preview_decision']['outcome'] == original['decision']['outcome']
                assert b['preview_decision']['outcome'] == expected
                assert a['changed'] is False
                assert b['changed'] is (case == 'PRICE_3PCT')
                if case == 'PRICE_3PCT':
                    assert a['preview_decision']['primary_reason_code'] == 'PRICE_VARIANCE'
                if code:
                    assert code in {f['code'] for f in b['preview_decision']['findings']}
                if case == 'OVERBILLED_PARTIAL':
                    assert 'PO_QUANTITY_EXCEEDED' in {f['code'] for f in b['preview_decision']['findings']}
                assert b['preview_policy']['price_tolerance_pct'] == '0.05'
                assert b['preview_policy']['require_explicit_po'] is True
                assert b['preview_policy']['commitment_overrun_allowance'] == '0.00'
                assert (await client.post(f'/api/runs/{run_id}/policy-preview', json={'price_tolerance_pct':'0.05'})).json() == b
                assert (await client.get(f'/api/runs/{run_id}')).json() == original
                assert (await client.get('/api/policy')).json() == current
            assert rows(app.state.engine) == before  # Run JSON, stages AND policy rows.
            assert authority(app.state.engine) == history
    asyncio.run(scenario())


@pytest.mark.parametrize('value', ['0.03', '0', '-0.02', 'NaN', 'Infinity', '', None, 0.05, 2, True, {}, []])
def test_invalid_tolerances_rejected(tmp_path, value):
    async def scenario():
        app = create_app(tmp_path/'db.sqlite', document_dir=tmp_path/'docs')
        async with app.router.lifespan_context(app):
            run_id = completed(app, 'PRICE_3PCT')
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                assert (await client.post(f'/api/runs/{run_id}/policy-preview', json={'price_tolerance_pct':value})).status_code == 422
    asyncio.run(scenario())


def test_unknown_incomplete_failed_and_extra_fields(tmp_path):
    async def scenario():
        app = create_app(tmp_path/'db.sqlite', document_dir=tmp_path/'docs')
        async with app.router.lifespan_context(app):
            repo = app.state.runs.repository
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                body = {'price_tolerance_pct':'0.05'}
                assert (await client.post('/api/runs/unknown/policy-preview', json=body)).status_code == 404
                for state in ('QUEUED', 'RUNNING', 'PROCESSING_FAILED', 'INTERRUPTED'):
                    snapshot = repo.create('a'*32)
                    repo.update(snapshot.id, execution_state=state)
                    assert (await client.post(f'/api/runs/{snapshot.id}/policy-preview', json=body)).status_code == 409
                run_id = completed(app, 'PRICE_3PCT')
                assert (await client.post(f'/api/runs/{run_id}/policy-preview', json={**body, 'require_explicit_po':False})).status_code == 422
    asyncio.run(scenario())


def test_preview_uses_decimal_and_validated_policy():
    from app.api.policy_preview import PreviewRequest
    assert PreviewRequest(price_tolerance_pct='0.05').price_tolerance_pct == Decimal('0.05')
    assert isinstance(PreviewRequest(price_tolerance_pct='0.02').price_tolerance_pct, Decimal)
    assert str(PreviewRequest(price_tolerance_pct='0.050').price_tolerance_pct) == '0.05'


def test_price_pdf_actual_pipeline_then_preview(tmp_path):
    async def scenario():
        import pymupdf
        from test_document_engine import ROOT
        raw = (ROOT/'tests/fixtures/PRICE_3PCT.pdf').read_bytes()
        with pymupdf.open(stream=raw, filetype='pdf') as pdf:
            assert len(pdf) == 1
            text = pdf[0].get_text()
            for printed in ('1030', '10300', '1854', '12154'):
                assert printed in text
        extractor = Extractor('PRICE_3PCT')
        app = create_app(tmp_path/'db.sqlite', document_dir=tmp_path/'docs', extractor=extractor)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                run_id = (await upload(client, 'PRICE_3PCT')).json()['run_id']
                await app.state.runs.idle()
                original = (await client.get(f'/api/runs/{run_id}')).json()
                assert original['decision']['outcome'] == 'REVIEW_REQUIRED'
                assert original['decision']['primary_reason_code'] == 'PRICE_VARIANCE'
                response = await client.post(f'/api/runs/{run_id}/policy-preview', json={'price_tolerance_pct':'0.05'})
                assert response.json()['preview_decision']['outcome'] == 'READY_FOR_AP'
                assert extractor.calls == len(extractor.provider.calls) == 1
                assert (await client.get(f'/api/runs/{run_id}')).json() == original
    asyncio.run(scenario())


def test_preview_loads_current_trusted_authority(tmp_path):
    from sqlalchemy.orm import Session
    from app.db.models import PurchaseOrder
    async def scenario():
        app = create_app(tmp_path/'db.sqlite', document_dir=tmp_path/'docs')
        async with app.router.lifespan_context(app):
            run_id = completed(app, 'PRICE_3PCT')
            original = app.state.runs.repository.load(run_id)
            # TEST ONLY: emulate an authoritative PO status update after the recorded analysis.
            with Session(app.state.engine) as session, session.begin():
                row = session.get(PurchaseOrder, 'PO-2010')
                row.payload = {**row.payload, 'status':'CLOSED'}
            before = authority(app.state.engine)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                response = await client.post(f'/api/runs/{run_id}/policy-preview',json={'price_tolerance_pct':'0.05'})
                assert response.status_code == 200
                assert response.json()['preview_decision']['outcome'] == 'BLOCKED'
                assert 'PO_CLOSED' in {f['code'] for f in response.json()['preview_decision']['findings']}
            assert authority(app.state.engine) == before
            assert app.state.runs.repository.load(run_id) == original
    asyncio.run(scenario())
