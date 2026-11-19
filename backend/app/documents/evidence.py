"""Independent, conservative source support checks; no financial decision rules."""
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
import re

from app.contracts import EvidenceRefV1, ExtractedInvoiceV1
from .consistency import AMOUNT, CURRENCIES, HEADER_LABELS, disputed_headers
from .schema import SourceClaim
from .source_layout import SUMMARY, flat, rows_for, split_headers, table_rows, unique_quotes
from .types import DocumentInspection, ExtractionError

LABELS = {
    **HEADER_LABELS,
    "invoice_date": r"invoice\s*date",
    "currency": r"currency",
    "item_code": r"(?:item\s*code|sku)",
    "qty": r"(?:quantity|qty\.?)",
    "unit_price_net": r"(?:unit\s*price(?:\s*\(net\))?|net\s*unit\s*price)",
    "line_net": r"(?:line\s*net|line\s*amount)",
    "account": r"(?:bank\s*)?account(?:\s*(?:number|no\.?|#))?",
    "ifsc": r"ifsc(?:\s*code)?",
}


def values(invoice):
    result = {name: getattr(invoice, name) for name in (
        "vendor_name_raw", "invoice_number", "invoice_date", "po_reference", "currency", "net", "tax", "total")}
    for i, line in enumerate(invoice.lines):
        for name in ("description", "item_code", "qty", "unit_price_net", "net"):
            result[f"lines[{i}].{name}"] = getattr(line, name)
    if invoice.bank_instructions:
        for name in ("account", "ifsc"):
            result[f"bank_instructions.{name}"] = getattr(invoice.bank_instructions, name)
    return result


def printed_value(text, expected):
    text = text.strip()
    if isinstance(expected, Decimal):
        amount = AMOUNT.fullmatch(text)
        return bool(amount and Decimal(amount[2].replace(",", "")) == expected)
    if isinstance(expected, date):
        for form in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%B %d, %Y"):
            try:
                if datetime.strptime(text, form).date() == expected:
                    return True
            except ValueError:
                pass
        return False
    return flat(text) == flat(str(expected))


def local_support(invoice, field, value, page, claim):
    """Preserve field-specific grounding for existing labelled blocks."""
    quote = flat(claim.quote)
    raw = flat(claim.raw_value)
    if not raw or not printed_value(claim.raw_value, value):
        return False
    source_lines = [text for text, _ in page.lines]
    line_field = re.fullmatch(r"lines\[(\d+)\]\.(description|item_code|qty|unit_price_net|net)", field)
    leaf = field
    scope = source_lines
    if line_field:
        index, leaf = int(line_field[1]), line_field[2]
        item = invoice.lines[index].item_code
        if not item:
            return False
        anchors = [i for i, text in enumerate(source_lines)
                   if (match := re.fullmatch(rf"\s*{LABELS['item_code']}\s*:\s*(.+)", text, re.I))
                   and printed_value(match[1], item)]
        if len(anchors) != 1:
            return False
        start = anchors[0]
        stop = next((i for i in range(start + 1, len(source_lines))
                     if re.match(rf"\s*(?:{LABELS['item_code']}|{LABELS['net']}|{LABELS['total']})\s*:", source_lines[i], re.I)), len(source_lines))
        scope = source_lines[start:stop]
        if leaf == "description":
            scope = source_lines[max(0, start - 1):start]
        if leaf == "net":
            leaf = "line_net"
    elif field.startswith("bank_instructions."):
        leaf = field.split(".")[1]

    candidates = []
    if leaf == "vendor_name_raw":
        labelled = [(text, match[1]) for text in source_lines
                    if (match := re.fullmatch(r"\s*(?:vendor|supplier|from|billed by)\s*:\s*(.+)", text, re.I))]
        if labelled:
            if len(labelled) != 1:
                return False
            candidates = [text for text, printed in labelled if printed_value(printed, value)]
        else:
            headings = [(i, text) for i, (text, size) in enumerate(page.lines) if i < 6 and size >= 14
                        and not re.search(r"\binvoice\b|\bcopy\b", text, re.I)]
            if len(headings) != 1:
                return False
            index, text = headings[0]
            preceding = " ".join(source_lines[max(0, index - 2):index])
            buyer_context = re.search(r"bill(?:ed)?\s*to|ship\s*to|sold\s*to|\bbuyer\b|\bcustomer\b", preceding, re.I)
            if not buyer_context and printed_value(text, value):
                candidates.append(text)
    elif leaf == "description":
        candidates = [text for text in scope if printed_value(text, value)]
    elif leaf in LABELS:
        # Any repeated field label is ambiguous, even when one value matches.
        labelled = [(text, match[1]) for text in scope
                    if (match := re.fullmatch(rf"\s*{LABELS[leaf]}\s*:\s*(.+)", text, re.I))]
        if len(labelled) != 1:
            return False
        if field in {"net", "tax", "total"} and any(SUMMARY.fullmatch(text.strip())
                                                    for text in scope[:scope.index(labelled[0][0])]):
            return False
        candidates = [text for text, printed in labelled if printed_value(printed, value)]
    if len(candidates) != 1:
        return False
    supporting_line = flat(candidates[0])
    # Require the full labelled source line, not just a quoted number somewhere.
    if supporting_line not in quote or raw not in supporting_line:
        return False
    if isinstance(value, Decimal) and not re.search(r"(?<![\d.,])" + re.escape(raw) + r"(?![\d.,])", supporting_line):
        return False
    return True


LINE_FIELD = re.compile(r"lines\[(\d+)\]\.(description|item_code|qty|unit_price_net|net)")


def supported_cell(printed, value, claim, currency=None):
    if not printed_value(printed, value) or not printed_value(claim.raw_value, value):
        return False
    raw, text = flat(claim.raw_value), flat(printed)
    if isinstance(value, Decimal):
        prefix = AMOUNT.fullmatch(printed)[1]
        if prefix and currency and CURRENCIES.get(prefix.upper(), prefix.upper()) != currency.upper():
            return False
        return bool(re.search(r"(?<![\d.,])" + re.escape(raw) + r"(?![\d.,])", text))
    return raw == text


def layout_support(invoice, field, value, claim, headers, table, unique_rows):
    if field in headers:
        pairs = headers[field]
        return (len(pairs) == 1 and pairs[0].quote == flat(claim.quote)
                and supported_cell(pairs[0].value, value, claim, invoice.currency))
    line = LINE_FIELD.fullmatch(field)
    if line and table:
        index, leaf = int(line[1]), line[2]
        row = table[index]
        # Ordinal mapping is allowed only for a complete single table with the same
        # item sequence and description context. The claim must select the row,
        # even when prices, quantities or item codes repeat elsewhere.
        return (row.quote in unique_rows and row.quote == flat(claim.quote) and leaf in row.values
                and supported_cell(row.values[leaf], value, claim, invoice.currency))
    return False


def ground_evidence(invoice: ExtractedInvoiceV1, claims: tuple[SourceClaim, ...],
                    inspection: DocumentInspection) -> ExtractedInvoiceV1:
    pages = {page.number: page for page in inspection.pages}
    native_pages = {number: page for number, page in pages.items() if page.route == "native_text"}
    layouts = {number: rows_for(page) for number, page in native_pages.items()}
    headers = {number: split_headers(rows) for number, rows in layouts.items()}
    tables = {number: table_rows(rows) for number, rows in layouts.items()}
    full_tables = [table for table in tables.values() if table]
    eligible_table = ()
    if len(full_tables) == 1:
        table = full_tables[0]
        if len(table) == len(invoice.lines) and all(
            line.item_code and printed_value(row.values["item_code"], line.item_code)
            and ("description" not in row.values or not line.description or printed_value(row.values["description"], line.description))
            for row, line in zip(table, invoice.lines)
        ):
            eligible_table = table
    located_quotes = {
        number: {pair.quote for group in pairs.values() for pair in group if pair.quote}
                | {row.quote for row in tables[number]}
        for number, pairs in headers.items()
    }
    distinct_rows = unique_quotes(eligible_table)
    if invoice.bank_instructions is None:
        bank_claimed = any(c.field.startswith("bank_instructions.") and c.raw_value for c in claims)
        bank_printed = any(re.fullmatch(rf"\s*(?:{LABELS['account']}|{LABELS['ifsc']})\s*:\s*\S.*", text, re.I)
                           for page in inspection.pages if page.route == "native_text" for text, _ in page.lines)
        bank_split = any(pair.value for pairs in headers.values() for field, group in pairs.items()
                         if field.startswith("bank_instructions.") for pair in group)
        if bank_claimed or bank_printed or bank_split:
            # A detected native instruction or explicit claim makes this omission
            # an invalid extraction response. Never backfill credentials.
            raise ExtractionError("INVALID_RESPONSE")
    disputed = disputed_headers(inspection.pages, headers.values())
    sources = {number: flat(page.native_text) for number, page in native_pages.items()}
    line_counts = {number: Counter(flat(text) for text, _ in page.lines) for number, page in native_pages.items()}
    by_field = defaultdict(list)
    for claim in claims:
        by_field[claim.field].append(claim)
    grounded = []
    for field, value in values(invoice).items():
        matches = by_field.get(field, ())
        claim = matches[0] if matches else None
        page = pages.get(claim.page) if claim else None
        state = "MISSING"
        if value is not None and claim and page and claim.quote and claim.raw_value:
            if page.route != "native_text":
                state = "SOURCE_LOCATED_UNVERIFIED"
            else:
                source, quote = sources[page.number], flat(claim.quote)
                occurrences = source.count(quote) if quote else 0
                if occurrences or quote in located_quotes[page.number]:
                    state = "SOURCE_LOCATED_UNVERIFIED"
                    if field not in disputed and len(matches) == 1:
                        table = eligible_table if tables[page.number] is eligible_table else ()
                        split = headers[page.number]
                        if field in split or (LINE_FIELD.fullmatch(field) and tables[page.number]):
                            supported = layout_support(invoice, field, value, claim, split, table, distinct_rows)
                        else:
                            # A complete source line is distinct from its substring in a longer
                            # statement label. Duplicate complete lines still fail closed.
                            unique = occurrences == 1 or line_counts[page.number][quote] == 1
                            supported = unique and local_support(invoice, field, value, page, claim)
                        if supported:
                            state = "NATIVE_VERIFIED"
        grounded.append(EvidenceRefV1(
            field=field, raw_value=claim.raw_value if claim else None,
            normalized_value=None if value is None else str(value),
            page=claim.page if claim else None, quote=claim.quote if claim else None,
            route=page.route if page else None, evidence_state=state,
        ))
    lines = list(invoice.lines)
    if inspection.route != "native_text":
        for index, line in enumerate(lines):
            key = f"lines[{index}].net"
            ref_index = next(i for i, ref in enumerate(grounded) if ref.field == key)
            ref = grounded[ref_index]
            if line.net is not None and ref.evidence_state != "NATIVE_VERIFIED":
                # A vision-model calculation/claim is not an independently
                # verified document-stated line amount. Keep the raw claim for
                # audit, but leave both the fact and its normalized value unknown.
                lines[index] = line.model_copy(update={"net": None})
                grounded[ref_index] = ref.model_copy(update={"normalized_value": None})
    # This comes from parser routing, never from a provider's field or source claim.
    flags = ("RASTER_CONTENT_UNRESOLVED",) if inspection.route == "mixed" else ()
    return invoice.model_copy(update={
        "lines": tuple(lines),
        "evidence": tuple(grounded),
        "document_integrity_flags": flags,
    })
