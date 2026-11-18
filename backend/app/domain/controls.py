"""Deterministic duplicate and bank controls; no model judgments or side effects."""
import re

from app.contracts import EvaluationContextV1, PolicyV1
from .common import finding, normalized, verified


def billed_duplicates(context: EvaluationContextV1, policy: PolicyV1):
    vendor, invoice = context.canonical_vendor, context.invoice
    if vendor is None or not normalized(invoice.invoice_number):
        return ()
    findings = []
    for billed in context.prior_billed_records:
        if billed.vendor_id != vendor.id:
            continue
        if normalized(billed.invoice_number) == normalized(invoice.invoice_number):
            findings.append(finding("EXACT_DUPLICATE", "BLOCK", "Invoice is already in the billed ledger",
                                    f"The canonical vendor and invoice number match authoritative billed record {billed.id}. "
                                    "A changed layout, date or amount does not create a new invoice identity.",
                                    source="billed_ledger", action="Hold processing and reconcile this reissued invoice with the original billed record.",
                                    billed_record_id=billed.id, billed_net=billed.net))
            continue
        compact = lambda value: re.sub(r"[^a-z0-9]", "", normalized(value))
        number_variant = bool(compact(invoice.invoice_number)) and compact(invoice.invoice_number) == compact(billed.invoice_number)
        same_business_facts = (
            invoice.net is not None and invoice.net == billed.net
            and normalized(invoice.currency) == normalized(billed.currency)
            and context.selected_po is not None and context.selected_po.id == billed.po_id
            and invoice.invoice_date is not None
            and abs((invoice.invoice_date - billed.invoice_date).days) <= 7
        )
        if number_variant or same_business_facts:
            findings.append(finding("POSSIBLE_DUPLICATE", "REVIEW", "Invoice may repeat a billed transaction",
                                    f"Billed record {billed.id} has a separator-only invoice-number variant or the same "
                                    "vendor, PO, currency and net amount within seven calendar days. This is a review signal, not proof.",
                                    source="billed_ledger", action="Compare the invoice and billed record to establish whether this is a distinct charge.",
                                    billed_record_id=billed.id))
    return tuple(findings)


def bank_instructions(context: EvaluationContextV1, policy: PolicyV1):
    invoice, vendor = context.invoice, context.canonical_vendor
    bank = invoice.bank_instructions
    if bank is None:
        return (finding("BANK_DETAILS_NOT_PROVIDED", "INFO", "No payment instructions supplied",
                        "Bank comparison is not applicable; missing instructions are not a verified contradiction."),)
    if vendor is None or vendor.verified_bank is None:
        return (finding("BANK_MASTER_UNVERIFIED", "REVIEW", "No verified bank master is available",
                        "The invoice supplies payment instructions, but no trusted bank record is available for comparison.",
                        source="vendor_master", owner="Procurement",
                        action="Verify payment details independently through the vendor's known contact channel."),)
    if not all(verified(invoice, f"bank_instructions.{name}") for name in ("account", "ifsc")):
        return (finding("BANK_DETAILS_UNVERIFIED", "REVIEW", "Invoice bank details need source verification",
                        "Uncertain or incomplete payment instructions cannot establish a verified bank contradiction.",
                        action="Verify the invoice bank fields and contact the vendor through a known independent channel."),)
    master = vendor.verified_bank
    if not master.account.strip() or not master.ifsc.strip():
        return (finding("BANK_MASTER_UNVERIFIED", "REVIEW", "Bank master is incomplete",
                        "The trusted record lacks complete bank details.", source="vendor_master", owner="Procurement",
                        action="Complete independent verification of the vendor bank master before processing."),)
    if normalized(bank.account) != normalized(master.account) or normalized(bank.ifsc) != normalized(master.ifsc):
        return (finding("BANK_DETAILS_MISMATCH", "BLOCK", "Invoice payment instructions differ from the bank master",
                        "Source-supported bank instructions contradict the verified vendor master. This is a hold, not proof of fraud.",
                        source="vendor_master", action="Hold processing and verify with the vendor using a known contact channel; do not use invoice contact details."),)
    return ()
