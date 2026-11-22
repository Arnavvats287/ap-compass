from decimal import Decimal
from io import BytesIO
from secrets import token_urlsafe
from xml.etree import ElementTree
from zipfile import ZipFile

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import event

from app.api.workbook import XLSX_TYPE
from app.main import create_app
from test_finance_engine import facts
from test_orchestration_api import authority
from test_review_api import body, complete

EXPORT = "/api/exports/invoices.xlsx"


def open_export(response):
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == XLSX_TYPE
    assert response.headers["content-disposition"].startswith('attachment; filename="ap-compass-')
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    book = load_workbook(BytesIO(response.content))
    assert book.sheetnames == ["Invoice Register", "Exceptions", "Evidence Summary"]
    for sheet in book:
        assert sheet.freeze_panes is None
        assert sheet.sheet_view.pane is None
        assert sheet.auto_filter.ref.startswith("A4:")
        assert sheet["A4"].fill.fgColor.rgb.endswith("252422")
        assert "Latest 100" in sheet["A2"].value
        assert not sheet.merged_cells.ranges
        assert sheet.row_dimensions[4].height >= 39
        assert all(cell.alignment.wrap_text for cell in sheet[4])
    return book


def test_excel_export_requires_private_auth_even_when_empty(tmp_path, monkeypatch):
    origin = "http://127.0.0.1:8077"
    password = token_urlsafe(32)
    monkeypatch.setenv("AP_COMPASS_MODE", "private")
    monkeypatch.setenv("AP_COMPASS_PRIVATE_ORIGIN", origin)
    monkeypatch.setenv("AP_COMPASS_PRIVATE_USERNAME", "export-test")
    monkeypatch.setenv("AP_COMPASS_PRIVATE_PASSWORD", password)
    app = create_app(tmp_path / "app.db", document_dir=tmp_path / "docs")
    with TestClient(app, base_url=origin) as client:
        guest = client.get(EXPORT)
        assert guest.status_code == 401
        assert guest.headers["www-authenticate"].startswith("Basic")
        book = open_export(client.get(EXPORT, auth=("export-test", password)))
        assert all(sheet.max_row == 4 for sheet in book)


def test_workbook_reads_stored_assessments_without_writes_or_inference(tmp_path):
    async def forbidden(raw):
        raise AssertionError("Export must never extract a PDF")

    app = create_app(tmp_path / "app.db", document_dir=tmp_path / "docs", extractor=forbidden)
    with TestClient(app) as client:
        ledger = authority(app.state.engine)
        reviewed_id = complete(app)
        review = client.post(f"/api/runs/{reviewed_id}/po-confirmations", json=body())
        assert review.status_code == 201
        assert review.json()["reassessment"]["outcome"] == "READY_FOR_AP"
        precision = Decimal("12345678901234567890.0000070")
        blocked_id = complete(app, facts("OVERBILLED_PARTIAL"))
        repo = app.state.runs.repository
        invoice = repo.load(blocked_id).extracted_invoice.model_copy(update={
            "vendor_name_raw": "=1+1", "invoice_number": "+Invoice-precision", "net": precision,
        })
        repo.update(blocked_id, extracted_invoice=invoice)
        blocked = client.get(f"/api/runs/{blocked_id}").json()
        assert blocked["decision"]["outcome"] == "BLOCKED"
        failed_id = repo.create("b" * 32).id
        repo.terminate(failed_id, "INVALID_PDF")
        statements = []

        @event.listens_for(app.state.engine, "before_cursor_execute")
        def capture(conn, cursor, statement, parameters, context, many):
            statements.append(statement)

        response = client.get(EXPORT)
        book = open_export(response)
        with ZipFile(BytesIO(response.content)) as archive:
            root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            warning = root.find("./{*}ignoredErrors/{*}ignoredError")
            assert warning is not None
            assert warning.attrib == {"sqref": "F5:H7", "numberStoredAsText": "1"}
        assert len(statements) == 1
        assert statements[0].lstrip().startswith("SELECT")
        assert authority(app.state.engine) == ledger
        register = book["Invoice Register"]
        assert register.max_column == 14
        assert register["N4"].value == "Execution state"
        assert register.auto_filter.ref == "A4:N7"
        rows = list(register.iter_rows(min_row=5, values_only=True))
        assert len(rows) == 3
        failed, blocked_row, reviewed_row = rows
        assert failed[8:11] == (None, None, "INVALID_PDF")
        assert failed[13] == "PROCESSING_FAILED"
        assert blocked_row[:2] == ("+Invoice-precision", "=1+1")
        assert blocked_row[4:9] == ("INR", str(precision), blocked["extracted_invoice"]["tax"],
                                      blocked["extracted_invoice"]["total"], "Blocked")
        assert register["B6"].data_type == "s"
        assert register["F6"].data_type == "s" and register["F6"].number_format == "@"
        assert register["F6"].alignment.horizontal == "right"
        assert register["F6"].alignment.wrap_text
        assert register["I6"].fill.fgColor.rgb != register["I7"].fill.fgColor.rgb
        assert register["A5"].fill.fgColor.rgb.endswith("F5F5F8")
        assert register["A6"].fill.fgColor.rgb.endswith("FFF1EF")
        assert register["A7"].fill.fgColor.rgb.endswith("FFF9E7")
        assert register["J7"].fill.fgColor.rgb.endswith("BCE8CD")
        assert reviewed_row[8:10] == ("Needs review", "Ready to process")
        exceptions = list(book["Exceptions"].iter_rows(min_row=5, values_only=True))
        assert any(row[4] == "PO_BALANCE_EXCEEDED" and "requested net:" in row[8] for row in exceptions)
        evidence = list(book["Evidence Summary"].iter_rows(min_row=5, values_only=True))
        assert evidence[0][6] is None
        assert evidence[1][3] == sum(ref["evidence_state"] == "NATIVE_VERIFIED"
                                     for ref in blocked["extracted_invoice"]["evidence"])
        assert all(cell.data_type != "f" for sheet in book for row in sheet for cell in row)
