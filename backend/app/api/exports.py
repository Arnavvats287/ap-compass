"""Authenticated in private mode by the same middleware as the invoice register."""
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from starlette.responses import Response

from .workbook import EXPORT_LIMIT, XLSX_TYPE, build_invoice_workbook

router = APIRouter(prefix="/api")


@router.get("/exports/invoices.xlsx", response_class=Response)
def export_invoices(request: Request):
    records = request.app.state.runs.repository.all_with_reviews(EXPORT_LIMIT)
    generated = datetime.now(timezone.utc)
    return Response(
        build_invoice_workbook(records, generated),
        media_type=XLSX_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="ap-compass-invoice-register-{generated.date()}.xlsx"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
