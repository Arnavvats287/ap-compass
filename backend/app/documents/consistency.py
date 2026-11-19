"""Bounded invoice-header consistency checks over independently inspected native lines."""
from decimal import Decimal
import re


# Full-line labels exclude previous/customer balances and line-level subtotals.
HEADER_LABELS = {
    "invoice_number": r"invoice\s*(?:number|no\.?|#)",
    "po_reference": r"(?:purchase\s*order|p\.?o\.?\s*(?:number|no\.?|#|reference)?)",
    "net": r"(?:net\s*subtotal|subtotal|invoice\s*net|net\s*(?:amount|total)|taxable\s*(?:amount|value))",
    "tax": r"(?:tax(?:\s*\([^)]{1,40}\))?|(?:gst|vat)(?:\s*\(?\d{1,2}(?:\.\d+)?%\)?)?)",
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


def parse_printed_amount(text: str) -> tuple[Decimal, str | None] | None:
    """Read the existing amount grammar without inferring a denomination."""
    match = AMOUNT.fullmatch(text.strip())
    if not match:
        return None
    prefix, number = match.groups()
    code = prefix.upper() if prefix else None
    return Decimal(number.replace(",", "")), CURRENCIES.get(code, code)


def disputed_headers(pages, split_observations=()):
    """Identify disagreement; never pick a replacement value or evaluate eligibility."""
    values = {field: set() for field in PATTERNS}
    currencies = {field: set() for field in PATTERNS}
    def record(field, raw):
        if field in {"invoice_number", "po_reference"}:
            values[field].add(" ".join(raw.split()).casefold())
        elif amount := parse_printed_amount(raw):
            number, currency = amount
            values[field].add(number)
            if currency:
                currencies[field].add(currency)

    ambiguous = set()
    for observations in split_observations:
        for field in PATTERNS.keys() & observations.keys():
            pairs = observations[field]
            if len(pairs) != 1 or not pairs[0].value:
                ambiguous.add(field)
            for pair in pairs:
                record(field, pair.value)
    for page in pages:
        if page.route != "native_text":
            continue
        for line, _ in page.lines:
            for field, pattern in PATTERNS.items():
                match = pattern.fullmatch(line)
                if not match:
                    continue
                record(field, match[1])
                break
    return ambiguous | {field for field in PATTERNS if len(values[field]) > 1 or len(currencies[field]) > 1}
