"""Atomic audited reassessment from stored extraction, original policy and current trusted authority."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.contracts import DecisionV1, PolicyV1, RunSnapshotV1, POCandidateV1
from app.db.models import InvoiceRun, ReviewAction
from app.domain import build_context
from app.domain.common import normalized
from app.domain.human_resolution import POConfirmation, InvalidConfirmation, evaluate_with_confirmed_po
from .repository import load_authority

DEMO_IDENTITY = 'Demo reviewer — identity not authenticated'


def fingerprint(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


class ReviewConflict(ValueError): pass
class ReviewUnavailable(ValueError): pass
class ReviewNotFound(ValueError): pass


class ReviewActionSnapshot(BaseModel):
    model_config=ConfigDict(frozen=True,extra='forbid')
    id: str
    source_run_id: str
    client_action_id: str
    action_type: Literal['CONFIRM_PO']='CONFIRM_PO'
    selected_po_id: str
    reviewer_label: str
    reviewer_identity: Literal['Demo reviewer — identity not authenticated']=DEMO_IDENTITY
    rationale: str
    created_at: datetime
    original_decision: DecisionV1
    reassessment: DecisionV1
    policy_snapshot: PolicyV1
    authority_fingerprint: str
    source_snapshot_fingerprint: str
    selection_provenance: str
    canonical_vendor_name: str


class ReviewHistory(BaseModel):
    actions: tuple[ReviewActionSnapshot,...]=()
    current_reviewed_assessment: DecisionV1 | None=None
    confirmation_available: bool=False
    unavailable_reason: str | None=None
    candidates: tuple[POCandidateV1,...]=()
    canonical_vendor_name: str | None=None
    authority_basis: str='Current authoritative procurement and billed records; source run recorded policy.'


def load_source(session,run_id):
    row=session.get(InvoiceRun,run_id)
    if row is None: raise ReviewNotFound()
    return RunSnapshotV1.model_validate({**row.payload,'stages':()})


def eligible_context(snapshot,authority):
    if (snapshot.execution_state!='COMPLETED' or snapshot.decision is None
            or snapshot.extracted_invoice is None or snapshot.policy_snapshot is None):
        raise ReviewUnavailable('Completed business analysis required')
    context=build_context(snapshot.extracted_invoice,*authority)
    if normalized(context.invoice.po_reference):
        raise ReviewUnavailable('An explicit invoice PO cannot be overridden')
    if context.canonical_vendor is None or not context.canonical_vendor.approved:
        raise ReviewUnavailable('Approved canonical supplier required')
    recorded_ids={c.po.id for c in snapshot.candidates}
    context=context.model_copy(update={'candidates':tuple(c for c in context.candidates if c.po.id in recorded_ids)})
    if not context.candidates: raise ReviewUnavailable('No retained authoritative PO candidates')
    return context


class ReviewService:
    def __init__(self,engine): self.engine=engine

    def history(self,run_id):
        with Session(self.engine) as session:
            snapshot=load_source(session,run_id)
            row=session.scalar(select(ReviewAction).where(ReviewAction.run_id==run_id))
            if row:
                action=ReviewActionSnapshot.model_validate(row.payload)
                return ReviewHistory(actions=(action,),current_reviewed_assessment=action.reassessment,
                    unavailable_reason='A confirmation has already been recorded',canonical_vendor_name=action.canonical_vendor_name)
            try:
                context=eligible_context(snapshot,load_authority(session))
            except ReviewUnavailable as error:
                return ReviewHistory(unavailable_reason=str(error))
            return ReviewHistory(confirmation_available=True,candidates=context.candidates,
                                 canonical_vendor_name=context.canonical_vendor.name)

    def confirm(self,run_id,*,po_id,reviewer_label,rationale,client_action_id):
        request_fingerprint=fingerprint({'po_id':po_id,'reviewer_label':reviewer_label,'rationale':rationale})
        with Session(self.engine) as session:
            # Serialize competing local/process requests before reading authority. No network work here.
            session.execute(text('BEGIN IMMEDIATE'))
            try:
                snapshot=load_source(session,run_id)
                existing=session.scalar(select(ReviewAction).where(ReviewAction.run_id==run_id))
                if existing:
                    if existing.client_action_id==client_action_id and existing.request_fingerprint==request_fingerprint:
                        return ReviewActionSnapshot.model_validate(existing.payload),False
                    raise ReviewConflict('A different confirmation is already recorded')
                authority=load_authority(session)
                context=eligible_context(snapshot,authority)
                if po_id not in {c.po.id for c in context.candidates}:
                    raise InvalidConfirmation('PO was not a retained deterministic candidate')
                decision=evaluate_with_confirmed_po(context,snapshot.policy_snapshot,POConfirmation(po_id,rationale))
                candidate=next(c for c in context.candidates if c.po.id==po_id)
                action=ReviewActionSnapshot(id=uuid4().hex,source_run_id=run_id,client_action_id=client_action_id,
                    selected_po_id=po_id,reviewer_label=reviewer_label,rationale=rationale,
                    created_at=datetime.now(timezone.utc),original_decision=snapshot.decision,reassessment=decision,
                    policy_snapshot=snapshot.policy_snapshot,
                    authority_fingerprint=fingerprint([[r.model_dump(mode='json') for r in group] for group in authority]),
                    source_snapshot_fingerprint=fingerprint(snapshot.model_dump(mode='json')),
                    selection_provenance='Audited human confirmation; '+candidate.selection_provenance,
                    canonical_vendor_name=context.canonical_vendor.name)
                session.add(ReviewAction(id=action.id,run_id=run_id,client_action_id=client_action_id,
                    request_fingerprint=request_fingerprint,payload=action.model_dump(mode='json')))
                session.commit()
                return action,True
            finally:
                session.rollback() # Also closes read-only idempotent paths; never partial audit rows.
