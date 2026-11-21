"""In-memory document adapter; bounded parsing/inference, no business decisions."""
import asyncio
from time import perf_counter

from app.ai.provider import ExtractionProvider, InferenceTracker, inference_tracker
from .evidence import ground_evidence, values
from .inspection import inspect_pdf
from .schema import parse_response
from .types import ExtractionError, ExtractionMetadata, ExtractionResult, ModelAttempt, TokenUsage


MODEL_OUTPUT_ERRORS = {"MODEL_OUTPUT_JSON", "MODEL_OUTPUT_SCHEMA", "MODEL_OUTPUT_UNUSABLE"}


def quality_failure(invoice, route):
    """Extraction quality only; never inspect amounts for financial eligibility."""
    fields = ("vendor_name_raw", "invoice_number", "invoice_date", "currency", "net", "tax", "total")
    if any(getattr(invoice, key) is None or getattr(invoice, key) == "" for key in fields) or not invoice.lines:
        return "MISSING_CRITICAL_FACTS"
    if any(line.qty is None or line.unit_price_net is None or not line.item_code for line in invoice.lines):
        return "INCOMPLETE_LINE_FACTS"
    source_fields = set(fields)
    if invoice.po_reference:
        source_fields.add("po_reference")
    for index, line in enumerate(invoice.lines):
        source_fields.update(f"lines[{index}].{key}" for key in ("item_code", "qty", "unit_price_net"))
        if line.net is not None:
            source_fields.add(f"lines[{index}].net")
    if route == "native_text" and any(ref.evidence_state != "NATIVE_VERIFIED" for ref in invoice.evidence
                                     if ref.field in source_fields):
        return "NATIVE_EVIDENCE_UNSUPPORTED"
    return None


def usable_extraction(invoice):
    """Partial facts are usable; an entirely empty structured reply is not."""
    header = (invoice.vendor_name_raw, invoice.invoice_number, invoice.invoice_date,
              invoice.po_reference, invoice.net, invoice.tax, invoice.total)
    lines = (value for line in invoice.lines for value in
             (line.description, line.item_code, line.qty, line.unit_price_net, line.net))
    return any(value is not None and (not isinstance(value, str) or value.strip())
               for value in (*header, *lines))


def preserves_source_evidence(primary, candidate):
    """Adopt a second extraction only when it adds proof without revising known facts."""
    if primary.lines and len(primary.lines) != len(candidate.lines):
        return False
    original = values(primary)
    alternate = values(candidate)
    proven = {ref.field for ref in candidate.evidence if ref.evidence_state == "NATIVE_VERIFIED"}
    already_proven = {ref.field for ref in primary.evidence if ref.evidence_state == "NATIVE_VERIFIED"}
    return (already_proven < proven
            and all(alternate.get(field) == value for field, value in original.items() if value is not None)
            and all(original.get(field) is not None or field in proven
                    for field, value in alternate.items() if value is not None))


async def extract_pdf(raw: bytes, provider: ExtractionProvider, *,
                      escalation_provider: ExtractionProvider | None = None,
                      scan_provider: ExtractionProvider | None = None,
                      model_timeout_seconds: float = 30, max_attempts: int = 2) -> ExtractionResult:
    if not (0 < model_timeout_seconds <= 45 and 1 <= max_attempts <= 2):
        raise ExtractionError("CONFIGURATION")
    allowed = {provider.model_id, escalation_provider.model_id if escalation_provider else provider.model_id}
    if scan_provider and scan_provider.model_id not in allowed:
        raise ExtractionError("CONFIGURATION")
    start = perf_counter()
    document = await asyncio.to_thread(inspect_pdf, raw)
    attempts = []
    chosen = scan_provider if document.route != "native_text" and scan_provider else provider
    initial_model = chosen.model_id
    escalation_reason = None
    primary_candidate = None

    def finish(invoice, selected_model, *, retained=False):
        return ExtractionResult(invoice=invoice, inspection=document, metadata=ExtractionMetadata(
            requested_model_id=initial_model, selected_model_id=selected_model,
            escalation_reason=escalation_reason, route=document.route, page_count=len(document.pages),
            model_calls=sum(attempt.inference_called for attempt in attempts),
            elapsed_ms=int((perf_counter() - start) * 1000), attempts=tuple(attempts),
            retained_primary=retained,
        ))

    for number in range(1, max_attempts + 1):
        began = perf_counter()
        reply = None
        tracker = InferenceTracker()
        tracking_token = inference_tracker.set(tracker)
        try:
            reply = await asyncio.wait_for(chosen.generate(document, model_timeout_seconds), model_timeout_seconds)
            invoice, claims = parse_response(reply.json_text)
            invoice = ground_evidence(invoice, claims, document)
            if not usable_extraction(invoice):
                raise ExtractionError("MODEL_OUTPUT_UNUSABLE")
            attempts.append(ModelAttempt(number, chosen.model_id, int((perf_counter() - began) * 1000), None, reply.model_id, reply.usage))
            if primary_candidate is not None and not preserves_source_evidence(primary_candidate, invoice):
                return finish(primary_candidate, provider.model_id, retained=True)
            quality = quality_failure(invoice, document.route)
            if (quality and number < max_attempts and escalation_provider
                    and chosen.model_id != escalation_provider.model_id):
                escalation_reason = quality
                if chosen.model_id == provider.model_id:
                    primary_candidate = invoice
                chosen = escalation_provider
                continue
            return finish(invoice, chosen.model_id)
        except TimeoutError:
            error = ExtractionError("PROVIDER_TIMEOUT", retryable=True)
        except ExtractionError as caught:
            error = caught
        except Exception:
            if reply is not None:
                raise  # Unexpected application error; orchestration logs only INTERNAL_ERROR.
            error = ExtractionError("PROVIDER_REJECTED")
        finally:
            inference_tracker.reset(tracking_token)
        attempts.append(ModelAttempt(number, chosen.model_id, int((perf_counter() - began) * 1000), error.code,
                                     reply.model_id if reply else None, reply.usage if reply else TokenUsage(),
                                     error.provider_status, reply is not None or (error.inference_attempted and tracker.called)))
        retry = error.retryable or error.code in MODEL_OUTPUT_ERRORS
        stronger_already_attempted = escalation_provider and chosen.model_id == escalation_provider.model_id
        if stronger_already_attempted and primary_candidate is not None:
            return finish(primary_candidate, provider.model_id, retained=True)
        if number == max_attempts or not retry or stronger_already_attempted:
            raise ExtractionError(error.code, calls=sum(attempt.inference_called for attempt in attempts), attempts=tuple(attempts),
                                  elapsed_ms=int((perf_counter() - start) * 1000), provider_status=error.provider_status) from None
        if error.code in MODEL_OUTPUT_ERRORS and escalation_provider and chosen.model_id != escalation_provider.model_id:
            escalation_reason = "INVALID_STRUCTURED_RESPONSE"
            chosen = escalation_provider
        await asyncio.sleep(.25)  # One bounded retry; never triggered by arithmetic findings.
    raise AssertionError("Unreachable")
