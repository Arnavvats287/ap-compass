"""Small parser-owned associations for native labels and rectangular tables."""
from collections import Counter, defaultdict
from dataclasses import dataclass
import re

from .consistency import (
    AMOUNT, GENERIC_PAYABLE, HEADER_LABELS, INVOICE_DUE_LABEL, PATTERNS, PAYABLE_ALIASES, QUALIFIER, inline_amount,
)
from .limits import MAX_LAYOUT_LINES


def flat(text):
    return " ".join(text.split()).casefold()


def layout_quote(text):
    return re.sub(r"\s*\|\s*", "|", flat(text))


def quote_forms(parts):
    """Allow a separator between exact printed cells, preserving their content and order."""
    forms = {layout_quote(" ".join(parts))}
    if all("|" not in part for part in parts):
        forms.add(layout_quote("|".join(parts)))
    return frozenset(forms)


SUMMARY = re.compile(r"(?:(?:customer|payment)\s+)?account\s+(?:summary|statement)\s*:?|"
                     r"(?:statement\s+(?:summary|activity|totals?)|payment\s+history)\s*:?", re.I)
INVOICE_DUE_IN_SUMMARY = re.compile(rf"{QUALIFIER}{INVOICE_DUE_LABEL}\s*:?", re.I)
PAYABLE_ALIAS_LABEL = re.compile(rf"{QUALIFIER}{PAYABLE_ALIASES}\s*:?", re.I)
GENERIC_PAYABLE_LABEL = re.compile(rf"{QUALIFIER}{GENERIC_PAYABLE}\s*:?", re.I)
HEADER = {
    **HEADER_LABELS,
    "vendor_name_raw": r"(?:supplier|vendor|from|billed by)",
    "invoice_date": r"invoice\s+date",
    "currency": r"(?:billing\s+)?currency",
    "bank_instructions.account": r"bank\s+account(?:\s*(?:number|no\.?|#))?",
    "bank_instructions.ifsc": r"ifsc(?:\s*code)?",
}
HEADER_PATTERNS = {field: re.compile(rf"{QUALIFIER}{label}\s*:?", re.I) for field, label in HEADER.items()}
INLINE_HEADERS = {field: re.compile(rf"{QUALIFIER}{label}\s*:\s*\S.*", re.I) for field, label in HEADER.items()}
NOT_VALUE = re.compile(r"(?:bill(?:ed)?\s+to|ship\s+to|sold\s+to|buyer|customer|remit\s+to|"
                       r"remittance\s+address|description|item\s+code|qty\.?|purchase\s+order)\s*:?.*", re.I)
OTHER_ROLE = re.compile(r"(?:(?:previous|prior|opening|closing|combined|customer)\s+(?:account\s+)?balance|"
                        r"(?:payment\s+)?account\s+(?:number|reference|total|balance)|"
                        r"settlement\s+balance|statement\s+total|(?:unapplied|available)\s+credit|"
                        r"service\s+date|(?:billing|shipping)\s+address)\s*:?", re.I)
IDENT = re.compile(r"(?=.*\d)[a-z\d][a-z\d./_-]{0,79}", re.I | re.ASCII)
DATE = re.compile(r"(?:\d{4}-\d{2}-\d{2}|\d{1,2}\s+[a-z]+\s+\d{4}|[a-z]+\s+\d{1,2},\s+\d{4})", re.I)
TABLE = {
    "item_code": r"(?:item\s+code|sku)",
    "description": r"(?:item\s+)?description",
    "service_period": r"service\s+period",
    "qty": r"(?:quantity|qty\.?)",
    "unit_price_net": r"(?:unit\s+net(?:\s+(?:price|rate))?|(?:net\s+)?unit\s+(?:price|rate)(?:\s*\(net\))?)",
    "net": r"(?:line\s+(?:net|amount)|net\s+amount)",
}
TABLE_PATTERNS = {field: re.compile(label, re.I) for field, label in TABLE.items()}
REQUIRED_COLUMNS = {"item_code", "qty", "unit_price_net"}


@dataclass(frozen=True)
class Cell:
    text: str
    rect: tuple[float, float, float, float]

    @property
    def y(self):
        return (self.rect[1] + self.rect[3]) / 2

    @property
    def x(self):
        return (self.rect[0] + self.rect[2]) / 2


@dataclass(frozen=True)
class Pair:
    value: str
    quotes: frozenset[str] = frozenset()
    cell: Cell | None = None


def rows_for(page):
    if not 0 < len(page.lines) == len(page.line_rects) <= MAX_LAYOUT_LINES:
        return ()
    if any(text.strip() and rect is None for (text, _), rect in zip(page.lines, page.line_rects)):
        return ()
    cells = sorted((Cell(text.strip(), rect) for (text, _), rect in zip(page.lines, page.line_rects)
                    if rect and text.strip()), key=lambda cell: cell.y)
    rows = []
    for cell in cells:
        if rows and cell.y - rows[-1][0].y <= 3:
            rows[-1].append(cell)
        else:
            rows.append([cell])
    return tuple(tuple(sorted(row, key=lambda cell: cell.rect[0])) for row in rows)


def clean(row):
    return all(left.rect[2] <= right.rect[0] for left, right in zip(row, row[1:]))


def matches(text, patterns):
    return next((name for name, pattern in patterns.items() if pattern.fullmatch(text)), None)


def has_left_label(row, index):
    if index == 0:
        return False
    left, value = row[index - 1], row[index]
    return (4 <= value.rect[0] - left.rect[2] <= 185
            and bool(NOT_VALUE.fullmatch(left.text) or OTHER_ROLE.fullmatch(left.text)
                     or matches(left.text, HEADER_PATTERNS) or matches(left.text, TABLE_PATTERNS)))


def table_header_band(row):
    labels = {field for cell in row if (field := matches(cell.text, TABLE_PATTERNS))}
    return len(labels) >= 2 and bool({"item_code", "qty"} & labels)


def header_shape(field, text):
    if field in {"net", "tax", "total"}:
        return bool(AMOUNT.fullmatch(text))
    if field in {"invoice_number", "po_reference"}:
        return bool(IDENT.fullmatch(text))
    if field == "invoice_date":
        return bool(DATE.fullmatch(text))
    if field == "currency":
        return bool(re.fullmatch(r"[A-Z]{3}", text))
    if field == "bank_instructions.account":
        return bool(re.fullmatch(r"[0-9][0-9 -]{3,30}", text))
    if field == "bank_instructions.ifsc":
        return bool(IDENT.fullmatch(text))
    return (2 <= len(text.split()) <= 10 and not any(ch.isdigit() for ch in text)
            and not NOT_VALUE.fullmatch(text) and not re.search(r"\b(?:invoice|address|statement)\b", text, re.I))


def has_amount_column_label_above(rows, row_index, value):
    for index in range(row_index - 1, -1, -1):
        row = rows[index]
        if value.y - row[0].y > 29:
            break
        if any(cell.rect[3] <= value.rect[1] and abs(cell.rect[0] - value.rect[0]) <= 7
               and (OTHER_ROLE.fullmatch(cell.text) or matches(cell.text, HEADER_PATTERNS)
                    or matches(cell.text, TABLE_PATTERNS)) for cell in row):
            return True
    return False


def invoice_amount_row(field, row, label):
    if abs(row[0].rect[0] - label.rect[0]) > 7 or abs(row[0].y - label.y) > 90:
        return False
    if len(row) == 1:
        return inline_amount(field, row[0].text)
    return (len(row) == 2 and clean(row) and bool(HEADER_PATTERNS[field].fullmatch(row[0].text))
            and bool(AMOUNT.fullmatch(row[1].text)))


def aligned_tax_summary(rows, index, label, amount):
    """Recognize a two-column invoice summary with a wider tax row."""
    if index == 0 or index + 1 == len(rows) or len(rows[index]) != 2 or not AMOUNT.fullmatch(amount.text):
        return False
    before, after = rows[index - 1], rows[index + 1]
    if abs((label.y - before[0].y) - (after[0].y - label.y)) > 4:
        return False
    for row, field in ((before, "net"), (after, "total")):
        if len(row) != 2 or not clean(row):
            return False
        other_label, other_amount = row
        if (not HEADER_PATTERNS[field].fullmatch(other_label.text) or not AMOUNT.fullmatch(other_amount.text)
                or abs(label.y - other_label.y) > 36 or abs(label.rect[0] - other_label.rect[0]) > 7
                or abs(amount.rect[2] - other_amount.rect[2]) > 4
                or not 4 <= other_amount.rect[0] - other_label.rect[2] <= 185):
            return False
    return True


def adjacent(rows, row_index, col, label, field):
    row = rows[row_index]
    if not clean(row):
        return ()
    options = []
    if col + 1 < len(row):
        right = row[col + 1]
        gap = right.rect[0] - label.rect[2]
        wide_tax = field == "tax" and 185 < gap <= 225 and aligned_tax_summary(rows, row_index, label, right)
        if (4 <= gap <= 185 or wide_tax) and not (
                (field == "total" or wide_tax) and has_amount_column_label_above(rows, row_index, right)):
            options.append(right)
    for index in range(row_index + 1, len(rows)):
        below = rows[index]
        if min(cell.y for cell in below) - label.y > 29:
            break
        aligned = [(i, cell) for i, cell in enumerate(below) if abs(cell.rect[0] - label.rect[0]) <= 7]
        if aligned:
            if clean(below):
                options.extend(cell for i, cell in aligned
                               if cell.rect[1] >= label.rect[3] and not has_left_label(below, i))
            break
    return tuple(Pair(cell.text, quote_forms((label.text, cell.text))
                      | {layout_quote(f"{label.text.rstrip(':')}: {cell.text}")}, cell) for cell in options
                 if not matches(cell.text, HEADER_PATTERNS) and header_shape(field, cell.text))


def split_headers(rows, *, summary_payables=None):
    observations = defaultdict(list)
    inline_fields = set()
    summary = False
    for index, row in enumerate(rows):
        summary |= any(SUMMARY.fullmatch(cell.text) for cell in row)
        if table_header_band(row):
            continue
        for col, label in enumerate(row):
            revised = re.match(r"(?:revised|final|corrected)\s", label.text, re.I)
            if inline := matches(label.text, INLINE_HEADERS):
                if not summary or revised or inline.startswith("bank_instructions."):
                    inline_fields.add(inline)
            field = matches(label.text, HEADER_PATTERNS)
            legacy_revision = revised and not PAYABLE_ALIAS_LABEL.fullmatch(label.text)
            if field and (not summary or legacy_revision or field.startswith("bank_instructions.")):
                generic = field == "total" and GENERIC_PAYABLE_LABEL.fullmatch(label.text)
                if generic and not (index >= 2 and invoice_amount_row("net", rows[index - 2], label)
                                    and invoice_amount_row("tax", rows[index - 1], label)):
                    pairs = ()
                else:
                    pairs = adjacent(rows, index, col, label, field)
                # An unresolved label counts as a competing association, even beside a supported label.
                observations[field].extend(pairs or (Pair(""),))
            elif field == "total" and summary_payables is not None and INVOICE_DUE_IN_SUMMARY.fullmatch(label.text):
                # An invoice-specific restatement can show a conflict. Its
                # placement in the account section cannot supply positive support.
                summary_payables.append(adjacent(rows, index, col, label, field))
    used_cells = Counter(pair.cell for pairs in observations.values() for pair in pairs if pair.cell is not None)
    for field, pairs in observations.items():
        if field in inline_fields or any(used_cells[pair.cell] > 1 for pair in pairs):
            pairs.append(Pair(""))
    return dict(observations)


def table_columns(row):
    labelled = [(field, cell) for cell in row if (field := matches(cell.text, TABLE_PATTERNS))]
    names = [field for field, _ in labelled]
    return labelled if len(labelled) == len(row) and len(names) == len(set(names)) and REQUIRED_COLUMNS <= set(names) else ()


def table_end(row):
    amount_fields = ("net", "tax", "total")
    if len(row) == 1:
        text = row[0].text
        return bool(SUMMARY.fullmatch(text) or any(
            (match := PATTERNS[field].fullmatch(text)) and AMOUNT.fullmatch(match[1]) for field in amount_fields))
    return (len(row) == 2 and clean(row) and matches(row[0].text, HEADER_PATTERNS) in amount_fields
            and bool(AMOUNT.fullmatch(row[1].text)))


def charge_cells(row, labels, edges):
    if not clean(row):
        return None
    cells = {}
    for cell in row:
        column = sum(cell.x > edge for edge in edges)
        key, label = labels[column]
        if (key in cells or (column and cell.rect[0] < edges[column - 1]) or
                (column < len(edges) and cell.rect[2] > edges[column]) or
                (column == 0 and abs(cell.rect[0] - label.rect[0]) > 22)):
            return None
        cells[key] = cell.text
    if not REQUIRED_COLUMNS <= cells.keys() or not IDENT.fullmatch(cells["item_code"]):
        return None
    quantity = AMOUNT.fullmatch(cells["qty"])
    if (not quantity or quantity[1] or
            any(not AMOUNT.fullmatch(cells[field]) for field in {"unit_price_net", "net"} & cells.keys())):
        return None
    return cells


def table_rows(rows):
    """None means no recognized header. An empty tuple means recognized but unresolved."""
    headers = [index for index, row in enumerate(rows) if REQUIRED_COLUMNS <= {
        matches(cell.text, TABLE_PATTERNS) for cell in row}]
    if not headers:
        return None
    if len(headers) != 1:
        return ()
    index = headers[0]
    previous = rows[index]
    labels = table_columns(previous)
    if not labels or not clean(previous):
        return ()
    edges = tuple((a.rect[2] + b.rect[0]) / 2 for (_, a), (_, b) in zip(labels, labels[1:]))
    result = []
    closed = False
    for row in rows[index + 1:]:
        if table_end(row):
            closed = True
            continue
        cells = charge_cells(row, labels, edges)
        if closed:
            # Another charge-shaped row after a totals band leaves the table extent unclear.
            if cells:
                return ()
            continue
        if not cells or min(cell.rect[1] for cell in row) < max(cell.rect[3] for cell in previous):
            return ()
        result.append(TableRow(cells, quote_forms(tuple(cell.text for cell in row))))
        previous = row
        if len(result) > 50:
            return ()
    return tuple(result)


@dataclass(frozen=True)
class TableRow:
    values: dict[str, str]
    quotes: frozenset[str]


def unique_quotes(table):
    return {quote for quote, count in Counter(quote for row in table for quote in row.quotes).items() if count == 1}
