"""Original DEV_ONLY layouts and controlled claims. No independent archive inputs."""
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def cells(pdf, y, *values):
    for x, text in values:
        pdf.drawString(x, y, text)


def source_layout(*, statement=False, conflict=None, ambiguity=False, missing_code=False,
                  overlapping=False, identical=False, extra_item=False, competing_label=False,
                  periods=False, omit_line_net=False, buyer_below=False, column_net_only=False):
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=A4, invariant=1)
    pdf.setFont("Helvetica", 11)
    if buyer_below:
        cells(pdf, 782, (186, "Supplier"))
    else:
        cells(pdf, 782, (44, "Supplier"), (186, "Orion Office Products"))
    cells(pdf, 760, (44, "Bill to"), (186, "West Yard Workshop"))
    cells(pdf, 738, (44, "Invoice No"), (186, "DEV-LAYOUT-107"))
    cells(pdf, 716, (44, "Invoice date"), (186, "08 Oct 2026"))
    cells(pdf, 694, (44, "PO No"), (186, "Currency"))
    cells(pdf, 678, (44, "PO-6001"), (186, "INR"))
    columns = [(44, "Item code"), (160, "Description"), (342, "Qty"), (405, "Unit net"),
               (502, "Net amount" if column_net_only else "Line net")]
    if periods:
        columns.insert(2, (262, "Service period"))
    cells(pdf, 620, *columns)
    first = ("OR-SUPPLY-01", "Stationery kits", "3", "1,000.00", "3,000.00")
    second = ("DEV-EXTRA-02" if extra_item else "OR-SUPPLY-01", "Archive packs", "2", "1,000.00", "2,000.00")
    if identical:
        second = first
    def printed_row(row, index):
        values = list(row)
        if periods:
            values.insert(2, ("Aug 2026", "Sep 2026")[index])
        if omit_line_net and index == 1:
            values.pop()
        if missing_code and index == 1:
            values[0] = ""
        return tuple(values)

    xs = [x for x, _ in columns]
    for index, y in enumerate((596, 589 if overlapping else 572)):
        cells(pdf, y, *zip(xs, printed_row((first, second)[index], index)))
    if not column_net_only:
        cells(pdf, 530, (332, "Subtotal"), (494, "INR 5,000.00"))
    cells(pdf, 508, (332, "GST"), (494, "INR 900.00"))
    cells(pdf, 486, (332, "Grand Total"), (494, "INR 5,900.00"))
    if ambiguity:
        cells(pdf, 469, (332, "INR 6,400.00"))
    if competing_label:
        cells(pdf, 465, (44, "Invoice No: DEV-LAYOUT-107"))
    if statement:
        cells(pdf, 406, (44, "Account summary"))
        cells(pdf, 382, (44, "Previous account balance"), (275, "INR 1,800.00"))
        cells(pdf, 360, (44, "Current invoice total"), (275, "INR 5,900.00"))
        cells(pdf, 338, (44, "Combined account balance"), (275, "INR 7,700.00"))
    if conflict == "same_page":
        cells(pdf, 200, (44, "Revised Grand Total: INR 6,400.00"))
    if conflict in {"next_page", "other_po"}:
        pdf.showPage()
        pdf.setFont("Helvetica", 11)
        if conflict == "next_page":
            cells(pdf, 780, (44, "Revision notice for this synthetic test invoice"))
            cells(pdf, 745, (44, "Revised Grand Total"), (230, "INR 6,400.00"))
        else:
            cells(pdf, 780, (44, "Attached purchase reference with uncertain invoice association"))
            cells(pdf, 745, (44, "PO No"), (230, "PO-1042"))
    pdf.save()

    header = [
        ("vendor_name_raw", "Orion Office Products", "Supplier Orion Office Products"),
        ("invoice_number", "DEV-LAYOUT-107", "Invoice No DEV-LAYOUT-107"),
        ("invoice_date", "08 Oct 2026", "Invoice date 08 Oct 2026"),
        ("po_reference", "PO-6001", "PO No PO-6001"),
        ("currency", "INR", "Currency INR"),
        ("net", "5,000.00", "Subtotal INR 5,000.00"),
        ("tax", "900.00", "GST INR 900.00"),
        ("total", "5,900.00", "Grand Total INR 5,900.00"),
    ]
    reply = {field: value for field, value, _ in header}
    reply.update(invoice_date="2026-10-08", net="5000", tax="900", total="5900", bank_instructions=None, lines=[])
    claims = header[:]
    for index, row in enumerate((first, second)):
        keys = ("item_code", "description", "qty", "unit_price_net", "net")
        line = dict(zip(keys, row))
        for key in ("unit_price_net", "net"):
            line[key] = line[key].replace(",", "")
        if missing_code and index == 1:
            line["item_code"] = None
        reply["lines"].append(line)
        quote = " ".join(printed_row(row, index))
        claims.extend((f"lines[{index}].{key}", value, quote) for key, value in zip(keys, row)
                      if line[key] is not None)
    reply["evidence"] = [{"field": field, "raw_value": raw, "quote": quote, "page": 1}
                         for field, raw, quote in claims]
    return stream.getvalue(), reply
