"""Bounded invoice-header consistency checks over independently inspected native lines."""
from decimal import Decimal
import re


# Full-line labels exclude previous/customer balances and line-level subtotals.
HEADER_LABELS = {
    "invoice_number": r"invoice\s*(?:number|no\.?|#)",
    "net": r"(?:net\s*subtotal|subtotal|invoice\s*net|net\s*(?:amount|total)|taxable\s*(?:amount|value))",
    "tax": r"(?:tax(?:\s*\([^)]{1,40}\))?|gst|vat)",
    "total": r"(?:invoice\s*total|grand\s*total|amount\s*due|gross(?:\s*total)?|total\s*(?:payable|amount)?)",
}
QUALIFIER = r"(?:(?:revised|final|corrected)\s+){0,2}"
PATTERNS = {
    field: re.compile(rf"\s*{QUALIFIER}{labels}\s*:\s*(.+?)\s*", re.I)
    for field, labels in HEADER_LABELS.items()
}
AMOUNT = re.compile(
    r"(?:(INR|USD|EUR|GBP|Rs\.?|₹|\$|€|£)\s*)?"
    r"(-?(?:[0-9]{1,18}|[0-9]{1,3}(?:,[0-9]{3}){1,5}|[0-9]{1,2}(?:,[0-9]{2}){1,6},[0-9]{3})"
    r"(?:\.[0-9]{1,6})?)", re.I
)
CURRENCIES = {"₹": "INR", "RS": "INR", "RS.": "INR", "$": "USD", "€": "EUR", "£": "GBP"}


def disputed_headers(pages):
    """Identify disagreement; never pick a replacement value or evaluate eligibility."""
    values = {field: set() for field in PATTERNS}
    currencies = {field: set() for field in PATTERNS}
    for page in pages:
        if page.route != "native_text":
            continue
        for line, _ in page.lines:
            for field, pattern in PATTERNS.items():
                match = pattern.fullmatch(line)
                if not match:
                    continue
                raw = match[1]
                if field == "invoice_number":
                    values[field].add(" ".join(raw.split()).casefold())
                elif amount := AMOUNT.fullmatch(raw):
                    currency, number = amount.groups()
                    values[field].add(Decimal(number.replace(",", "")))
                    if currency:
                        currencies[field].add(CURRENCIES.get(currency.upper(), currency.upper()))
                break
    return {field for field in PATTERNS if len(values[field]) > 1 or len(currencies[field]) > 1}
