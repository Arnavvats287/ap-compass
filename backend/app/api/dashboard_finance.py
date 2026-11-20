"""Read-only dashboard analytics over recorded decisions and procurement authority."""
from collections import Counter, defaultdict
from decimal import Decimal, localcontext

from app.domain.common import normalized
from app.domain.matching import resolve_vendor

RECENT_LIMIT = 100


def exact_sum(amounts):
    with localcontext() as context:
        context.prec = max(28, max(amount.adjusted() for amount in amounts)
                           - min(amount.as_tuple().exponent for amount in amounts)
                           + len(str(len(amounts))) + 4)
        return sum(amounts, Decimal(0))


def exact_currency_totals(grouped, *, fixed=False):
    totals = {currency: exact_sum(amounts) for currency, amounts in sorted(grouped.items())}
    return {currency: format(total, "f") if fixed else str(total) for currency, total in totals.items()}


def vendor_attention(snapshots, vendors):
    groups = {}
    for snapshot in snapshots:
        decision, invoice = snapshot.decision, snapshot.extracted_invoice
        raw_name = invoice.vendor_name_raw if invoice else None
        if not raw_name or not raw_name.strip() or not decision or decision.outcome not in ("BLOCKED", "REVIEW_REQUIRED"):
            continue
        canonical = resolve_vendor(raw_name, vendors)
        if canonical and canonical.approved:
            key, display = ("approved", canonical.id), canonical.name
        else:
            key, display = ("recorded", raw_name), raw_name
        group = groups.setdefault(key, {"name": display, "source_names": set(), "review_count": 0,
                                       "blocked_count": 0, "gross": defaultdict(list), "missing_gross_count": 0})
        group["source_names"].add(raw_name)
        group["blocked_count" if decision.outcome == "BLOCKED" else "review_count"] += 1
        if invoice.total is not None and invoice.currency:
            group["gross"][invoice.currency].append(invoice.total)
        else:
            group["missing_gross_count"] += 1

    def sort_key(item):
        key, group = item
        currencies = group["gross_by_currency"]
        comparable = len(currencies) == 1 and not group["missing_gross_count"]
        currency = next(iter(currencies)) if comparable else ""
        gross = Decimal(currencies[currency]).copy_negate() if comparable else Decimal(0)
        # Do not compare different currency magnitudes or incomplete/mixed totals.
        return (-(group["review_count"] + group["blocked_count"]), not comparable, currency,
                gross, group["name"].casefold(), key)

    for group in groups.values():
        group["source_names"] = sorted(group["source_names"])
        group["gross_by_currency"] = exact_currency_totals(group.pop("gross"), fixed=True)
    return [group for _, group in sorted(groups.items(), key=sort_key)[:10]]


def procurement_capacity(vendors, orders, billed):
    names = {vendor.id: vendor.name for vendor in vendors}
    bills = defaultdict(list)
    for bill in billed:
        bills[normalized(bill.po_id)].append(bill)

    rows = []
    for order in orders:
        prior = bills[normalized(order.id)]
        comparable = all(normalized(bill.currency) == normalized(order.currency) for bill in prior)
        billed_net = exact_sum([bill.net for bill in prior]) if prior and comparable else Decimal(0)
        remaining = exact_sum([order.authorized_net, billed_net.copy_negate()]) if comparable else None
        rows.append((remaining, {
            "po_id": order.id, "vendor_name": names.get(order.vendor_id, order.vendor_id),
            "status": order.status, "currency": order.currency, "approved_net": format(order.authorized_net, "f"),
            "previously_billed_net": format(billed_net, "f") if comparable else None,
            "remaining_net": format(remaining, "f") if remaining is not None else None,
        }))
    return [row for _, row in sorted(rows, key=lambda entry: (
        entry[1]["currency"], entry[0] is None,
        entry[0].copy_negate() if entry[0] is not None else Decimal(0), entry[1]["po_id"],
    ))]


def exception_insights(snapshots):
    counts = Counter(finding.code for snapshot in snapshots if snapshot.decision
                     for finding in snapshot.decision.findings if finding.severity in ("REVIEW", "BLOCK"))
    return [{"code": code, "count": count}
            for code, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]]
