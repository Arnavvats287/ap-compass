"""Generate native-text oracle fixtures; default selection preserves the four Phase 1 PDFs."""
import json
from decimal import Decimal
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[1]
IDS = ("HAPPY_CLEAN", "HAPPY_PARTIAL", "OVERBILLED_PARTIAL", "DUPLICATE_REISSUED")

def generate(output=ROOT / "tests/fixtures", *, ids=IDS, cases=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    cases = cases if cases is not None else json.loads((ROOT / "data/fixture_manifest.json").read_text())["fixture_cases"]
    for case in cases:
        if case["id"] not in ids:
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
        rows = ["Invoice number: " + case["invoice_number"], "Invoice date: " + case["invoice_date"], "Purchase order: " + (case["po_reference"] or "Not stated"), "Currency: " + case["currency"]]
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
            line_rows = ["Item code: " + (line["item_code"] or "Not stated"), "Quantity: " + (line["qty"] or "Not stated"), "Unit price (net): INR " + (line["unit_price_net"] or "Not stated")]
            if line["qty"] is not None and line["unit_price_net"] is not None:
                line_rows.append("Line net: INR " + str(Decimal(line["qty"]) * Decimal(line["unit_price_net"])))
            for row in line_rows:
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
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=(*IDS, "PRICE_3PCT"))
    args = parser.parse_args()
    generate(ids=(args.case,) if args.case else IDS)
