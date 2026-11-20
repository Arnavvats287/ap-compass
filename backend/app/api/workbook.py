"""Workbook presentation of persisted snapshots. No policy or evidence interpretation."""
from collections import Counter
from io import BytesIO
import re
from textwrap import wrap
from zipfile import ZipFile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.orchestration.reviews import ReviewActionSnapshot

EXPORT_LIMIT = 100
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
INK, CHARCOAL, COPPER, STRIPE, RULE = "252525", "252422", "A64016", "F8F6F3", "E4DED7"
MUTED = "625B54"
OUTCOMES = {
    "READY_FOR_AP": "Ready to process",
    "REVIEW_REQUIRED": "Needs review",
    "BLOCKED": "Blocked",
}
GREEN = ("1C553A", "BCE8CD", "EFF9F2")
YELLOW = ("6B4409", "FFE69B", "FFF9E7")
RED = ("952F2F", "F5BCB7", "FFF1EF")
TECHNICAL = ("494B56", "E7E8EF", "F5F5F8")
STATUS_COLORS = {
    "Ready to process": GREEN,
    "Needs review": YELLOW,
    "Blocked": RED,
    "PASS": GREEN,
    "REVIEW": YELLOW,
    "BLOCK": RED,
    "PROCESSING_FAILED": TECHNICAL,
    "INTERRUPTED": TECHNICAL,
    "Required": YELLOW,
}
SOURCE_REVIEW_CODES = {"SOURCE_EVIDENCE_MISSING", "DOCUMENT_CONTENT_UNVERIFIED"}
COMPARISON_FIELDS = {
    "authorized_net", "prior_billed_net", "remaining_net", "requested_net", "excess_net",
    "expected_gross", "stated_gross", "difference", "remaining_qty", "requested_qty",
    "prior_billed_qty", "excess_qty", "invoice_price", "po_price", "tolerance_pct",
}
INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")

REGISTER = (
    ("Invoice number", 21), ("Supplier", 25), ("Invoice date", 14), ("PO reference", 15),
    ("Currency", 12), ("Net amount", 17), ("Tax amount", 17), ("Gross amount", 17),
    ("Original automated decision", 19), ("Current reviewed decision", 19),
    ("Primary issue", 31), ("Owner", 17), ("Next action", 42), ("Execution state", 23),
    ("Recorded unit-price tolerance", 19),
)
EXCEPTIONS = (
    ("Invoice number", 21), ("Supplier", 25), ("Severity", 13), ("Finding title", 31),
    ("Finding code", 30), ("Explanation", 46), ("Resolution owner", 17),
    ("Recommended next action", 42), ("Recorded financial comparison", 33),
)
EVIDENCE = (
    ("Invoice number", 21), ("Supplier", 25), ("Source route", 19),
    ("Native-verified references", 18), ("Unverified references", 16),
    ("Missing references", 16), ("Source review requirement", 19), ("Extraction provider", 26),
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


def wrapped_lines(value, width):
    return sum(max(1, len(wrap(line, width))) for line in str(value).split("\n"))


def add_sheet(book, title, columns, rows, invoice_count, generated, note, *,
              status_columns=(), right_columns=(), row_status_columns=()):
    sheet = book.create_sheet(title)
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 95
    sheet.sheet_properties.tabColor = COPPER if title == "Invoice Register" else CHARCOAL
    # Ordinary cells and a single worksheet pane avoid titles repeating while scrolling.
    sheet["A1"] = "AP Compass"
    sheet["A1"].font = Font(name="Calibri", size=16, bold=True, color=COPPER)
    sheet["C1"] = title
    sheet["C1"].font = Font(name="Calibri", size=16, bold=True, color=INK)
    sheet["A2"] = f"Latest {EXPORT_LIMIT} · {invoice_count} exported"
    sheet["C2"] = f"Generated {generated:%Y-%m-%d %H:%M UTC}"
    sheet["C3"] = note
    for address in ("A2", "C2", "C3"):
        sheet[address].font = Font(name="Calibri", size=10, italic=True, color=MUTED)
    for row, height in enumerate((29, 17, 20), 1):
        sheet.row_dimensions[row].height = height

    header_lines = 1
    for index, (heading, width) in enumerate(columns, 1):
        cell = sheet.cell(4, index, heading)
        cell.fill = fill(CHARCOAL)
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        cell.border = Border(right=Side(style="thin", color="514C47"))
        sheet.column_dimensions[get_column_letter(index)].width = width
        header_lines = max(header_lines, wrapped_lines(heading, width - 5))
    sheet.row_dimensions[4].height = max(27, header_lines * 15 + 9)

    for index, values in enumerate(rows, 5):
        lines = max((wrapped_lines(value, width - 4)
                     for value, (_, width) in zip(values, columns) if value is not None), default=1)
        row_status = next((STATUS_COLORS[values[col - 1]] for col in row_status_columns
                           if values[col - 1] in STATUS_COLORS), None)
        row_surface = row_status[2] if row_status else ("FFFFFF" if index % 2 else STRIPE)
        for col, value in enumerate(values, 1):
            cell = sheet.cell(index, col)
            write_cell(cell, value)
            colors = STATUS_COLORS.get(value) if col in status_columns else None
            text, surface = colors[:2] if colors else (INK, row_surface)
            cell.fill = fill(surface)
            cell.font = Font(name="Calibri", size=11, color=text, bold=bool(colors or col == 1))
            cell.alignment = Alignment(horizontal="right" if col in right_columns else "left",
                                       vertical="top" if lines > 1 else "center",
                                       wrap_text=True, indent=1)
            cell.border = Border(bottom=Side(style="hair", color=RULE))
            if col in right_columns and isinstance(value, str):
                cell.number_format = "@"
        sheet.row_dimensions[index].height = min(396, max(23, lines * 15 + 6))
    sheet.auto_filter.ref = f"A4:{get_column_letter(len(columns))}{sheet.max_row}"


def save_workbook(book, invoice_count):
    with BytesIO() as original:
        book.save(original)
        if not invoice_count:
            return original.getvalue()
        # openpyxl has no public writer for this sheet setting. Suppress Excel's
        # number-as-text warning only where exact amounts and percentages are intentional.
        last_row = invoice_count + 4
        ignored = (f'<ignoredErrors><ignoredError sqref="F5:H{last_row} O5:O{last_row}" '
                   'numberStoredAsText="1"/></ignoredErrors>').encode("ascii")
        with ZipFile(original) as source, BytesIO() as output:
            with ZipFile(output, "w") as target:
                for item in source.infolist():
                    contents = source.read(item)
                    if item.filename == "xl/worksheets/sheet1.xml":
                        contents = contents.replace(b"</worksheet>", ignored + b"</worksheet>", 1)
                    target.writestr(item, contents)
            return output.getvalue()


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
            f"{(snapshot.policy_snapshot.price_tolerance_pct * 100).normalize():f}%"
            if snapshot.policy_snapshot is not None else None,
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
    invoice_count = len(register)
    add_sheet(book, "Invoice Register", REGISTER, register, invoice_count, generated,
              "Amounts are exact text. Issue, owner and action reflect the original automated assessment.",
              status_columns=(9, 10, 14), right_columns=(6, 7, 8), row_status_columns=(9, 14))
    add_sheet(book, "Exceptions", EXCEPTIONS, exceptions, invoice_count, generated,
              "All recorded automated findings, including informational and passing checks.",
              status_columns=(3,), row_status_columns=(3,))
    add_sheet(book, "Evidence Summary", EVIDENCE, evidence, invoice_count, generated,
              "Counts reflect stored evidence references. A blank review requirement means no recorded decision.",
              status_columns=(7,), right_columns=(4, 5, 6))
    return save_workbook(book, invoice_count)
