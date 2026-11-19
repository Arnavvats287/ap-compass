"""Render the two frozen Group C PDFs from the reviewed business facts."""
import argparse
import json
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tests/fixtures/golden_v1"
MANIFEST = ROOT / "data/golden_dataset_v1.json"
INK = colors.HexColor("#172e34")
TEAL = colors.HexColor("#056b64")
MUTED = colors.HexColor("#4a5d63")
WARM = colors.HexColor("#f5eade")
PALE = colors.HexColor("#eaf3f2")


def write(pdf, x, y, value, *, size=11, bold=False, color=INK):
    pdf.setFillColor(color)
    pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    pdf.drawString(x, y, value)


def panel(pdf, x, y, width, height, color):
    pdf.setFillColor(color)
    pdf.rect(x, y, width, height, fill=1, stroke=0)


def money(value):
    return f"INR {Decimal(value):,.2f}"


def identity(pdf, x, y, case):
    for offset, (label, key) in enumerate((
        ("Invoice number", "invoice_number"), ("Invoice date", "invoice_date"),
        ("Purchase order", "po_reference"), ("Currency", "currency"),
    )):
        write(pdf, x, y - offset * 21, f"{label}: {case[key]}")


def line_detail(pdf, x, y, line):
    write(pdf, x, y, line["description"], size=13, bold=True)
    write(pdf, x, y - 21, f"Item code: {line['item_code']}")
    write(pdf, x, y - 42, f"Quantity: {line['qty']}")
    write(pdf, x, y - 63, f"Unit price (net): {money(line['unit_price_net'])}")
    write(pdf, x, y - 84, f"Line net: {money(line['net'])}", bold=True)


def totals(pdf, x, y, case):
    write(pdf, x, y, f"Net subtotal: {money(case['net'])}")
    write(pdf, x, y - 23, f"Tax (GST 18%): {money(case['tax'])}")
    write(pdf, x, y - 51, f"Invoice total: {money(case['gross'])}", size=14, bold=True)


def scope_invoice(pdf, case):
    panel(pdf, 0, 817, A4[0], 25, TEAL)
    write(pdf, 48, 768, case["vendor_name"], size=21, bold=True)
    write(pdf, 48, 730, "Service invoice", size=15, color=TEAL)
    identity(pdf, 48, 692, case)
    write(pdf, 48, 574, "Services billed", size=14, bold=True)
    for index, line in enumerate(case["lines"]):
        x = 48 + index * 253
        panel(pdf, x, 425, 245, 128, PALE)
        line_detail(pdf, x + 14, 530, line)
    write(pdf, 299, 383, "Current invoice charges", size=13, bold=True, color=TEAL)
    totals(pdf, 299, 350, case)


def statement_invoice(pdf, case):
    panel(pdf, 0, 0, 28, A4[1], WARM)
    write(pdf, 57, 768, "Tax invoice", size=28, bold=True)
    write(pdf, 57, 732, case["vendor_name"], size=17, bold=True)
    identity(pdf, 57, 685, case)
    write(pdf, 57, 573, "Current purchase", size=13, color=TEAL, bold=True)
    line_detail(pdf, 57, 539, case["lines"][0])
    panel(pdf, 305, 453, 240, 104, PALE)
    totals(pdf, 320, 531, case)
    panel(pdf, 57, 261, 488, 143, WARM)
    write(pdf, 74, 375, "Account summary", size=16, bold=True)
    write(pdf, 74, 353, "Account history is separate from the current invoice charges.", color=MUTED)
    summary = case["account_summary"]
    write(pdf, 74, 329, f"Previous account balance: {money(summary['previous_balance'])}")
    write(pdf, 74, 307, f"Current invoice total: {money(summary['current_invoice_total'])}")
    write(pdf, 74, 285, f"Account balance including previous amount: {money(summary['combined_balance'])}", bold=True)


LAYOUTS = {"SCOPE_UNAUTHORIZED_LINE": scope_invoice, "STATEMENT_PRIOR_BALANCE": statement_invoice}


def generate(output: Path):
    dataset = json.loads(MANIFEST.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    for case in dataset["cases"]:
        if case["group"] != "C":
            continue
        pdf = canvas.Canvas(str(output / Path(case["pdf"]["path"]).name), pagesize=A4, invariant=1)
        pdf.setTitle(f"Synthetic invoice {case['invoice_number']}")
        LAYOUTS[case["case_id"]](pdf, case)
        write(pdf, 57, 65, "Synthetic AP Compass fixture. Fictional transaction. No payment instructions.",
              size=9, color=MUTED)
        pdf.showPage()
        pdf.save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    generate(parser.parse_args().output)
