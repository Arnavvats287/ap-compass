"""Workbook presentation of persisted snapshots. No policy or evidence interpretation."""
from collections import Counter
from io import BytesIO
from math import ceil
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.orchestration.reviews import ReviewActionSnapshot

EXPORT_LIMIT = 100
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
INK, FOREST, CREAM, SAGE = "20352F", "225646", "F8F7EF", "E6EEDB"
OUTCOMES = {
    "READY_FOR_AP": "Ready to process",
    "REVIEW_REQUIRED": "Needs review",
    "BLOCKED": "Blocked",
}
STATUS_COLORS = {
    "Ready to process": ("256043", "EAF3EC"),
    "Needs review": ("80510E", "FFF3DB"),
    "Blocked": ("A13731", "FBEFEC"),
    "REVIEW": ("80510E", "FFF3DB"),
    "BLOCK": ("A13731", "FBEFEC"),
    "PROCESSING_FAILED": ("6A3835", "F5EDEB"),
    "INTERRUPTED": ("586452", "EFF0E8"),
}
SOURCE_REVIEW_CODES = {"SOURCE_EVIDENCE_MISSING", "DOCUMENT_CONTENT_UNVERIFIED"}
COMPARISON_FIELDS = {
    "authorized_net", "prior_billed_net", "remaining_net", "requested_net", "excess_net",
    "expected_gross", "stated_gross", "difference", "remaining_qty", "requested_qty",
    "prior_billed_qty", "excess_qty", "invoice_price", "po_price", "tolerance_pct",
}
INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")

REGISTER = (
    ("Invoice number", 25), ("Supplier", 30), ("Invoice date", 15), ("PO reference", 17),
    ("Currency", 12), ("Net amount", 19), ("Tax amount", 19), ("Gross amount", 19),
    ("Original automated decision", 30), ("Current reviewed decision", 28),
    ("Primary issue", 35), ("Owner", 20), ("Next action", 48), ("Execution state", 24),
)
EXCEPTIONS = (
    ("Invoice number", 25), ("Supplier", 30), ("Severity", 13), ("Finding title", 33),
    ("Finding code", 32), ("Explanation", 54), ("Resolution owner", 20),
    ("Recommended next action", 49), ("Recorded financial comparison", 40),
)
EVIDENCE = (
    ("Invoice number", 25), ("Supplier", 30), ("Source route", 20),
    ("Native-verified references", 28), ("Unverified references", 23),
    ("Missing references", 22), ("Source review requirement", 29), ("Extraction provider", 30),
)


def write_cell(cell, value):
    if isinstance(value, str):
        cell.value = INVALID_XML.sub("\ufffd", value)
        # Serialize even formula-like strings as literal inline strings.
        cell.data_type = "s"
    else:
        cell.value = value


def fill(color):
    return PatternFill("solid", fgColor=color)


def add_sheet(book, title, columns, rows, metadata, note, *, status_columns=(), right_columns=()):
    sheet = book.create_sheet(title)
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 85
    sheet.sheet_properties.tabColor = FOREST
    for row, text in enumerate((f"AP Compass  /  {title}", metadata, note), 1):
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=len(columns))
        cell = sheet.cell(row, 1)
        write_cell(cell, text)
        cell.font = Font(name="Calibri", size=19 if row == 1 else 11, bold=row == 1, color=INK)
        cell.fill = fill(SAGE if row == 1 else CREAM)
        cell.alignment = Alignment(vertical="center", indent=1)
        sheet.row_dimensions[row].height = 32 if row == 1 else 20
    for index, (heading, width) in enumerate(columns, 1):
        cell = sheet.cell(4, index, heading)
        cell.fill = fill(FOREST)
        cell.font = Font(name="Calibri", bold=True, color="FFFFFF")
        cell.alignment = Alignment(vertical="center", indent=1)
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.row_dimensions[4].height = 26
    for index, values in enumerate(rows, 5):
        lines = 1
        for col, value in enumerate(values, 1):
            cell = sheet.cell(index, col)
            write_cell(cell, value)
            if value is not None:
                width = columns[col - 1][1] - 3
                lines = max(lines, sum(max(1, ceil(len(line) / width)) for line in str(value).split("\n")))
            colors = STATUS_COLORS.get(value) if col in status_columns else None
            text, surface = colors or (INK, "FFFFFF" if index % 2 else CREAM)
            cell.fill = fill(surface)
            cell.font = Font(name="Calibri", color=text, bold=bool(colors))
            cell.alignment = Alignment(horizontal="right" if col in right_columns else "left",
                                       vertical="center", wrap_text=True, indent=1)
            if col in right_columns and isinstance(value, str):
                cell.number_format = "@"
        sheet.row_dimensions[index].height = min(240, max(24, lines * 16 + 8))
    sheet.freeze_panes = "C5"
    sheet.auto_filter.ref = f"A4:{get_column_letter(len(columns))}{sheet.max_row}"


def build_invoice_workbook(records, generated):
    register, exceptions, evidence = [], [], []
    for snapshot, review_payload in records:
        decision = snapshot.decision
        invoice = snapshot.extracted_invoice
        review = ReviewActionSnapshot.model_validate(review_payload) if review_payload else None
        identity = (invoice.invoice_number, invoice.vendor_name_raw) if invoice else (None, None)
        findings = decision.findings if decision else ()
        primary = next((f.title for f in findings if f.code == decision.primary_reason_code), None)
        amounts = (invoice.net, invoice.tax, invoice.total) if invoice else (None,) * 3
        register.append((
            *identity,
            invoice.invoice_date.isoformat() if invoice and invoice.invoice_date else None,
            invoice.po_reference if invoice else None, invoice.currency if invoice else None,
            *(str(amount) if amount is not None else None for amount in amounts),
            OUTCOMES[decision.outcome] if decision else None,
            OUTCOMES[review.reassessment.outcome] if review else None,
            primary or (decision.primary_reason_code if decision else snapshot.execution_error_code),
            decision.owner if decision else None, decision.next_action if decision else None,
            snapshot.execution_state,
        ))
        for finding in findings:
            comparison = "\n".join(
                f"{entry.name.replace('_', ' ')}: {entry.value}" for entry in finding.values
                if entry.name in COMPARISON_FIELDS and entry.value is not None
            )
            exceptions.append((
                *identity, finding.severity, finding.title, finding.code, finding.explanation,
                finding.owner, finding.next_action, comparison or None,
            ))
        counts = Counter(ref.evidence_state for ref in invoice.evidence) if invoice else Counter()
        source_review = None
        if decision:
            source_review = "Required" if any(f.code in SOURCE_REVIEW_CODES for f in findings) else "Not flagged"
        evidence.append((
            *identity, snapshot.source_route, counts["NATIVE_VERIFIED"],
            counts["SOURCE_LOCATED_UNVERIFIED"], counts["MISSING"], source_review, snapshot.model_id,
        ))
    book = Workbook()
    book.remove(book.active)
    book.properties.title = "AP Compass Invoice Register"
    book.properties.creator = "AP Compass"
    metadata = f"Latest {EXPORT_LIMIT} persisted invoices by submission  ·  {len(register)} exported  ·  {generated:%Y-%m-%d %H:%M UTC}"
    add_sheet(book, "Invoice Register", REGISTER, register, metadata,
              "Exact amounts stored as text. Issue, owner and action are from the original automated assessment.",
              status_columns=(9, 10, 14), right_columns=(6, 7, 8))
    add_sheet(book, "Exceptions", EXCEPTIONS, exceptions, metadata,
              "All recorded automated findings, including informational and passing checks.",
              status_columns=(3,))
    add_sheet(book, "Evidence Summary", EVIDENCE, evidence, metadata,
              "Counts reflect stored evidence references. A blank review requirement means no recorded decision.",
              right_columns=(4, 5, 6))
    with BytesIO() as output:
        book.save(output)
        return output.getvalue()
