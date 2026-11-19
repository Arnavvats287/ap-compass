"""Bounded API-local policy simulation; no policy editing or persistent decision writes."""
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, field_validator

from app.contracts import Amount, DecisionV1, PolicyV1
from app.orchestration.policy_preview import preview, PreviewUnavailable

router = APIRouter(prefix='/api')


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    price_tolerance_pct: Amount

    @field_validator('price_tolerance_pct')
    @classmethod
    def allowed(cls, value):
        if value not in (Decimal('0.02'), Decimal('0.05')):
            raise ValueError('Choose 0.02 or 0.05')
        return Decimal('0.02') if value == Decimal('0.02') else Decimal('0.05')


class PreviewResponse(BaseModel):
    original_policy: PolicyV1
    preview_policy: PolicyV1
    original_decision: DecisionV1
    preview_decision: DecisionV1
    changed: bool


@router.post('/runs/{run_id}/policy-preview', response_model=PreviewResponse)
def policy_preview(run_id: str, body: PreviewRequest, request: Request):
    repository = request.app.state.runs.repository
    snapshot = repository.load(run_id)
    if snapshot is None:
        raise HTTPException(404, 'Run not found')
    try:
        policy, decision, changed = preview(snapshot, repository, body.price_tolerance_pct)
    except PreviewUnavailable:
        raise HTTPException(409, 'Policy preview requires a completed business analysis') from None
    except ValueError:
        raise HTTPException(503, 'Policy preview is unavailable: trusted records could not be evaluated') from None
    return PreviewResponse(original_policy=snapshot.policy_snapshot, preview_policy=policy,
                           original_decision=snapshot.decision, preview_decision=decision, changed=changed)
