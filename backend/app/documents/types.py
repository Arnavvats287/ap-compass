"""Adapter-local types, not extensions of public financial contracts."""
from dataclasses import dataclass, field
from typing import Literal

from app.contracts import ExtractedInvoiceV1, SourceRoute

ErrorCode = Literal[
    "INVALID_PDF", "EMPTY_PDF", "ENCRYPTED_PDF", "UNSUPPORTED_PDF", "INPUT_TOO_LARGE",
    "PAGE_LIMIT", "RESOURCE_LIMIT", "PARSER_TIMEOUT", "PARSER_FAILED", "CONFIGURATION",
    "MODEL_UNAVAILABLE", "AUTHORIZATION", "RATE_LIMIT", "PROVIDER_UNAVAILABLE",
    "PROVIDER_TIMEOUT", "PROVIDER_REJECTED", "INVALID_RESPONSE",
]


class ExtractionError(Exception):
    """Only allowlisted codes, counts and timings; never retain provider messages."""
    def __init__(self, code: ErrorCode, *, calls=0, retryable=False, attempts=(), elapsed_ms=None, provider_status=None):
        super().__init__(code)
        self.code = code
        self.calls = calls
        self.retryable = retryable
        self.attempts = attempts
        self.elapsed_ms = elapsed_ms
        self.provider_status = provider_status


@dataclass(frozen=True)
class PageInspection:
    number: int
    route: SourceRoute
    native_text: str = field(repr=False)
    # Native line text and actual font sizes; internal location context only.
    lines: tuple[tuple[str, float], ...] = field(repr=False)
    image_png: bytes | None = field(default=None, repr=False)
    image_width: int | None = None
    image_height: int | None = None


@dataclass(frozen=True)
class DocumentInspection:
    route: SourceRoute
    pages: tuple[PageInspection, ...] = field(repr=False)
    byte_count: int


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    thinking_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class ProviderReply:
    json_text: str = field(repr=False)
    model_id: str | None
    usage: TokenUsage = field(default_factory=TokenUsage)


@dataclass(frozen=True)
class ModelAttempt:
    number: int
    requested_model_id: str
    elapsed_ms: int
    error_code: str | None
    actual_model_id: str | None
    usage: TokenUsage
    provider_http_status: int | None = None


@dataclass(frozen=True)
class ExtractionMetadata:
    requested_model_id: str
    selected_model_id: str
    escalation_reason: str | None
    route: SourceRoute
    page_count: int
    model_calls: int
    elapsed_ms: int
    attempts: tuple[ModelAttempt, ...]
    schema_version: str = "invoice-extraction-wire-v1"
    prompt_version: str = "invoice-facts-v1"


@dataclass(frozen=True)
class ExtractionResult:
    invoice: ExtractedInvoiceV1 = field(repr=False)
    inspection: DocumentInspection = field(repr=False)
    metadata: ExtractionMetadata
