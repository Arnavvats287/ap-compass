"""Demo-only human confirmation. Bounded inputs; no extraction or financial logic in routes."""
import json
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from app.domain.human_resolution import InvalidConfirmation
from app.orchestration.reviews import (ReviewService,ReviewActionSnapshot,ReviewHistory,
                                       ReviewConflict,ReviewUnavailable,ReviewNotFound)

router=APIRouter(prefix='/api')


class ConfirmationRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,str_strip_whitespace=True)
    po_id: str=Field(min_length=1,max_length=80,pattern=r'^[A-Za-z0-9-]+$')
    reviewer_label: str=Field(min_length=1,max_length=80)
    rationale: str=Field(min_length=10,max_length=2000)
    client_action_id: str=Field(min_length=36,max_length=36)

    @field_validator('client_action_id')
    @classmethod
    def valid_key(cls,value):
        parsed=UUID(value)
        if str(parsed)!=value: raise ValueError('Canonical UUID required')
        return value

    @field_validator('reviewer_label','rationale')
    @classmethod
    def safe_text(cls,value):
        if any(ord(c)<32 and c not in '\n\t' or ord(c)==127 for c in value):
            raise ValueError('Control characters are not allowed')
        return value


def service(request): return ReviewService(request.app.state.engine)


@router.get('/runs/{run_id}/review-history',response_model=ReviewHistory)
def history(run_id: str,request: Request):
    try: return service(request).history(run_id)
    except ReviewNotFound: raise HTTPException(404,'Run not found') from None
    except Exception: raise HTTPException(503,'Trusted review records are unavailable') from None


@router.post('/runs/{run_id}/po-confirmations',response_model=ReviewActionSnapshot,status_code=201)
async def confirm(run_id: str,request: Request,response: Response):
    if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':
        raise HTTPException(415,'Expected application/json')
    raw=bytearray()
    async for chunk in request.stream():
        if len(raw)+len(chunk)>8192: raise HTTPException(413,'Confirmation request too large')
        raw.extend(chunk)
    try: body=ConfirmationRequest.model_validate(json.loads(raw))
    except (ValidationError,ValueError,TypeError,UnicodeError,RecursionError):
        # Do not echo reviewer input (which may contain sensitive text) in validation responses/logs.
        raise HTTPException(422,'Choose a valid PO, demo reviewer, rationale (10–2000 characters), and UUID action key') from None
    from starlette.concurrency import run_in_threadpool
    try:
        action,created=await run_in_threadpool(service(request).confirm,run_id,**body.model_dump())
    except ReviewNotFound: raise HTTPException(404,'Run not found') from None
    except (ReviewConflict,ReviewUnavailable):
        raise HTTPException(409,'Confirmation unavailable or already recorded; reload review history') from None
    except InvalidConfirmation:
        raise HTTPException(422,'Selected PO is not a valid same-vendor candidate') from None
    except Exception:
        # Unexpected failures must not expose raw exception text or leave a partial action.
        raise HTTPException(503,'Trusted records could not be evaluated') from None
    response.status_code=201 if created else 200
    return action
