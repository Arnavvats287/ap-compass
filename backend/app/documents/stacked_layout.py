"""Association of native charge tables with a description and a stacked item code."""
from dataclasses import dataclass
import re

from .consistency import HEADER_LABELS, parse_printed_amount
from .source_layout import IDENT, SUMMARY, Cell, Pair, clean, flat, header_shape, quote_forms, table_end

ITEM = re.compile(r"(?:billed item|item\s*/\s*stock code)", re.I)
QUANTITY = re.compile(r"(?:qty\.?|quantity|units)", re.I)
RATE = re.compile(r"(?:unit (?:net|price)|net unit price)(?: \(([A-Z]{3})\))?", re.I)
PER_UNIT = re.compile(r"net\s*/\s*([a-z]{2,20})", re.I)
LINE_NET = re.compile(r"(?:line net|extended net|line amount)(?: \(([A-Z]{3})\))?", re.I)
QUALIFIED_NET = re.compile(rf"{HEADER_LABELS['net']} \(([A-Z]{{3}})\)", re.I)
QUALIFIED_TAX = re.compile(rf"{HEADER_LABELS['tax']} \(([A-Z]{{3}})\)", re.I)
SUMMARY_TOTAL = re.compile(rf"(?:{HEADER_LABELS['total']}|balance due)", re.I)


@dataclass(frozen=True)
class Charge:
    values: tuple[str, str, str, str, str]
    source_quote: str
    currency: str | None


CHARGE_FIELDS = ("description", "item_code", "qty", "unit_price_net", "net")


def aligned(label: Cell, value: Cell):
    return min(abs(label.rect[edge] - value.rect[edge]) for edge in (0, 2)) <= 7


def below(label: Cell, value: Cell, limit: int):
    return label.rect[3] <= value.rect[1] and value.y - label.y <= limit and aligned(label, value)


def pair(label: Cell, cell: Cell):
    quote = f"{label.text} {cell.text}"
    return Pair(cell.text, quote_forms((label.text, cell.text)), cell, quote)


def stacked_heading(row):
    """Recognize fixed columns, or a quantity unit explicitly echoed in the rate header."""
    if len(row) != 4 or not clean(row) or not ITEM.fullmatch(row[0].text):
        return None
    rate = RATE.fullmatch(row[2].text)
    net = LINE_NET.fullmatch(row[3].text)
    unit = PER_UNIT.fullmatch(row[2].text)
    if not net or not (
        (QUANTITY.fullmatch(row[1].text) and rate)
        or (unit and flat(row[1].text) == flat(unit[1]) + "s")
    ):
        return None
    denominations = {m[1].upper() for m in (rate, net) if m and m[1]}
    return (denominations.pop() if denominations else None,) if len(denominations) <= 1 else None


def qualified_summary_labels(row):
    if len(row) != 3 or not clean(row):
        return None
    net, tax = QUALIFIED_NET.fullmatch(row[0].text), QUALIFIED_TAX.fullmatch(row[1].text)
    if net and tax and net[1].upper() == tax[1].upper() and SUMMARY_TOTAL.fullmatch(row[2].text):
        return net[1].upper()
    return None


def charge_values(header, row):
    if len(row) != 4 or not clean(row) or not all(aligned(label, cell) for label, cell in zip(header, row)):
        return None
    if not any(char.isalpha() for char in row[0].text):
        return None
    amounts = [parse_printed_amount(cell.text) for cell in row[1:]]
    if not all(amounts) or amounts[0][1]:
        return None
    return tuple(cell.text for cell in row)


def stacked_charges(rows):
    """Return None for no recognized heading, () for incomplete or competing tables."""
    found = [(index, meta[0]) for index, row in enumerate(rows) if (meta := stacked_heading(row))]
    if not found:
        return None
    if len(found) != 1:
        return ()
    head, denomination = found[0]
    header = rows[head]
    result = []
    index = head + 1
    while index < len(rows):
        row = rows[index]
        if table_end(row) or qualified_summary_labels(row):
            # A charge after invoice totals is ambiguous. Do not ignore it.
            return tuple(result) if not any(charge_values(header, later) for later in rows[index + 1:]) else ()
        values = charge_values(header, row)
        code_row = rows[index + 1] if index + 1 < len(rows) else ()
        if not values or len(code_row) != 1 or not below(row[0], code_row[0], 26) or not IDENT.fullmatch(code_row[0].text):
            return ()
        code = code_row[0].text
        result.append(Charge((values[0], code, *values[1:]), " ".join((*values, code)), denomination))
        if len(result) > 50:
            return ()
        index += 2
    return ()


def invoice_metadata(rows):
    """Only the top invoice heading/band can label an adjacent invoice identifier or issue date."""
    result = {}
    for row, following in zip(rows[:6], rows[1:7]):
        if not clean(row) or not clean(following):
            continue
        labels = {flat(cell.text): cell for cell in row}
        if "invoice" not in labels:
            continue
        for field, role in (("invoice_number", "invoice"), ("invoice_date", "issued")):
            label = labels.get(role)
            if label is None or (field == "invoice_date" and "due" not in labels):
                continue
            for cell in following:
                if any(other is not label and aligned(other, cell) for other in row):
                    continue
                if (below(label, cell, 30) and header_shape(field, cell.text)
                        and (field != "invoice_number" or "-" in cell.text
                             and not header_shape("invoice_date", cell.text)
                             and not flat(cell.text).startswith(("po-", "po_")))):
                    result.setdefault(field, []).append(pair(label, cell))
    return result


def currency_summary(rows):
    """Labelled net/tax/balance columns, with a matching explicit currency on gross."""
    found = []
    for index, row in enumerate(rows):
        denomination = qualified_summary_labels(row)
        if not denomination:
            continue
        found.append((index, denomination))
    fields = ("net", "tax", "total", "currency")
    if not found:
        return {}, None
    unresolved = {field: [Pair("")] for field in fields}
    if len(found) != 1:
        return unresolved, None
    index, denomination = found[0]
    if index + 1 == len(rows) or any(SUMMARY.fullmatch(cell.text) for row in rows[:index] for cell in row):
        return unresolved, None
    if not any(stacked_heading(row) for row in rows[:index]):
        return unresolved, None
    labels, values = rows[index:index + 2]
    if len(values) != 3 or not clean(values) or not all(below(label, cell, 24) for label, cell in zip(labels, values)):
        return unresolved, None
    amounts = tuple(parse_printed_amount(cell.text) for cell in values)
    if (not all(amounts) or amounts[2][1] != denomination
            or any(amount[1] not in (None, denomination) for amount in amounts)):
        return unresolved, None
    result = {field: [pair(label, cell)] for field, label, cell in zip(("net", "tax", "total"), labels, values)}
    result["currency"] = [Pair(denomination, quote_forms((labels[0].text,)), labels[0], labels[0].text)]
    return result, denomination
