"""Request validation and read projections; no financial rules."""
import asyncio
from datetime import datetime
from decimal import Decimal, localcontext

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from python_multipart.exceptions import MultipartParseError
from starlette.datastructures import UploadFile
from starlette.responses import Response

from app.contracts import RunSnapshotV1, PolicyV1, Amount
from app.documents.limits import MAX_INPUT_BYTES

router = APIRouter(prefix="/api")


class CreatedRun(BaseModel):
    run_id: str
    execution_state: str = "QUEUED"


class RunSummary(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    execution_state: str
    outcome: str | None = None
    vendor_name: str | None = None
    invoice_number: str | None = None
    total: Amount | None = None
    currency: str | None = None
    primary_reason_code: str | None = None
    owner: str | None = None


def find(request, run_id):
    snapshot = request.app.state.runs.repository.load(run_id)
    if snapshot is None:
        raise HTTPException(404, "Run not found")
    return snapshot


@router.post("/runs", status_code=202, response_model=CreatedRun)
async def create_run(request: Request):
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "multipart/form-data":
        raise HTTPException(415, "Expected multipart PDF upload")
    # Bound the entire multipart envelope too. Starlette's per-part limit alone
    # does not bound file spooling. 64 KiB permits ordinary headers/boundaries.
    maximum = MAX_INPUT_BYTES + 65536
    envelope = bytearray()
    async for chunk in request.stream():
        if len(envelope) + len(chunk) > maximum:
            raise HTTPException(413, "Upload too large")
        envelope.extend(chunk)
    async def receive():
        return {"type": "http.request", "body": bytes(envelope), "more_body": False}
    bounded_request = Request(request.scope, receive)
    try:
        async with bounded_request.form(max_files=1, max_fields=0, max_part_size=1024) as form:
            items = form.multi_items()
            if len(items) != 1 or items[0][0] != "file" or not isinstance(items[0][1], UploadFile):
                raise HTTPException(400, "Exactly one file field is required")
            upload = items[0][1]
            if upload.content_type != "application/pdf":
                raise HTTPException(415, "Expected application/pdf")
            raw = await upload.read(MAX_INPUT_BYTES + 1)
    except MultipartParseError:
        raise HTTPException(400, "Malformed multipart upload") from None
    if len(raw) > MAX_INPUT_BYTES:
        raise HTTPException(413, "PDF too large")
    if not raw or not raw.startswith(b"%PDF-"):
        raise HTTPException(400, "Empty or invalid PDF signature")
    service = request.app.state.runs
    document_id = await asyncio.to_thread(service.documents.write, raw)
    snapshot = service.repository.create(document_id)
    service.submit(snapshot.id)
    return CreatedRun(run_id=snapshot.id)


@router.get("/runs", response_model=list[RunSummary])
def list_runs(request: Request, limit: int = Query(50, ge=1, le=100)):
    output = []
    for snapshot in request.app.state.runs.repository.all(limit):
        invoice, decision = snapshot.extracted_invoice, snapshot.decision
        output.append(RunSummary(id=snapshot.id, created_at=snapshot.created_at, updated_at=snapshot.updated_at,
            execution_state=snapshot.execution_state, outcome=decision.outcome if decision else None,
            vendor_name=invoice.vendor_name_raw if invoice else None, invoice_number=invoice.invoice_number if invoice else None,
            total=invoice.total if invoice else None, currency=invoice.currency if invoice else None,
            primary_reason_code=decision.primary_reason_code if decision else None, owner=decision.owner if decision else None))
    return output


@router.get("/runs/{run_id}", response_model=RunSnapshotV1)
def run_detail(request: Request, run_id: str):
    return find(request, run_id)


@router.get("/runs/{run_id}/document")
async def document(request: Request, run_id: str):
    snapshot = find(request, run_id)
    try:
        raw = await asyncio.to_thread(request.app.state.runs.documents.read, snapshot.document_id)
    except (OSError, ValueError):
        raise HTTPException(404, "Document not found") from None
    return Response(raw, media_type="application/pdf", headers={"Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff", "Content-Disposition": 'inline; filename="invoice.pdf"'})


@router.get("/policy", response_model=PolicyV1)
def policy(request: Request):
    return request.app.state.runs.current_policy


@router.get("/dashboard")
def dashboard(request: Request):
    snapshots = request.app.state.runs.repository.all()
    counts = dict(total_runs=len(snapshots), in_progress=0, completed=0, ready=0, review_required=0,
                  blocked=0, processing_failed=0, interrupted=0)
    outcomes = {"READY_FOR_AP": "ready", "REVIEW_REQUIRED": "review_required", "BLOCKED": "blocked"}
    flagged = {}
    missing = 0
    for snapshot in snapshots:
        if snapshot.execution_state in ("QUEUED", "RUNNING"):
            counts["in_progress"] += 1
        else:
            counts[snapshot.execution_state.lower()] += 1
        if snapshot.decision:
            counts[outcomes[snapshot.decision.outcome]] += 1
            if snapshot.decision.outcome in ("REVIEW_REQUIRED", "BLOCKED"):
                invoice = snapshot.extracted_invoice
                if invoice is None or invoice.net is None or not invoice.currency:
                    missing += 1
                else:
                    flagged.setdefault(invoice.currency, []).append(invoice.net)
    values = {}
    for currency, amounts in sorted(flagged.items()):
        # Exact display projection, including widely separated decimal exponents.
        # No rounding, cross-currency addition or financial decision is performed.
        with localcontext() as context:
            context.prec = max(28, max(amount.adjusted() for amount in amounts)
                               - min(amount.as_tuple().exponent for amount in amounts)
                               + len(str(len(amounts))) + 4)
            values[currency] = str(sum(amounts, Decimal(0)))
    return {**counts, "flagged_invoice_net_by_currency": values,
            "flagged_invoice_net_missing_count": missing}
