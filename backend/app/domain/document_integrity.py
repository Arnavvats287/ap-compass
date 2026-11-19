"""Deterministic review of integrity observations from the document adapter."""
from app.contracts import EvaluationContextV1, FindingV1, PolicyV1
from .common import finding


def document_content(context: EvaluationContextV1, _policy: PolicyV1) -> tuple[FindingV1, ...]:
    flags = context.invoice.document_integrity_flags or ()
    if "RASTER_CONTENT_UNRESOLVED" not in flags:
        return ()
    return (finding(
        "DOCUMENT_CONTENT_UNVERIFIED",
        "REVIEW",
        "Additional document content needs verification",
        "Some rendered content may contain invoice information that could not be independently verified.",
        owner="Accounts Payable",
        action="Inspect the complete rendered invoice and independently confirm any relevant charges "
               "or payment instructions before proceeding.",
    ),)
