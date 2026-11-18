"""Generate exactly the four Phase 1 synthetic native-text PDFs from the oracle."""
import json
from decimal import Decimal
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[1]
IDS = ("HAPPY_CLEAN", "HAPPY_PARTIAL", "OVERBILLED_PARTIAL", "DUPLICATE_REISSUED")

def generate(output=ROOT / "tests/fixtures"):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ROOT / "data/fixture_manifest.json").read_text())["fixture_cases"]
    for case in cases:
        if case["id"] not in IDS:
            continue
        pdf = canvas.Canvas(str(output / case["filename"]), pagesize=A4, invariant=1)
        pdf.setTitle("Synthetic invoice - " + case["invoice_number"])
        duplicate = case["id"] == "DUPLICATE_REISSUED"
        x = 48 if not duplicate else 70
        pdf.setFillColorRGB(.08, .24, .20)
        pdf.rect(0, 735, 595, 107, fill=1, stroke=0)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont("Helvetica-Bold", 23)
        pdf.drawString(x, 790, "INVOICE" if not duplicate else "REISSUED INVOICE COPY")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x, 763, "SYNTHETIC DEMO - Fictional supplier and transaction")
        pdf.setFillColorRGB(.12, .2, .17)
        pdf.setFont("Helvetica-Bold", 17)
        pdf.drawString(x, 690, case["vendor_name"])
        pdf.setFont("Helvetica", 11)
        rows = ["Invoice number: " + case["invoice_number"], "Invoice date: " + case["invoice_date"], "Purchase order: " + case["po_reference"], "Currency: " + case["currency"]]
        y = 655
        for row in rows:
            pdf.drawString(x, y, row); y -= 23
        y -= 25
        pdf.setStrokeColorRGB(.8, .85, .8)
        pdf.line(x, y, 545, y); y -= 30
        for line in case["lines"]:
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(x, y, line["description"]); y -= 23
            pdf.setFont("Helvetica", 10)
            for row in ["Item code: " + line["item_code"], "Quantity: " + line["qty"], "Unit price (net): INR " + line["unit_price_net"], "Line net: INR " + str(Decimal(line["qty"]) * Decimal(line["unit_price_net"]))]:
                pdf.drawString(x, y, row); y -= 21
        y -= 22
        pdf.line(x, y, 545, y); y -= 30
        for label, key in [("Net subtotal", "net"), ("Tax (synthetic GST)", "tax"), ("Invoice total", "gross")]:
            pdf.setFont("Helvetica-Bold" if key == "gross" else "Helvetica", 12)
            pdf.drawString(x, y, label + ": INR " + case[key]); y -= 27
        pdf.setFont("Helvetica", 9)
        pdf.setFillColorRGB(.45, .5, .45)
        pdf.drawString(x, 80, "Fictional test data only. No payment instruction or posting authority.")
        pdf.drawString(x, 63, "Native-text fixture | AP Compass | Page 1 of 1")
        pdf.showPage(); pdf.save()
        print("Generated " + case["filename"])

if __name__ == "__main__":
    generate()
