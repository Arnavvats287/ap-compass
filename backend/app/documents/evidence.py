"""Independent, conservative source support checks; no financial decision rules."""
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
import re

from app.contracts import EvidenceRefV1, ExtractedInvoiceV1
from .consistency import HEADER_LABELS, PAYABLE_ALIASES, QUALIFIER, disputed_headers, inline_amount, parse_printed_amount
from .schema import SourceClaim
from .source_layout import GENERIC_PAYABLE_LABEL, SUMMARY, flat, inline_identity, layout_quote, rows_for, split_headers, table_rows, unique_quotes
from .stacked_layout import CHARGE_FIELDS, currency_summary, invoice_metadata, stacked_charges
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
        amount = parse_printed_amount(text)
        return bool(amount and amount[0] == expected)
    if isinstance(expected, date):
        for form in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%B %d, %Y"):
            try:
                if datetime.strptime(text, form).date() == expected:
                    return True
            except ValueError:
                pass
        return False
    return flat(text) == flat(str(expected))


def supported_amount(printed, expected, claim_raw, currency, *, quantity=False):
    source = parse_printed_amount(printed)
    claim = parse_printed_amount(claim_raw)
    if source is None or claim is None or source[0] != expected or claim[0] != expected:
        return False
    denomination, claimed_denomination = source[1], claim[1]
    if quantity and (denomination or claimed_denomination):
        return False
    if denomination and denomination != (currency or "").strip().upper():
        return False
    if claimed_denomination and claimed_denomination != denomination:
        return False
    return bool(re.search(r"(?<![\d.,])" + re.escape(flat(claim_raw)) + r"(?![\d.,])", flat(printed)))


def local_support(invoice, field, value, page, claim):
    """Preserve field-specific grounding for existing labelled blocks."""
    quote = flat(claim.quote)
    raw = flat(claim.raw_value)
    if not raw or (not isinstance(value, Decimal) and not printed_value(claim.raw_value, value)):
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
            buyer_context = re.search(r"bill(?:ed)?\s*to|ship\s*to|sold\s*to|\bbuyer\b|\bcustomer\b|"
                                      r"remit(?:tance)?\s*(?:to|address)", preceding, re.I)
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
        index = scope.index(labelled[0][0])
        if field in {"net", "tax", "total"} and any(SUMMARY.fullmatch(text.strip()) for text in scope[:index]):
            return False
        text, printed = labelled[0]
        if isinstance(value, Decimal):
            source_line = flat(text)
            label = text.partition(":")[0].strip()
            if field == "total" and GENERIC_PAYABLE_LABEL.fullmatch(label) and not (
                    index >= 2 and inline_amount("net", scope[index - 2]) and inline_amount("tax", scope[index - 1])):
                return False
            payable_alias = field == "total" and re.fullmatch(rf"{QUALIFIER}{PAYABLE_ALIASES}", label, re.I)
            quote_matches = source_line == quote if payable_alias else source_line in quote
            return quote_matches and supported_amount(printed, value, claim.raw_value, invoice.currency,
                                                      quantity=leaf == "qty")
        candidates = [text] if printed_value(printed, value) else []
    if len(candidates) != 1:
        return False
    supporting_line = flat(candidates[0])
    # Require the full labelled source line, not just a quoted number somewhere.
    if supporting_line not in quote or raw not in supporting_line:
        return False
    return True


LINE_FIELD = re.compile(r"lines\[(\d+)\]\.(description|item_code|qty|unit_price_net|net)")


def supported_cell(printed, value, claim, currency=None, *, quantity=False):
    if isinstance(value, Decimal):
        return supported_amount(printed, value, claim.raw_value, currency, quantity=quantity)
    return (printed_value(printed, value) and printed_value(claim.raw_value, value)
            and flat(claim.raw_value) == flat(printed))


def layout_support(invoice, field, value, claim, quote, headers, table, unique_rows):
    if field in headers:
        pairs = headers[field]
        return (len(pairs) == 1 and quote in pairs[0].quotes
                and supported_cell(pairs[0].value, value, claim, invoice.currency))
    line = LINE_FIELD.fullmatch(field)
    if line and table:
        index, leaf = int(line[1]), line[2]
        row = table[index]
        # Ordinal mapping is allowed only for a complete single table with the same
        # item sequence and description context. The claim must select the row,
        # even when prices, quantities or item codes repeat elsewhere.
        return (quote in unique_rows and quote in row.quotes and leaf in row.values
                and supported_cell(row.values[leaf], value, claim, invoice.currency, quantity=leaf == "qty"))
    return False


HYBRID_HEADERS = {"invoice_number", "invoice_date", "po_reference", "currency", "net", "tax", "total"}


def independently_supported_header(value, claim, quote, pair, currency):
    """Use the parser-owned association when the claim quotes its actual value row.

    The entire row must be recognizable from PDF text. Only the corresponding
    labelled cell supplies the fact, never another numeric cell on that row.
    """
    if not pair.source_quote or quote not in (pair.quotes | pair.context_quotes):
        return False
    if isinstance(value, Decimal):
        printed = parse_printed_amount(pair.value)
        raw = parse_printed_amount(claim.raw_value)
        return bool(printed and raw and printed[0] == raw[0] == value
                    and supported_amount(pair.value, value, pair.value, currency)
                    and (raw[1] is None or raw[1] == printed[1]))
    return supported_cell(pair.value, value, claim)


def stacked_row_proofs(invoice, charges):
    """Prove the entire row mapping before using a short field quote."""
    if not charges or len(charges) != len(invoice.lines):
        return ()
    # An identical printed charge cannot anchor one row rather than the other.
    if len({tuple(flat(value) for value in row.values) for row in charges}) != len(charges):
        return ()
    for row, line in zip(charges, invoice.lines):
        if row.currency and row.currency != invoice.currency:
            return ()
        for field, printed in zip(CHARGE_FIELDS, row.values):
            fact = getattr(line, field)
            if isinstance(fact, Decimal):
                if not supported_amount(printed, fact, printed, invoice.currency, quantity=field == "qty"):
                    return ()
            elif fact is None or not printed_value(printed, fact):
                return ()
    return charges


def source_cell_proof(field, value, claim, invoice, pairs, charges):
    """A short exact cell quote is sufficient only inside this independently mapped layout."""
    if field in HYBRID_HEADERS and len(pairs) == 1 and pairs[0].source_quote:
        candidate = pairs[0]
        quotes = {layout_quote(candidate.value), *candidate.quotes, *candidate.context_quotes}
        printed, source_quote = candidate.value, candidate.source_quote
    elif (line := LINE_FIELD.fullmatch(field)) and charges:
        charge = charges[int(line[1])]
        printed = charge.values[CHARGE_FIELDS.index(line[2])]
        source_quote = charge.source_quote
        quotes = {layout_quote(printed), layout_quote(source_quote)}
    else:
        return None
    if isinstance(value, Decimal):
        # Permit omission of the code when the rest of this printed cell matches
        # exactly. The independently associated source still controls currency.
        source = parse_printed_amount(printed)
        raw = parse_printed_amount(claim.raw_value)
        if not source or not raw or source[0] != raw[0] or raw[1] not in (None, source[1]):
            return None
        if source[1] and raw[1] is None and flat(printed).endswith(flat(claim.raw_value)):
            quotes.add(layout_quote(claim.raw_value))
        valid = supported_amount(printed, value, printed, invoice.currency, quantity=field.endswith(".qty"))
    else:
        valid = supported_cell(printed, value, claim)
    if valid and layout_quote(claim.quote) in quotes:
        return printed, source_quote
    return None


def ground_evidence(invoice: ExtractedInvoiceV1, claims: tuple[SourceClaim, ...],
                    inspection: DocumentInspection) -> ExtractedInvoiceV1:
    pages = {page.number: page for page in inspection.pages}
    native_pages = {number: page for number, page in pages.items() if page.route == "native_text"}
    layouts = {number: rows_for(page) for number, page in native_pages.items()}
    summary_payables = []
    tables = {number: table_rows(rows) for number, rows in layouts.items()}
    stacked_page = None
    charge_proofs = ()
    summary_currency = None
    supplemental = defaultdict(list)
    recognized_tables = [table for table in tables.values() if table is not None]
    if inspection.route == "native_text" and len(layouts) == 1:
        number, rows = next(iter(layouts.items()))
        charges = stacked_charges(rows)
        if charges is not None:
            stacked_page = number
            extra, summary_currency = currency_summary(rows)
            for field, pairs in (*invoice_metadata(rows).items(), *extra.items()):
                supplemental[field].extend(pairs)
            if not recognized_tables:
                charge_proofs = stacked_row_proofs(invoice, charges)
    headers = {
        number: split_headers(rows, summary_payables=summary_payables,
                              supplemental=supplemental if number == stacked_page else None)
        for number, rows in layouts.items()
    }
    inline_headers = {number: inline_identity(rows) for number, rows in layouts.items()}
    identity_counts = Counter()
    for candidates in (*headers.values(), *inline_headers.values()):
        for field in ("invoice_number", "invoice_date", "po_reference", "currency"):
            identity_counts[field] += len(candidates.get(field, ()))
    eligible_table = ()
    if len(recognized_tables) == 1 and stacked_page is None:
        table = recognized_tables[0]
        if len(table) == len(invoice.lines) and all(
            line.item_code and printed_value(row.values["item_code"], line.item_code)
            and ("description" not in row.values or not line.description or printed_value(row.values["description"], line.description))
            for row, line in zip(table, invoice.lines)
        ):
            eligible_table = table
    located_quotes = {
        number: {quote for group in pairs.values() for pair in group for quote in pair.quotes}
                | {quote for row in (tables[number] or ()) for quote in row.quotes}
        for number, pairs in headers.items()
    }
    distinct_rows = unique_quotes(eligible_table)
    bare_table = None
    if inspection.route == "native_text" and len(eligible_table) == 1:
        values_by_role = eligible_table[0].values
        if all(role in values_by_role and (fact := getattr(invoice.lines[0], role)) is not None
               and (supported_amount(values_by_role[role], fact, values_by_role[role], invoice.currency,
                                     quantity=role == "qty") if isinstance(fact, Decimal)
                    else printed_value(values_by_role[role], fact)) for role in CHARGE_FIELDS):
            bare_table = eligible_table[0]
    if invoice.bank_instructions is None:
        bank_claimed = any(c.field.startswith("bank_instructions.") and c.raw_value for c in claims)
        bank_printed = any(re.fullmatch(rf"\s*(?:{LABELS['account']}|{LABELS['ifsc']})\s*:\s*\S.*", text, re.I)
                           for page in inspection.pages if page.route == "native_text" for text, _ in page.lines)
        bank_split = any(pair.value for pairs in headers.values() for field, group in pairs.items()
                         if field.startswith("bank_instructions.") for pair in group)
        if bank_claimed or bank_printed or bank_split:
            # A detected native instruction or explicit claim makes this omission
            # an invalid extraction response. Never backfill credentials.
            raise ExtractionError("MODEL_OUTPUT_UNUSABLE")
    disputed = disputed_headers(inspection.pages, headers.values(), summary_payables=summary_payables)
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
        native_proof = None
        if value is not None and claim and page and claim.quote and claim.raw_value:
            if page.route != "native_text":
                state = "SOURCE_LOCATED_UNVERIFIED"
            else:
                source, quote = sources[page.number], flat(claim.quote)
                occurrences = source.count(quote) if quote else 0
                normalized_quote = layout_quote(claim.quote)
                splits = headers[page.number]
                # The alternate quote can span adjacent cells or native column layout.
                # Restrict it to a unique parser-owned header on a single native page.
                pairs = splits.get(field, ())
                eligible = field not in disputed and len(matches) == 1 and not (
                    summary_currency and field in {"net", "tax", "total"} and summary_currency != invoice.currency
                )
                if (eligible and inspection.route == "native_text" and len(pages) == 1
                        and field in HYBRID_HEADERS and len(pairs) == 1
                        and not layout_support(invoice, field, value, claim, normalized_quote, splits, (), ())
                        and independently_supported_header(value, claim, normalized_quote, pairs[0], invoice.currency)):
                    native_proof = (pairs[0].value, pairs[0].source_quote)
                    state = "NATIVE_VERIFIED"
                if state != "NATIVE_VERIFIED" and (occurrences or normalized_quote in located_quotes[page.number]):
                    state = "SOURCE_LOCATED_UNVERIFIED"
                    if eligible:
                        table = eligible_table if tables[page.number] is eligible_table else ()
                        if field in splits or (LINE_FIELD.fullmatch(field) and (recognized_tables or stacked_page is not None)):
                            supported = layout_support(invoice, field, value, claim, normalized_quote, splits, table, distinct_rows)
                        else:
                            # A complete source line is distinct from its substring in a longer
                            # statement label. Duplicate complete lines still fail closed.
                            unique = occurrences == 1 or line_counts[page.number][quote] == 1
                            supported = unique and local_support(invoice, field, value, page, claim)
                        if supported:
                            state = "NATIVE_VERIFIED"
                if state != "NATIVE_VERIFIED" and eligible and page.number == stacked_page and charge_proofs:
                    native_proof = source_cell_proof(field, value, claim, invoice, pairs, charge_proofs)
                    if native_proof:
                        state = "NATIVE_VERIFIED"
                if state != "NATIVE_VERIFIED" and eligible and inspection.route == "native_text":
                    # A bare claim must match the specific, independently associated native cell.
                    candidates = pairs or inline_headers[page.number].get(field, ())
                    if (field in HYBRID_HEADERS and len(candidates) == 1
                            and normalized_quote == layout_quote(candidates[0].value)
                            and (field in {"net", "tax", "total"} or identity_counts[field] == 1)):
                        native_proof = source_cell_proof(field, value, claim, invoice, candidates, ())
                    elif bare_table and tables[page.number] is eligible_table and (line := LINE_FIELD.fullmatch(field)):
                        leaf = line[2]
                        printed = bare_table.values.get(leaf)
                        if (printed and layout_quote(printed) == normalized_quote and
                                supported_cell(printed, value, claim, invoice.currency, quantity=leaf == "qty")):
                            native_proof = (printed, " ".join(bare_table.values.values()))
                    if native_proof:
                        state = "NATIVE_VERIFIED"
        grounded.append(EvidenceRefV1(
            field=field, raw_value=native_proof[0] if native_proof else claim.raw_value if claim else None,
            normalized_value=None if value is None else str(value),
            page=claim.page if claim else None, quote=native_proof[1] if native_proof else claim.quote if claim else None,
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
