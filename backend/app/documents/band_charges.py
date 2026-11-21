"""Source-only charge rows for native service-period tables."""
import re
from dataclasses import dataclass
from datetime import date

from .consistency import parse_printed_amount
from .source_layout import HEADER, HEADER_PATTERNS, IDENT, SUMMARY, Pair, flat, header_shape, quote_forms
from .stacked_layout import LINE_NET, QUANTITY, Charge, below, pair

ITEM_HEADING = re.compile(r"service\s+period\s*/\s*item", re.I)
RATE_HEADING = re.compile(r"(?:(?:net|unit)\s+)*(?:rate|price)(?: \(([A-Z]{3})\))?", re.I)
FUSED = re.compile(r"(\S+)\s+/\s+(.+)")
HEADINGS = {"item": ITEM_HEADING, "qty": QUANTITY, "rate": RATE_HEADING, "net": LINE_NET}

# Labels that may close the charge area: the repository's own header vocabulary for net, tax and total.
NET_CHARGES = r"net\s+(?:service\s+)?charges"
SUMMARY_LABELS = {
    "net": (HEADER_PATTERNS["net"], re.compile(rf"{NET_CHARGES}\s*:?", re.I)),
    "tax": (HEADER_PATTERNS["tax"],),
    "total": (HEADER_PATTERNS["total"],),
}
EDGE = 8        # right-edge alignment of a number with its heading
ITEM_EDGE = 22  # left-edge alignment of item-column cells
LABEL_GAP = (4, 185)  # same label-to-amount distance the existing header association allows

MONTHS = {name.casefold(): index for index, name in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1
)}
PERIOD = re.compile(r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})")


def is_service_period(text):
    match = PERIOD.fullmatch(text)
    if not match:
        return False
    start, end, month, year = match.groups()
    month_number = MONTHS.get(month.casefold())
    if month_number is None:
        return False
    try:
        return date(int(year), month_number, int(start)) <= date(int(year), month_number, int(end))
    except ValueError:
        return False


def summary_role(text):
    return next((role for role, patterns in SUMMARY_LABELS.items() if any(p.fullmatch(text) for p in patterns)), None)


def band_charges(rows):
    """Return None for an unrelated layout or () for an unresolved service table."""
    table = service_period_table(rows)
    return table.charges if isinstance(table, ServicePeriodTable) else table


@dataclass(frozen=True)
class ServicePeriodTable:
    charges: tuple[Charge, ...]
    item_x: float
    net: Pair | None


def service_period_table(rows):
    """Read a complete native charge table and its separately labelled summary net."""
    cells = [cell for row in rows for cell in row]
    found = {name: [(cell, m) for cell in cells if (m := pattern.fullmatch(cell.text))]
             for name, pattern in HEADINGS.items()}
    if not found["item"]:
        return None
    if any(len(group) != 1 for group in found.values()):
        return ()
    item, qty, rate, net = (found[name][0][0] for name in HEADINGS)
    heading = (item, qty, rate, net)
    if (max(c.y for c in heading) - min(c.y for c in heading) > 3
            or any(a.rect[2] > b.rect[0] for a, b in zip(heading, heading[1:]))):
        return ()
    denominations = {m[1].upper() for name in ("rate", "net") for _, m in found[name] if m[1]}
    if len(denominations) > 1:
        return ()  # competing printed denominations
    currency = denominations.pop() if denominations else None
    bottom = max(c.rect[3] for c in heading)
    numeric = {"qty": qty, "rate": rate, "net": net}

    def in_item_column(cell):
        return abs(cell.rect[0] - item.rect[0]) <= ITEM_EDGE

    def is_amount(cell):
        return parse_printed_amount(cell.text) is not None

    body = sorted((c for c in cells if c.rect[0] >= item.rect[0] - ITEM_EDGE and c.rect[1] >= bottom
                   and all(c is not h for h in heading)), key=lambda c: c.y)
    anchors = [c for c in body if in_item_column(c) and (m := FUSED.fullmatch(c.text)) and IDENT.fullmatch(m[1])]
    if not 0 < len(anchors) <= 50:
        return ()
    centers = [a.y for a in anchors]
    last = centers[-1] + ((centers[-1] - centers[-2]) / 2 if len(centers) > 1 else 40)
    bounds = [bottom, *((a + b) / 2 for a, b in zip(centers, centers[1:])), last]

    charges, used = [], set()
    for k, anchor in enumerate(anchors):
        band = [c for c in body if bounds[k] <= c.y < bounds[k + 1]]
        captions = [c for c in band if in_item_column(c) and c is not anchor]
        if (len(captions) != 1 or captions[0].rect[3] > anchor.rect[1]
                or not is_service_period(captions[0].text)):
            return ()
        cols = {}
        for name, head in numeric.items():
            hit = [c for c in band if abs(c.rect[2] - head.rect[2]) <= EDGE and not in_item_column(c)]
            if len(hit) != 1:
                return ()
            cols[name] = hit[0]
        if {id(cell) for cell in (*captions, anchor, *cols.values())} != {id(cell) for cell in band}:
            return ()  # an unexplained cell inside this charge
        amounts = {name: parse_printed_amount(c.text) for name, c in cols.items()}
        if not all(amounts.values()) or amounts["qty"][1]:
            return ()
        code, description = FUSED.fullmatch(anchor.text).groups()
        used.update(id(c) for c in band)
        charges.append(Charge((description, code, cols["qty"].text, cols["rate"].text, cols["net"].text),
                              " ".join(c.text for c in (*captions, anchor, cols["qty"], cols["rate"], cols["net"])),
                              currency))

    unused = [cell for cell in body if id(cell) not in used]
    if any(cell.rect[1] < max(anchors[-1].rect[3], last) for cell in unused):
        return ()  # Summary and footer cells belong below all charges.

    # Bind each amount in the summary to exactly one supported label on its own row.
    summary = {}
    footer = []
    for cell in unused:
        role = summary_role(cell.text)
        if role:
            if role in summary:
                return ()
            neighbors = [other for other in unused if other is not cell and abs(other.y - cell.y) <= 3]
            if len(neighbors) != 1:
                return ()
            amount = neighbors[0]
            if (not is_amount(amount) or not LABEL_GAP[0] <= amount.rect[0] - cell.rect[2] <= LABEL_GAP[1]
                    or amount.rect[2] > net.rect[2] + EDGE or in_item_column(cell)):
                return ()
            summary[role] = (cell, amount)
        elif re.fullmatch(r"\d{1,2}\s*/\s*\d{1,2}", cell.text):
            footer.append(cell)
    if list(summary) not in (["net", "total"], ["net", "tax", "total"]):
        return ()
    total_end = max(cell.rect[3] for cell in summary["total"])
    if len(footer) > 1 or any(cell.rect[1] <= total_end for cell in footer):
        return ()
    accounted = {id(cell) for pair in summary.values() for cell in pair} | {id(cell) for cell in footer}
    if any(id(cell) not in accounted for cell in unused):
        return ()
    label, amount = summary["net"]
    net_pair = pair(label, amount) if re.fullmatch(rf"{NET_CHARGES}\s*:?", label.text, re.I) else None
    return ServicePeriodTable(tuple(charges), item.rect[0], net_pair)


SERVICE_ROLES = {
    "invoice_date": "issued",
    "po_reference": r"customer\s+po",
    "net": NET_CHARGES,
}
LEGAL_SUFFIX = re.compile(r"(?:pvt\.?\s+ltd\.?|private\s+limited|limited|ltd\.?)", re.I)


def service_period_headers(rows, table):
    """Map the masthead and its labelled sidebar independently of extracted facts."""
    cells = [cell for row in rows for cell in row]
    left = [cell for cell in cells if cell.rect[2] < table.item_x]
    titles = [cell for cell in left if flat(cell.text) == "service invoice"]
    if len(titles) != 1:
        return {}, set()
    title = titles[0]
    column = [cell for cell in left if abs(cell.rect[0] - title.rect[0]) <= 7]
    # The issue date and customer PO belong to the same metadata column as
    # the invoice identifier and billing currency, above any footer.
    sidebar_labels = ("invoice number", "issued", "customer po", "billing currency")
    sidebar = [[cell for cell in column if flat(cell.text).rstrip(":") == role] for role in sidebar_labels]
    valid_sidebar = all(len(group) == 1 for group in sidebar) and (
        title.y < sidebar[0][0].y < sidebar[1][0].y < sidebar[2][0].y < sidebar[3][0].y
    )
    result, ambiguous = {}, set()
    for field, alias in SERVICE_ROLES.items():
        labels = [cell for cell in cells if re.fullmatch(rf"{alias}\s*:?", cell.text, re.I)]
        if not labels:
            continue
        role = rf"(?:(?:revised|final|corrected)\s+)*(?:{HEADER[field]}|{alias})"
        if sum(bool(re.fullmatch(rf"{role}(?:\s*:\s*.*)?", cell.text, re.I)) for cell in cells) != 1:
            ambiguous.add(field)
            continue
        if field == "net":
            if table.net and not any(SUMMARY.fullmatch(cell.text) and cell.y < table.net.cell.y for cell in cells):
                result[field] = [table.net]
            continue
        label = labels[0]
        if not valid_sidebar or label not in column:
            continue
        next_cells = [cell for cell in left if label.y < cell.y <= label.y + 30]
        if len(next_cells) == 1:
            value = next_cells[0]
            if value in column and below(label, value, 30) and header_shape(field, value.text):
                result[field] = [pair(label, value)]

    masthead = [cell for cell in left if cell.y < title.y]
    buyers = [cell for cell in cells if re.fullmatch(r"bill\s+to\s*:?", cell.text, re.I)]
    has_seller_label = any(re.fullmatch(rf"(?:{HEADER['vendor_name_raw']}|seller|issued by)(?:\s*:\s*.*)?", cell.text, re.I)
                           for cell in cells)
    if (len(masthead) == 2 and all(cell in column for cell in masthead) and len(buyers) == 1
            and buyers[0].rect[0] >= table.item_x and buyers[0].y < title.y and not has_seller_label):
        name, suffix = masthead
        buyer_names = [cell for cell in cells if cell.rect[0] >= table.item_x
                       and below(buyers[0], cell, 30) and header_shape("vendor_name_raw", cell.text)]
        printed = f"{name.text} {suffix.text}"
        if (len(buyer_names) == 1 and flat(buyer_names[0].text) != flat(printed)
                and below(name, suffix, 38) and below(suffix, title, 64)
                and header_shape("vendor_name_raw", name.text) and LEGAL_SUFFIX.fullmatch(suffix.text)
                and not any(flat(printed) == flat(cell.text) for cell in cells)):
            result["vendor_name_raw"] = [Pair(printed, quote_forms((name.text, suffix.text)), source_quote=printed)]
    return result, ambiguous
