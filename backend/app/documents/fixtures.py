"""Development-only generation of the authorized image-only manifest fixture."""
from io import BytesIO
import json
from pathlib import Path


def native_case(case, *, extra_text=None):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=A4, invariant=1)
    x, y = 48, 790
    pdf.setFont("Helvetica-Bold", 23)
    pdf.drawString(x, y, "INVOICE")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(x, y - 27, "SYNTHETIC DEMO - Fictional supplier and transaction")
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(x, 690, case["vendor_name"])
    pdf.setFont("Helvetica", 11)
    rows = [f"Invoice number: {case['invoice_number']}", f"Invoice date: {case['invoice_date']}",
            f"Purchase order: {case['po_reference']}", f"Currency: {case['currency']}"]
    for line in case["lines"]:
        rows += [line["description"], f"Item code: {line['item_code']}", f"Quantity: {line['qty']}",
                 f"Unit price (net): INR {line['unit_price_net']}"]
    rows += [f"Net subtotal: INR {case['net']}", f"Tax (synthetic GST): INR {case['tax']}",
             f"Invoice total: INR {case['gross']}"]
    if case.get("bank_instructions"):
        rows += [f"Account number: {case['bank_instructions']['account']}", f"IFSC: {case['bank_instructions']['ifsc']}"]
    y = 650
    for row in rows:
        pdf.drawString(x, y, row)
        y -= 29
    if extra_text:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x, y - 10, extra_text)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(x, 70, "Synthetic native-text source for the image-only test fixture. No payment authority.")
    pdf.showPage()
    pdf.save()
    return stream.getvalue()


def image_only(native_bytes):
    import pymupdf
    with pymupdf.open(stream=native_bytes, filetype="pdf") as original, pymupdf.open() as result:
        for page in original:
            image = page.get_pixmap(dpi=120, colorspace=pymupdf.csRGB, alpha=False).tobytes("png")
            target = result.new_page(width=page.rect.width, height=page.rect.height)
            target.insert_image(target.rect, stream=image)
        return result.tobytes(garbage=4, deflate=True)


def main():
    root = Path(__file__).resolve().parents[3]
    case = next(c for c in json.loads((root / "data/fixture_manifest.json").read_text())["fixture_cases"] if c["id"] == "SCAN_CONFLICT")
    target = root / "tests/fixtures/SCAN_CONFLICT.pdf"
    target.write_bytes(image_only(native_case(case)))
    print("Generated SCAN_CONFLICT.pdf from unchanged manifest; stated total preserved.")


if __name__ == "__main__":
    main()
