"""Request validation and read projections; no financial rules."""
import asyncio
from datetime import datetime
from decimal import Decimal, localcontext
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from python_multipart.exceptions import MultipartParseError
from starlette.datastructures import UploadFile
from starlette.responses import Response

from app.contracts import RunSnapshotV1, PolicyV1, Amount
from app.orchestration.reviews import ReviewActionSnapshot
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
    reviewed_outcome: str | None = None
    reviewed_at: datetime | None = None
    review_action_id: str | None = None


def find(request, run_id):
    snapshot = request.app.state.runs.repository.load(run_id)
    if snapshot is None:
        raise HTTPException(404, "Run not found")
    return snapshot


async def read_pdf(request: Request):
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
    return raw


@router.post("/runs", status_code=202, response_model=CreatedRun)
async def create_run(request: Request, price_tolerance_pct: Literal["0.02", "0.05"] | None = None):
    service = request.app.state.runs
    if len(request.query_params.getlist("price_tolerance_pct")) > 1:
        raise HTTPException(422, "Select exactly one unit-price tolerance")
    if not service.uploads_enabled:
        raise HTTPException(403, "New invoice uploads are disabled")
    if not service.reserve_upload():
        raise HTTPException(429, "Invoice capacity is full; try again after an active invoice finishes")
    try:
        try:
            async with asyncio.timeout(30):
                raw = await read_pdf(request)
        except TimeoutError:
            raise HTTPException(408, "Invoice upload timed out") from None
        ready = service.submit_upload(raw, Decimal(price_tolerance_pct) if price_tolerance_pct else None)
    except BaseException:
        service.release_upload()
        raise
    # A disconnected caller must not cancel an accepted file/row pair or free its slot.
    snapshot = await asyncio.shield(ready)
    if snapshot is None:
        raise HTTPException(503, "Invoice storage is temporarily unavailable; no run was confirmed")
    return CreatedRun(run_id=snapshot.id)


@router.get("/runs", response_model=list[RunSummary])
def list_runs(request: Request, limit: int = Query(50, ge=1, le=100)):
    output = []
    for snapshot, review_payload in request.app.state.runs.repository.all_with_reviews(limit):
        review = ReviewActionSnapshot.model_validate(review_payload) if review_payload else None
        invoice, decision = snapshot.extracted_invoice, snapshot.decision
        output.append(RunSummary(id=snapshot.id, created_at=snapshot.created_at, updated_at=snapshot.updated_at,
            execution_state=snapshot.execution_state, outcome=decision.outcome if decision else None,
            vendor_name=invoice.vendor_name_raw if invoice else None, invoice_number=invoice.invoice_number if invoice else None,
            total=invoice.total if invoice else None, currency=invoice.currency if invoice else None,
            primary_reason_code=decision.primary_reason_code if decision else None, owner=decision.owner if decision else None,
            reviewed_outcome=review.reassessment.outcome if review else None, reviewed_at=review.created_at if review else None,
            review_action_id=review.id if review else None))
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
        "X-Content-Type-Options": "nosniff", "Content-Disposition": 'inline; filename="invoice.pdf"',
        "Content-Security-Policy": "frame-ancestors 'self'; base-uri 'none'", "X-Frame-Options": "SAMEORIGIN"})


@router.get("/policy", response_model=PolicyV1)
def policy(request: Request):
    return request.app.state.runs.current_policy


def exact_currency_totals(grouped, *, fixed=False):
    values = {}
    for currency, amounts in sorted(grouped.items()):
        # Display aggregation only. Keep the precision of widely separated exponents.
        with localcontext() as context:
            context.prec = max(28, max(amount.adjusted() for amount in amounts)
                               - min(amount.as_tuple().exponent for amount in amounts)
                               + len(str(len(amounts))) + 4)
            total = sum(amounts, Decimal(0))
            values[currency] = format(total, "f") if fixed else str(total)
    return values


@router.get("/dashboard")
def dashboard(request: Request):
    snapshots = request.app.state.runs.repository.all()
    counts = dict(total_runs=len(snapshots), in_progress=0, completed=0, ready=0, review_required=0,
                  blocked=0, processing_failed=0, interrupted=0)
    outcomes = {"READY_FOR_AP": "ready", "REVIEW_REQUIRED": "review_required", "BLOCKED": "blocked"}
    flagged = {}
    missing = 0
    gross = {key: {} for key in ("submitted", *outcomes.values())}
    gross_missing = dict.fromkeys(gross, 0)
    for snapshot in snapshots:
        if snapshot.execution_state in ("QUEUED", "RUNNING"):
            counts["in_progress"] += 1
        else:
            counts[snapshot.execution_state.lower()] += 1
        invoice = snapshot.extracted_invoice
        bucket = outcomes[snapshot.decision.outcome] if snapshot.decision else None
        if bucket:
            counts[bucket] += 1
        if bucket in ("review_required", "blocked"):
            if invoice is None or invoice.net is None or not invoice.currency:
                missing += 1
            else:
                flagged.setdefault(invoice.currency, []).append(invoice.net)
        for group in ("submitted", bucket) if bucket else ("submitted",):
            if invoice is None or invoice.total is None or not invoice.currency:
                gross_missing[group] += 1
            else:
                gross[group].setdefault(invoice.currency, []).append(invoice.total)
    return {**counts, "flagged_invoice_net_by_currency": exact_currency_totals(flagged),
            "flagged_invoice_net_missing_count": missing,
            "invoice_gross": {key: {"by_currency": exact_currency_totals(amounts, fixed=True),
                                     "missing_count": gross_missing[key]}
                              for key, amounts in gross.items()}}
