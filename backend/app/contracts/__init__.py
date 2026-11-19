"""Version 1 immutable snapshots. No extraction or decision implementation."""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, BeforeValidator, model_validator


def reject_float(value):
    if isinstance(value, (float, bool)):
        raise ValueError("Use a decimal string or Decimal, never a binary float")
    return value

Amount = Annotated[Decimal, BeforeValidator(reject_float)]
EvidenceState = Literal["NATIVE_VERIFIED", "SOURCE_LOCATED_UNVERIFIED", "MISSING"]
RunExecutionState = Literal["QUEUED", "RUNNING", "COMPLETED", "PROCESSING_FAILED", "INTERRUPTED"]
StageState = Literal["QUEUED", "RUNNING", "PASSED", "WARNING", "FAILED", "SKIPPED"]
SourceRoute = Literal["native_text", "image_only", "mixed"]

class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

class BankInstructionsV1(Contract):
    account: str
    ifsc: str

class VendorV1(Contract):
    id: str
    name: str
    aliases: tuple[str, ...] = ()
    approved: bool
    verified_bank: BankInstructionsV1 | None = None

class POLineV1(Contract):
    item_code: str
    description: str
    ordered_qty: Amount
    unit_price_net: Amount
    authorized_net: Amount

class PurchaseOrderV1(Contract):
    id: str
    vendor_id: str
    status: str
    currency: str
    po_date: date
    lines: tuple[POLineV1, ...]
    authorized_net: Amount

class BilledLineV1(Contract):
    item_code: str
    qty: Amount
    unit_price_net: Amount
    line_net: Amount

class PriorBilledInvoiceV1(Contract):
    id: str
    invoice_number: str
    vendor_id: str
    po_id: str
    status: Literal["BILLED"]
    invoice_date: date
    currency: str
    net: Amount
    tax: Amount
    gross: Amount
    lines: tuple[BilledLineV1, ...]

class EvidenceRefV1(Contract):
    field: str
    raw_value: str | None = None
    normalized_value: str | None = None
    page: int | None = Field(default=None, ge=1)
    quote: str | None = None
    route: SourceRoute | None = None
    evidence_state: EvidenceState = "MISSING"

class InvoiceLineV1(Contract):
    description: str | None = None
    item_code: str | None = None
    qty: Amount | None = None
    unit_price_net: Amount | None = None
    net: Amount | None = None

DocumentIntegrityFlag = Literal["RASTER_CONTENT_UNRESOLVED"]


class ExtractedInvoiceV1(Contract):
    schema_version: Literal["extracted-invoice-v1"] = "extracted-invoice-v1"
    vendor_name_raw: str | None = None
    vendor_name_normalized: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    po_reference: str | None = None
    currency: str | None = None
    net: Amount | None = None
    tax: Amount | None = None
    total: Amount | None = None
    lines: tuple[InvoiceLineV1, ...] = ()
    bank_instructions: BankInstructionsV1 | None = None
    evidence: tuple[EvidenceRefV1, ...] = ()
    # Missing denotes a historical snapshot that predates this adapter assessment.
    document_integrity_flags: tuple[DocumentIntegrityFlag, ...] | None = Field(
        default=None, exclude_if=lambda flags: flags is None,
    )

class PolicyV1(Contract):
    version: str = "policy-v1"
    effective_at: datetime = datetime(2026, 11, 19, tzinfo=timezone.utc)
    price_tolerance_pct: Amount = Field(default=Decimal("0.02"), ge=0)
    require_explicit_po: bool = True
    amount_rounding_allowance: Amount = Field(default=Decimal("1.00"), ge=0)
    commitment_overrun_allowance: Amount = Field(default=Decimal("0.00"), ge=0)

class POCandidateV1(Contract):
    po: PurchaseOrderV1
    selection_provenance: str
    rank: int | None = None

class EvaluationContextV1(Contract):
    invoice: ExtractedInvoiceV1
    canonical_vendor: VendorV1 | None = None
    candidates: tuple[POCandidateV1, ...] = ()
    selected_po: PurchaseOrderV1 | None = None
    selection_provenance: str | None = None
    prior_billed_records: tuple[PriorBilledInvoiceV1, ...] = ()
    procurement_records: tuple[PurchaseOrderV1, ...] = ()

class FindingValueV1(Contract):
    name: str
    value: str | None = None

class FindingV1(Contract):
    code: str
    severity: Literal["PASS", "INFO", "REVIEW", "BLOCK"]
    title: str
    explanation: str
    source_type: str
    evidence_refs: tuple[EvidenceRefV1, ...] = ()
    owner: str | None = None
    next_action: str | None = None
    values: tuple[FindingValueV1, ...] = ()

class DecisionV1(Contract):
    outcome: Literal["READY_FOR_AP", "REVIEW_REQUIRED", "BLOCKED"]
    findings: tuple[FindingV1, ...] = ()
    primary_reason_code: str | None = None
    next_action: str | None = None
    owner: str | None = None
    policy_version: str

class RunStageV1(Contract):
    name: str
    state: StageState
    started_at: datetime | None = None
    finished_at: datetime | None = None

class TimingV1(Contract):
    name: str
    milliseconds: int = Field(ge=0)

class UsageV1(Contract):
    model_calls: int | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)

EXECUTION_ERROR_CODES = frozenset({
    "INVALID_PDF", "EMPTY_PDF", "ENCRYPTED_PDF", "UNSUPPORTED_PDF", "INPUT_TOO_LARGE",
    "PAGE_LIMIT", "RESOURCE_LIMIT", "PARSER_TIMEOUT", "PARSER_FAILED", "CONFIGURATION",
    "MODEL_UNAVAILABLE", "AUTHORIZATION", "RATE_LIMIT", "PROVIDER_TIMEOUT",
    "PROVIDER_UNAVAILABLE", "PROVIDER_REJECTED", "INVALID_RESPONSE", "INTERNAL_ERROR",
    "SERVER_RESTART",
})

class RunSnapshotV1(Contract):
    id: str
    execution_state: RunExecutionState
    execution_error_code: str | None = None
    decision: DecisionV1 | None = None
    stages: tuple[RunStageV1, ...] = ()
    extracted_invoice: ExtractedInvoiceV1 | None = None
    candidates: tuple[POCandidateV1, ...] = ()
    document_id: str
    source_route: SourceRoute | None = None
    model_id: str | None = None
    extraction_schema_version: str | None = None
    policy_snapshot: PolicyV1 | None = None
    timings: tuple[TimingV1, ...] = ()
    usage: UsageV1 | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def decision_only_after_completion(self):
        if self.execution_error_code is not None:
            if self.execution_state not in ("PROCESSING_FAILED", "INTERRUPTED"):
                raise ValueError("Only technical terminal states may have an execution error")
            if self.execution_error_code not in EXECUTION_ERROR_CODES:
                raise ValueError("Execution error must be an allowlisted code")
        if self.execution_state != "COMPLETED" and self.decision is not None:
            raise ValueError("Only a completed analysis may have a business decision")
        if self.execution_state == "COMPLETED" and self.decision is None:
            raise ValueError("A completed analysis requires exactly one decision")
        if self.decision and (not self.policy_snapshot or self.decision.policy_version != self.policy_snapshot.version):
            raise ValueError("Decision requires the matching immutable policy snapshot")
        return self
