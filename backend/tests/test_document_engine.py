"""Offline provider replies are synthetic TEST DATA, never live inference evidence."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace

import pymupdf
import pytest

from app.contracts import PolicyV1
from app.documents.evidence import ground_evidence
from app.documents.fixtures import image_only, native_case
from app.documents.inspection import inspect_pdf
from app.documents.limits import MAX_IMAGE_EDGE, MAX_IMAGE_PIXELS, MAX_INPUT_BYTES
from app.documents.pipeline import extract_pdf
from app.documents.schema import WireInvoice, parse_response, provider_schema
from app.documents.types import ExtractionError, ProviderReply, TokenUsage
from app.ai.gemini import GeminiProvider, GeminiSettings, provider_error, verify_model
from app.domain import build_context, evaluate
from test_finance_engine import VENDORS, POS, HISTORY

ROOT = Path(__file__).resolve().parents[2]
CASES = {case["id"]: case for case in json.loads((ROOT / "data/fixture_manifest.json").read_text())["fixture_cases"]}
NATIVE = ("HAPPY_CLEAN", "HAPPY_PARTIAL", "OVERBILLED_PARTIAL", "DUPLICATE_REISSUED")


def wire(case_id="HAPPY_CLEAN", *, line_net=True):
    case = CASES[case_id]
    output = {"vendor_name_raw": case["vendor_name"], "invoice_number": case["invoice_number"],
              "invoice_date": case["invoice_date"], "po_reference": case["po_reference"], "currency": case["currency"],
              "net": case["net"], "tax": case["tax"], "total": case["gross"],
              "lines": [], "bank_instructions": case.get("bank_instructions"), "evidence": []}
    claims = [("vendor_name_raw", case["vendor_name"], case["vendor_name"])]
    for name, label in (("invoice_number", "Invoice number"), ("invoice_date", "Invoice date"),
                        ("po_reference", "Purchase order"), ("currency", "Currency"),
                        ("net", "Net subtotal: INR"), ("tax", "Tax (synthetic GST): INR"), ("total", "Invoice total: INR")):
        printed = f"{label} {output[name]}" if label.endswith("INR") else f"{label}: {output[name]}"
        claims.append((name, output[name], printed))
    for i, line in enumerate(case["lines"]):
        copied = {**line, "net": str(Decimal(line["qty"]) * Decimal(line["unit_price_net"])) if line_net else None}
        output["lines"].append(copied)
        for name, label in (("description", None), ("item_code", "Item code"), ("qty", "Quantity"),
                            ("unit_price_net", "Unit price (net): INR"), ("net", "Line net: INR")):
            value = copied[name]
            if value is not None:
                printed = value if label is None else f"{label} {value}" if label.endswith("INR") else f"{label}: {value}"
                claims.append((f"lines[{i}].{name}", value, printed))
    if case.get("bank_instructions"):
        for name, label in (("account", "Account number"), ("ifsc", "IFSC")):
            value = case["bank_instructions"][name]
            claims.append((f"bank_instructions.{name}", value, f"{label}: {value}"))
    output["evidence"] = [{"field": name, "page": 1, "raw_value": value, "quote": quote} for name, value, quote in claims]
    return output


class FakeProvider:
    """Dependency-injected test double, not a Gemini implementation."""
    def __init__(self, replies=None, model="TEST_ONLY-lite"):
        self.model_id = model
        self.replies = list(replies or [json.dumps(wire())])
        self.calls = []

    async def generate(self, document, timeout_seconds):
        self.calls.append(document)
        event = self.replies.pop(0)
        if isinstance(event, BaseException):
            raise event
        if callable(event):
            return await event()
        return ProviderReply(event, self.model_id, TokenUsage(10, 20, None, 30))


@pytest.fixture(scope="module")
def native_documents():
    return {name: inspect_pdf((ROOT / "tests/fixtures" / (name + ".pdf")).read_bytes()) for name in NATIVE}


def run(raw, provider, **kwargs):
    return asyncio.run(extract_pdf(raw, provider, **kwargs))


@pytest.mark.parametrize("case_id", NATIVE)
def test_four_real_native_pdfs_with_fake_provider_and_real_verification(case_id):
    fake = FakeProvider([json.dumps(wire(case_id))])
    result = run((ROOT / "tests/fixtures" / (case_id + ".pdf")).read_bytes(), fake)
    assert result.inspection.route == "native_text"
    assert result.invoice.net == Decimal(CASES[case_id]["net"])
    assert result.invoice.invoice_number == CASES[case_id]["invoice_number"]
    assert all(ref.evidence_state == "NATIVE_VERIFIED" for ref in result.invoice.evidence)
    assert result.metadata.model_calls == 1
    assert result.metadata.attempts[0].usage == TokenUsage(10, 20, None, 30)
    assert result.metadata.elapsed_ms >= 0
    assert evaluate(build_context(result.invoice, VENDORS, POS, HISTORY), PolicyV1()).outcome == CASES[case_id]["expected_decision"]


@pytest.mark.parametrize("edit", ["extra_decision", "extra_po_selection", "float_amount", "bad_date", "bad_decimal", "claimed_verification", "partial_bank", "missing_key"])
def test_exact_schema_rejects_invalid_or_authoritative_model_fields(edit):
    output = wire()
    if edit == "extra_decision": output["decision"] = "READY_FOR_AP"
    elif edit == "extra_po_selection": output["selected_po"] = "PO-6001"
    elif edit == "float_amount": output["net"] = 48000.0
    elif edit == "bad_date": output["invoice_date"] = "2026-02-30"
    elif edit == "bad_decimal": output["net"] = "NaN"
    elif edit == "claimed_verification": output["evidence"][0]["evidence_state"] = "NATIVE_VERIFIED"
    elif edit == "partial_bank": output["bank_instructions"] = {"account": None, "ifsc": "TEST"}
    else: del output["tax"]
    with pytest.raises(ExtractionError, match="MODEL_OUTPUT_SCHEMA"):
        parse_response(json.dumps(output))


@pytest.mark.parametrize("change,expected", [({"quote": "not in this PDF"}, "MISSING"), ({"page": 2}, "MISSING"),
    ({"raw_value": "49000"}, "SOURCE_LOCATED_UNVERIFIED"), ({"quote": "Line net: INR 48000"}, "SOURCE_LOCATED_UNVERIFIED"),
    ({"quote": "48000"}, "SOURCE_LOCATED_UNVERIFIED"), ({"quote": None}, "MISSING")])
def test_untrusted_claims_are_not_promoted(native_documents, change, expected):
    output = wire()
    output["evidence"] = [{**e, **change} if e["field"] == "net" else e for e in output["evidence"]]
    invoice, claims = parse_response(json.dumps(output))
    grounded = ground_evidence(invoice, claims, native_documents["HAPPY_CLEAN"])
    assert next(e for e in grounded.evidence if e.field == "net").evidence_state == expected


def test_model_normalized_fact_must_agree_with_actual_printed_value(native_documents):
    output = wire()
    output["net"] = "49000"
    invoice, claims = parse_response(json.dumps(output))
    grounded = ground_evidence(invoice, claims, native_documents["HAPPY_CLEAN"])
    assert next(e for e in grounded.evidence if e.field == "net").evidence_state != "NATIVE_VERIFIED"


def test_missing_and_duplicate_claims_cannot_verify(native_documents):
    output = wire()
    output["evidence"] = [e for e in output["evidence"] if e["field"] != "net"]
    output["evidence"].append(deepcopy(output["evidence"][0]))
    invoice, claims = parse_response(json.dumps(output))
    result = ground_evidence(invoice, claims, native_documents["HAPPY_CLEAN"])
    refs = {r.field: r for r in result.evidence}
    assert refs["net"].evidence_state == "MISSING"
    assert refs["vendor_name_raw"].evidence_state != "NATIVE_VERIFIED"


def test_scan_has_no_native_text_and_never_verified():
    raw = (ROOT / "tests/fixtures/SCAN_CONFLICT.pdf").read_bytes()
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        assert not pdf[0].get_text().strip()
        assert pdf[0].get_images()
    result = run(raw, FakeProvider([json.dumps(wire("SCAN_CONFLICT", line_net=False))]))
    assert result.inspection.route == "image_only"
    assert all(ref.evidence_state == "SOURCE_LOCATED_UNVERIFIED" for ref in result.invoice.evidence if ref.normalized_value is not None)
    page = result.inspection.pages[0]
    assert page.image_png.startswith(b"\x89PNG")
    assert max(page.image_width, page.image_height) <= MAX_IMAGE_EDGE + 1
    assert page.image_width * page.image_height <= MAX_IMAGE_PIXELS
    decision = evaluate(build_context(result.invoice, VENDORS, POS, HISTORY), PolicyV1())
    assert decision.outcome == "REVIEW_REQUIRED"
    assert "TOTAL_RECONCILIATION_FAILED" in {f.code for f in decision.findings}
    assert result.metadata.model_calls == 1  # No retry for genuinely inconsistent totals.


def test_mixed_pages_keep_original_number_and_per_page_text():
    with pymupdf.open(stream=(ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes(), filetype="pdf") as native, pymupdf.open(stream=(ROOT / "tests/fixtures/SCAN_CONFLICT.pdf").read_bytes(), filetype="pdf") as scan:
        native.insert_pdf(scan)
        raw = native.tobytes()
    document = inspect_pdf(raw)
    assert document.route == "mixed"
    assert [(p.number, p.route) for p in document.pages] == [(1, "native_text"), (2, "image_only")]
    assert document.pages[0].native_text and not document.pages[1].native_text.strip()


@pytest.mark.parametrize("raw,code", [(b"", "EMPTY_PDF"), (b"not a PDF", "INVALID_PDF"),
    (b"%PDF-1.7\ncorrupt\n%%EOF", "INVALID_PDF"), (b"%PDF-1.7\n" + b"x" * MAX_INPUT_BYTES + b"%%EOF", "INPUT_TOO_LARGE")],
    ids=["zero-bytes", "wrong-signature", "corrupt-parser-input", "over-eight-megabytes"])
def test_malformed_empty_oversized_rejected(raw, code):
    with pytest.raises(ExtractionError, match=code): inspect_pdf(raw)


@pytest.mark.parametrize("kind,code", [("encrypted", "ENCRYPTED_PDF"), ("blank", "EMPTY_PDF"),
    ("eleven_pages", "PAGE_LIMIT"), ("attachment", "UNSUPPORTED_PDF"), ("oversize_page", "RESOURCE_LIMIT")])
def test_parser_security_limits(kind, code):
    with pymupdf.open() as pdf:
        for _ in range(11 if kind == "eleven_pages" else 1):
            page = pdf.new_page(width=15000 if kind == "oversize_page" else 595)
            if kind != "blank": page.insert_text((50, 80), "Synthetic invoice content. This is sufficiently long native text.")
        if kind == "attachment": pdf.embfile_add("attached.txt", b"untrusted data")
        raw = pdf.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="test-owner", user_pw="test-user") if kind == "encrypted" else pdf.tobytes()
    with pytest.raises(ExtractionError, match=code): inspect_pdf(raw)


def test_partial_extraction_preserves_none(native_documents):
    output = wire()
    output.update(net=None, tax=None, total=None)
    output["lines"][0].update(qty=None, unit_price_net=None, net=None)
    invoice, claims = parse_response(json.dumps(output))
    result = ground_evidence(invoice, claims, native_documents["HAPPY_CLEAN"])
    assert result.net is None and result.tax is None and result.total is None
    assert result.lines[0].qty is None
    assert evaluate(build_context(result, VENDORS, POS, HISTORY), PolicyV1()).outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("kind", ["invalid_json", "timeout", "transient"])
def test_bounded_retries(kind):
    first = {"invalid_json": "not JSON", "timeout": TimeoutError(),
             "transient": ExtractionError("PROVIDER_UNAVAILABLE", retryable=True)}[kind]
    fake = FakeProvider([first, json.dumps(wire())])
    result = run((ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes(), fake)
    assert result.metadata.model_calls == 2 and len(fake.calls) == 2
    assert result.metadata.attempts[0].error_code is not None


@pytest.mark.parametrize("code", ["RATE_LIMIT", "AUTHORIZATION", "PROVIDER_REJECTED", "MODEL_UNAVAILABLE"])
def test_unrecoverable_errors_do_not_switch_model(code):
    fake = FakeProvider([ExtractionError(code)])
    stronger = FakeProvider(model="TEST_ONLY-strong")
    with pytest.raises(ExtractionError) as error:
        run((ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes(), fake, escalation_provider=stronger)
    assert error.value.code == code and error.value.calls == 1
    assert len(error.value.attempts) == 1
    assert not stronger.calls


def test_timeout_is_enforced_on_hanging_provider():
    async def hang():
        await asyncio.sleep(5)
    fake = FakeProvider([hang, hang])
    with pytest.raises(ExtractionError, match="PROVIDER_TIMEOUT") as error:
        run((ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes(), fake, model_timeout_seconds=.01)
    assert error.value.calls == 2


@pytest.mark.parametrize("kind,reason", [("invalid", "INVALID_STRUCTURED_RESPONSE"), ("missing", "MISSING_CRITICAL_FACTS"), ("evidence", "NATIVE_EVIDENCE_UNSUPPORTED")])
def test_one_quality_escalation_uses_same_schema(kind, reason):
    output = wire()
    if kind == "missing": output["net"] = None
    if kind == "evidence": output["evidence"] = []
    primary = FakeProvider(["bad JSON" if kind == "invalid" else json.dumps(output)])
    strong = FakeProvider([json.dumps(wire())], model="TEST_ONLY-strong")
    result = run((ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes(), primary, escalation_provider=strong)
    assert len(primary.calls) == len(strong.calls) == 1
    assert result.metadata.selected_model_id == strong.model_id
    assert result.metadata.escalation_reason == reason
    assert result.metadata.model_calls == 2


def test_invalid_stronger_response_is_not_repeated():
    primary = FakeProvider(["bad JSON"])
    strong = FakeProvider(["bad JSON"], model="TEST_ONLY-strong")
    with pytest.raises(ExtractionError, match="MODEL_OUTPUT_JSON") as error:
        run((ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes(), primary, escalation_provider=strong)
    assert error.value.calls == 2 and len(strong.calls) == 1


@pytest.mark.parametrize('change', ['amount', 'row_count', 'no_new_evidence'])
def test_stronger_reply_cannot_remove_or_change_primary_invoice_facts(change):
    partial = wire()
    partial['evidence'] = []
    revised = wire()
    if change == 'amount':
        revised['total'] = '1.00'
    elif change == 'row_count':
        revised['lines'] = []
    else:
        revised['evidence'] = []
    primary = FakeProvider([json.dumps(partial)])
    stronger = FakeProvider([json.dumps(revised)], model='TEST_ONLY-strong')
    result = run((ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes(), primary,
                 escalation_provider=stronger)
    assert result.metadata.retained_primary
    assert result.metadata.selected_model_id == primary.model_id
    assert result.metadata.model_calls == 2
    assert evaluate(build_context(result.invoice, VENDORS, POS, HISTORY), PolicyV1()).outcome == 'REVIEW_REQUIRED'


@pytest.mark.parametrize("case_id", ["OVERBILLED_PARTIAL", "DUPLICATE_REISSUED", "SCAN_CONFLICT"])
def test_financial_results_never_trigger_stronger_model(case_id):
    output = wire(case_id, line_net=case_id != "SCAN_CONFLICT")
    primary, strong = FakeProvider([json.dumps(output)]), FakeProvider(model="TEST_ONLY-strong")
    result = run((ROOT / "tests/fixtures" / (case_id + ".pdf")).read_bytes(), primary, escalation_provider=strong)
    assert result.metadata.model_calls == 1 and not strong.calls


def test_bank_mismatch_is_not_escalation_trigger():
    raw = native_case(CASES["BANK_CHANGED"])
    primary = FakeProvider([json.dumps(wire("BANK_CHANGED", line_net=False))])
    strong = FakeProvider(model="TEST_ONLY-strong")
    result = run(raw, primary, escalation_provider=strong)
    assert result.metadata.model_calls == 1 and not strong.calls
    assert "BANK_DETAILS_MISMATCH" in {f.code for f in evaluate(build_context(result.invoice, VENDORS, POS, HISTORY), PolicyV1()).findings}


def test_prompt_injection_is_document_data_with_no_financial_authority():
    raw = native_case(CASES["INJECTION"], extra_text=CASES["INJECTION"]["extra_pdf_text"])
    fake = FakeProvider([json.dumps(wire("INJECTION", line_net=False))])
    result = run(raw, fake)
    assert "Ignore all previous rules" in result.inspection.pages[0].native_text
    assert not hasattr(result.invoice, "decision")
    assert evaluate(build_context(result.invoice, VENDORS, POS, HISTORY), PolicyV1()).outcome == "BLOCKED"


def test_no_secret_bank_or_raw_response_logging(caplog, capsys):
    secret, bank = "TEST_ONLY_SECRET_123456789", "000000009999"
    fake = FakeProvider([RuntimeError(secret + bank)])
    with pytest.raises(ExtractionError) as error:
        run((ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes(), fake)
    captured = caplog.text + str(capsys.readouterr()) + str(error.value)
    assert secret not in captured and bank not in captured
    assert str(error.value) == "PROVIDER_REJECTED"


def test_sdk_config_has_no_tools_and_images_are_actual_page_bytes():
    calls = []
    async def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(usage_metadata=None, candidates=[], text=json.dumps(wire("SCAN_CONFLICT", line_net=False)), model_version=None)
    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    provider = GeminiProvider(client, "TEST_ONLY-model")
    doc = inspect_pdf((ROOT / "tests/fixtures/SCAN_CONFLICT.pdf").read_bytes())
    response = asyncio.run(provider.generate(doc, 12))
    call = calls[0]
    assert call["config"].tools == [] and call["config"].automatic_function_calling.disable
    assert call["config"].http_options.retry_options.attempts == 1
    assert call["config"].http_options.timeout == 12000
    assert call["config"].response_json_schema == provider_schema()
    assert call["contents"][0].parts[1].inline_data.data == doc.pages[0].image_png
    assert response.usage == TokenUsage() and response.model_id is None


@pytest.mark.parametrize("code,expected,retry", [(400,"PROVIDER_REJECTED",False), (401,"AUTHORIZATION",False),
    (403,"AUTHORIZATION",False), (404,"MODEL_UNAVAILABLE",False), (429,"RATE_LIMIT",False), (503,"PROVIDER_UNAVAILABLE",True)])
def test_sdk_error_mapping_is_sanitized(code, expected, retry):
    error = provider_error(SimpleNamespace(code=code, message="sensitive provider payload"))
    assert error.code == expected and error.retryable == retry
    assert "sensitive" not in str(error)


def test_environment_configuration_allows_only_two_models(monkeypatch):
    monkeypatch.setenv("GEMINI_ESCALATION_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "TEST_ONLY_NEVER_REAL_KEY")
    monkeypatch.setenv("GEMINI_SCAN_MODEL", "third-model")
    with pytest.raises(ExtractionError, match="CONFIGURATION"): GeminiSettings.from_environment()
    monkeypatch.setenv("GEMINI_SCAN_MODEL", "gemini-3.5-flash-lite")
    settings = GeminiSettings.from_environment()
    assert settings.scan_model == settings.primary_model
    assert "TEST_ONLY_NEVER_REAL_KEY" not in repr(settings)


def test_short_lived_parser_memory_limit_is_enforced():
    import os
    import subprocess
    import sys
    code = """from app.documents.limits import constrain_process_memory, PARSER_MEMORY_BYTES
job = constrain_process_memory()
try:
    allocation = bytearray(PARSER_MEMORY_BYTES + 1024 * 1024)
    print('UNBOUNDED')
except MemoryError:
    print('MEMORY_LIMIT_ENFORCED')
"""
    env = {key: os.environ[key] for key in ('PATH','SYSTEMROOT','WINDIR') if key in os.environ}
    env['PYTHONPATH'] = str(ROOT / 'backend')
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=8, env=env)
    assert result.returncode == 0
    assert result.stdout.strip() == b'MEMORY_LIMIT_ENFORCED'


def test_parser_timeout_is_sanitized_and_secrets_not_inherited(monkeypatch):
    import subprocess
    from app.documents import inspection
    monkeypatch.setenv('GEMINI_API_KEY','TEST_ONLY_SECRET_DO_NOT_INHERIT')
    def timeout(*args, **kwargs):
        assert kwargs['shell'] is False
        assert kwargs['timeout'] == 12
        assert 'GEMINI_API_KEY' not in kwargs['env']
        raise subprocess.TimeoutExpired(args[0], 12)
    monkeypatch.setattr(inspection.subprocess, 'run', timeout)
    with pytest.raises(ExtractionError, match='PARSER_TIMEOUT'):
        inspect_pdf((ROOT / 'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes())


def test_scan_stronger_model_is_attempted_at_most_once_even_on_outage():
    primary = FakeProvider()
    strong = FakeProvider([ExtractionError('PROVIDER_UNAVAILABLE', retryable=True)], model='TEST_ONLY-strong')
    with pytest.raises(ExtractionError) as error:
        run((ROOT / 'tests/fixtures/SCAN_CONFLICT.pdf').read_bytes(), primary, escalation_provider=strong, scan_provider=strong)
    assert error.value.calls == 1 and len(strong.calls) == 1 and not primary.calls


def test_unrecoverable_escalation_quota_is_technical_failure():
    primary = FakeProvider(['bad JSON'])
    strong = FakeProvider([ExtractionError('RATE_LIMIT', provider_status=429)], model='TEST_ONLY-strong')
    with pytest.raises(ExtractionError) as error:
        run((ROOT / 'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes(), primary, escalation_provider=strong)
    assert error.value.code == 'RATE_LIMIT' and error.value.calls == 2
    assert error.value.attempts[-1].provider_http_status == 429
    assert error.value.elapsed_ms is not None
    assert error.value.attempts[-1].usage == TokenUsage()


@pytest.mark.parametrize('arguments', [{'max_attempts':3},{'model_timeout_seconds':46},{'model_timeout_seconds':0}])
def test_invalid_call_bounds_rejected_before_provider(arguments):
    provider=FakeProvider()
    with pytest.raises(ExtractionError, match='CONFIGURATION'):
        run(b'',provider,**arguments)
    assert not provider.calls


def test_third_scan_provider_is_rejected():
    with pytest.raises(ExtractionError, match='CONFIGURATION'):
        run(b'',FakeProvider(),scan_provider=FakeProvider(model='third'))


def test_mixed_single_page_renders_and_does_not_promote_ocr_layer():
    scan=(ROOT / 'tests/fixtures/SCAN_CONFLICT.pdf').read_bytes()
    with pymupdf.open(stream=scan,filetype='pdf') as pdf:
        pdf[0].insert_text((40,40),'Synthetic hidden or partial OCR text. Invoice number: SCAN_CONFLICT-2026')
        raw=pdf.tobytes()
    inspected=inspect_pdf(raw)
    assert inspected.route == 'mixed'
    assert inspected.pages[0].image_png
    invoice,claims=parse_response(json.dumps(wire('SCAN_CONFLICT',line_net=False)))
    invoice=ground_evidence(invoice,claims,inspected)
    assert not any(ref.evidence_state=='NATIVE_VERIFIED' for ref in invoice.evidence)


def test_repeated_contradictory_label_is_ambiguous():
    with pymupdf.open(stream=(ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes(),filetype='pdf') as pdf:
        pdf[0].insert_text((48,720),'Net subtotal: INR 49000')
        inspected=inspect_pdf(pdf.tobytes())
    invoice,claims=parse_response(json.dumps(wire()))
    result=ground_evidence(invoice,claims,inspected)
    assert next(ref for ref in result.evidence if ref.field=='net').evidence_state=='SOURCE_LOCATED_UNVERIFIED'


def test_numeric_normalization_uses_actual_printed_raw_value():
    case=deepcopy(CASES['HAPPY_CLEAN'])
    case['net']='48,000.00'
    inspected=inspect_pdf(native_case(case))
    output=wire(line_net=False)
    for claim in output['evidence']:
        if claim['field']=='net': claim.update(raw_value='48,000.00',quote='Net subtotal: INR 48,000.00')
    invoice,claims=parse_response(json.dumps(output))
    result=ground_evidence(invoice,claims,inspected)
    assert next(ref for ref in result.evidence if ref.field=='net').evidence_state=='NATIVE_VERIFIED'


def test_sdk_returned_tool_call_is_never_executed(native_documents):
    from google.genai import types
    async def generate(**kwargs):
        part=types.Part.from_function_call(name='authorize_payment',args={'amount':'1'})
        return SimpleNamespace(usage_metadata=None,candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))],text='',model_version=None)
    client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    with pytest.raises(ExtractionError,match='PROVIDER_REJECTED'):
        asyncio.run(GeminiProvider(client,'TEST_ONLY-model').generate(native_documents['HAPPY_CLEAN'],12))


def test_model_metadata_does_not_prove_unsupported_method_access():
    async def get(**kwargs):
        return SimpleNamespace(supported_actions=['embedContent'])
    client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(get=get)))
    with pytest.raises(ExtractionError,match='MODEL_UNAVAILABLE'):
        asyncio.run(verify_model(client,'TEST_ONLY-model'))


def test_private_schema_bounds_still_apply_after_generation_simplification():
    schema=provider_schema()
    assert 'maxLength' not in json.dumps(schema) and 'pattern' not in json.dumps(schema)
    output=wire()
    output['net']='1' * 19
    with pytest.raises(ExtractionError,match='MODEL_OUTPUT_SCHEMA'):parse_response(json.dumps(output))
    output=wire()
    output['lines']=output['lines'] * 51
    with pytest.raises(ExtractionError,match='MODEL_OUTPUT_SCHEMA'):parse_response(json.dumps(output))


def test_configured_adapter_wires_only_environment_models(monkeypatch):
    monkeypatch.setenv("GEMINI_ESCALATION_ENABLED", "true")
    from app.ai import gemini
    seen=[]
    async def get(**kwargs):
        seen.append(kwargs['model'])
        return SimpleNamespace(name='models/'+kwargs['model'],version='TEST_ONLY-version',supported_actions=['generateContent'])
    async def generate(**kwargs):
        seen.append(kwargs['model'])
        return SimpleNamespace(usage_metadata=None,candidates=[],text=json.dumps(wire()),model_version='TEST_ONLY-reported')
    async def close():pass
    client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(get=get,generate_content=generate),aclose=close),close=lambda:None)
    monkeypatch.setenv('GEMINI_API_KEY','TEST_ONLY-key')
    monkeypatch.delenv('GEMINI_SCAN_MODEL',raising=False)
    monkeypatch.setattr(gemini,'make_client',lambda settings:client)
    result=asyncio.run(gemini.extract_configured_pdf((ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes()))
    assert result.metadata.model_calls==1
    assert seen==['gemini-3.5-flash-lite','gemini-3.5-flash-lite']  # Unused optional metadata is lazy.


def test_buyer_heading_cannot_verify_supplier_identity():
    with pymupdf.open(stream=(ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes(),filetype='pdf') as pdf:
        pdf[0].insert_text((48,125),'Bill to:')
        document=inspect_pdf(pdf.tobytes())
    invoice,claims=parse_response(json.dumps(wire()))
    result=ground_evidence(invoice,claims,document)
    assert next(ref for ref in result.evidence if ref.field=='vendor_name_raw').evidence_state!='NATIVE_VERIFIED'


def test_line_value_from_another_item_cannot_verify_current_item():
    case=deepcopy(CASES['HAPPY_CLEAN'])
    first={**case['lines'][0],'qty':'4'}
    second={**case['lines'][0],'item_code':'SECOND-ITEM','description':'Another item','qty':'5'}
    case['lines']=[first,second]
    document=inspect_pdf(native_case(case))
    output=wire(line_net=False)
    output['lines'][0]['qty']='5'
    for claim in output['evidence']:
        if claim['field']=='lines[0].qty':claim.update(raw_value='5',quote='Quantity: 5')
    invoice,claims=parse_response(json.dumps(output))
    result=ground_evidence(invoice,claims,document)
    assert next(ref for ref in result.evidence if ref.field=='lines[0].qty').evidence_state!='NATIVE_VERIFIED'


def test_visible_bank_instructions_cannot_be_silently_declared_absent():
    output=wire('BANK_CHANGED',line_net=False)
    output['bank_instructions']=None
    output['evidence']=[claim for claim in output['evidence'] if not claim['field'].startswith('bank_instructions.')]
    provider=FakeProvider([json.dumps(output),json.dumps(output)])
    with pytest.raises(ExtractionError,match='MODEL_OUTPUT_UNUSABLE') as error:
        run(native_case(CASES['BANK_CHANGED']),provider)
    assert error.value.calls==2


@pytest.mark.parametrize('case_id', ['HAPPY_CLEAN', 'SCAN_CONFLICT'])
def test_primary_only_never_constructs_or_checks_optional_model(monkeypatch, case_id):
    from app.ai import gemini
    seen, constructed = [], []
    async def get(**kwargs):
        seen.append(('metadata',kwargs['model']))
        assert kwargs['model']=='gemini-3.5-flash-lite'
        return SimpleNamespace(name='models/'+kwargs['model'],version='TEST_ONLY',supported_actions=['generateContent'])
    async def generate(**kwargs):
        seen.append(('generation',kwargs['model']))
        return SimpleNamespace(usage_metadata=None,candidates=[],text=json.dumps(wire(case_id)),model_version='TEST_ONLY-primary')
    async def close():pass
    client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(get=get,generate_content=generate),aclose=close),close=lambda:None)
    real_provider=gemini.GeminiProvider
    def provider(*args,**kwargs):
        constructed.append(args[1])
        return real_provider(*args,**kwargs)
    monkeypatch.setenv('GEMINI_API_KEY','TEST_ONLY-key')
    monkeypatch.setenv('GEMINI_ESCALATION_ENABLED','false')
    monkeypatch.setenv('GEMINI_ESCALATION_MODEL','invalid-unused-optional-model')
    monkeypatch.setenv('GEMINI_ESCALATION_THINKING_LEVEL','invalid-unused-setting')
    monkeypatch.setenv('GEMINI_SCAN_MODEL','invalid-unused-scan-override')
    monkeypatch.setattr(gemini,'make_client',lambda settings:client)
    monkeypatch.setattr(gemini,'GeminiProvider',provider)
    result=asyncio.run(gemini.extract_configured_pdf((ROOT/'tests/fixtures'/(case_id+'.pdf')).read_bytes()))
    assert constructed==['gemini-3.5-flash-lite']
    assert seen==[('metadata','gemini-3.5-flash-lite'),('generation','gemini-3.5-flash-lite')]
    assert result.metadata.model_calls==1
    if case_id=='SCAN_CONFLICT': assert result.invoice.lines[0].net is None


@pytest.mark.parametrize('condition',['incomplete','uncertain'])
@pytest.mark.parametrize('error_code',['PROVIDER_UNAVAILABLE','PROVIDER_TIMEOUT','RATE_LIMIT'])
def test_valid_primary_survives_optional_outage_without_evidence_upgrade(native_documents,condition,error_code):
    output=wire()
    if condition=='incomplete': output['tax']=None
    else: output['evidence']=[]
    invoice,claims=parse_response(json.dumps(output))
    expected=ground_evidence(invoice,claims,native_documents['HAPPY_CLEAN'])
    primary=FakeProvider([json.dumps(output)])
    stronger=FakeProvider([ExtractionError(error_code,provider_status=429 if error_code=='RATE_LIMIT' else 503 if error_code=='PROVIDER_UNAVAILABLE' else None)],model='TEST_ONLY-strong')
    result=run((ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes(),primary,escalation_provider=stronger)
    assert result.invoice==expected
    assert result.metadata.retained_primary is True
    assert result.metadata.selected_model_id==primary.model_id
    assert result.metadata.model_calls==2 and len(result.metadata.attempts)==2
    assert result.metadata.attempts[0].error_code is None
    assert result.metadata.attempts[1].error_code==error_code
    assert result.metadata.attempts[1].actual_model_id is None
    assert result.metadata.attempts[1].usage==TokenUsage()
    assert result.metadata.elapsed_ms>=sum(a.elapsed_ms for a in result.metadata.attempts)
    assert evaluate(build_context(result.invoice,VENDORS,POS,HISTORY),PolicyV1()).outcome=='REVIEW_REQUIRED'


def test_retained_uncertain_primary_can_still_be_business_blocked():
    output=wire('OVERBILLED_PARTIAL')
    output['evidence']=[]
    primary=FakeProvider([json.dumps(output)])
    stronger=FakeProvider([ExtractionError('RATE_LIMIT')],model='TEST_ONLY-strong')
    result=run((ROOT/'tests/fixtures/OVERBILLED_PARTIAL.pdf').read_bytes(),primary,escalation_provider=stronger)
    assert result.metadata.retained_primary
    assert evaluate(build_context(result.invoice,VENDORS,POS,HISTORY),PolicyV1()).outcome=='BLOCKED'


@pytest.mark.parametrize('code',['PROVIDER_UNAVAILABLE','PROVIDER_TIMEOUT','RATE_LIMIT'])
def test_unusable_primary_does_not_become_successful_fallback(code):
    primary=FakeProvider(['invalid JSON'])
    stronger=FakeProvider([ExtractionError(code)],model='TEST_ONLY-strong')
    with pytest.raises(ExtractionError) as error:
        run((ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes(),primary,escalation_provider=stronger)
    assert error.value.code==code and error.value.calls==2


def test_scan_unstated_line_net_cleared_without_fixing_stated_gross():
    fake=FakeProvider([json.dumps(wire('SCAN_CONFLICT',line_net=True))])
    result=run((ROOT/'tests/fixtures/SCAN_CONFLICT.pdf').read_bytes(),fake)
    assert result.invoice.lines[0].net is None
    assert result.invoice.total==Decimal('86200')
    assert result.invoice.net+result.invoice.tax==Decimal('82600')
    assert result.invoice.total-(result.invoice.net+result.invoice.tax)==Decimal('3600')
    ref=next(r for r in result.invoice.evidence if r.field=='lines[0].net')
    assert ref.normalized_value is None and ref.evidence_state!='NATIVE_VERIFIED'
    assert ref.raw_value=='70000'  # Keep the untrusted claim for audit; not an invoice-stated fact.
    assert all(r.evidence_state!='NATIVE_VERIFIED' for r in result.invoice.evidence)
    decision=evaluate(build_context(result.invoice,VENDORS,POS,HISTORY),PolicyV1())
    assert decision.outcome=='REVIEW_REQUIRED'
    arithmetic=next(f for f in decision.findings if f.code=='TOTAL_RECONCILIATION_FAILED')
    assert {v.name:v.value for v in arithmetic.values}['difference']=='3600'


def test_primary_only_is_default_even_with_stale_optional_configuration(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','TEST_ONLY-key')
    monkeypatch.delenv('GEMINI_ESCALATION_ENABLED',raising=False)
    monkeypatch.setenv('GEMINI_ESCALATION_MODEL','unused-invalid-value')
    settings=GeminiSettings.from_environment()
    assert settings.escalation_enabled is False
    assert settings.active_models==('gemini-3.5-flash-lite',)


@pytest.mark.parametrize('status',[503,429,'timeout'])
def test_optional_metadata_failure_retains_primary_without_counting_generation(monkeypatch,status):
    from app.ai import gemini
    from google.genai import errors
    seen=[]
    output=wire()
    output['evidence']=[]
    async def get(**kwargs):
        seen.append(('metadata',kwargs['model']))
        if kwargs['model']=='gemini-3.6-flash':
            if status=='timeout': raise TimeoutError()
            raise errors.APIError(status,{'error':{'code':status,'message':'TEST_ONLY_sensitive_error'}})
        return SimpleNamespace(name='models/'+kwargs['model'],version='TEST_ONLY',supported_actions=['generateContent'])
    async def generate(**kwargs):
        seen.append(('generation',kwargs['model']))
        assert kwargs['model']=='gemini-3.5-flash-lite'
        return SimpleNamespace(usage_metadata=None,candidates=[],text=json.dumps(output),model_version='TEST_ONLY-primary')
    async def close():pass
    client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(get=get,generate_content=generate),aclose=close),close=lambda:None)
    monkeypatch.setenv('GEMINI_API_KEY','TEST_ONLY-key')
    monkeypatch.setenv('GEMINI_ESCALATION_ENABLED','true')
    monkeypatch.setenv('GEMINI_ESCALATION_MODEL','gemini-3.6-flash')
    monkeypatch.setenv('GEMINI_SCAN_MODEL','gemini-3.5-flash-lite')
    monkeypatch.setattr(gemini,'make_client',lambda settings:client)
    result=asyncio.run(gemini.extract_configured_pdf((ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes()))
    assert result.metadata.retained_primary
    assert result.metadata.model_calls==1  # Optional metadata request never reached generation.
    assert len(result.metadata.attempts)==2
    assert result.metadata.attempts[-1].inference_called is False
    assert result.metadata.attempts[-1].actual_model_id is None
    assert result.metadata.attempts[-1].error_code=={503:'PROVIDER_UNAVAILABLE',429:'RATE_LIMIT','timeout':'PROVIDER_TIMEOUT'}[status]
    assert seen==[('metadata','gemini-3.5-flash-lite'),('generation','gemini-3.5-flash-lite'),('metadata','gemini-3.6-flash')]


def test_empty_structured_primary_is_unusable_not_a_review_result():
    output=wire()
    for key in output:
        output[key]=[] if key in ('lines','evidence') else None
    provider=FakeProvider([json.dumps(output),json.dumps(output)])
    with pytest.raises(ExtractionError,match='MODEL_OUTPUT_UNUSABLE') as error:
        run((ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes(),provider)
    assert error.value.calls==2


def test_primary_outage_without_any_facts_remains_technical_failure():
    provider=FakeProvider([ExtractionError('PROVIDER_UNAVAILABLE',retryable=True),ExtractionError('PROVIDER_UNAVAILABLE',retryable=True)])
    stronger=FakeProvider(model='TEST_ONLY-strong')
    with pytest.raises(ExtractionError,match='PROVIDER_UNAVAILABLE') as error:
        run((ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes(),provider,escalation_provider=stronger)
    assert error.value.calls==2 and not stronger.calls


def test_retained_primary_does_not_log_optional_provider_payload(caplog,capsys):
    secret,bank='TEST_ONLY_SECRET_DO_NOT_LOG','000000009999'
    output=wire()
    output['evidence']=[]
    error=ExtractionError('RATE_LIMIT')
    error.args=(secret+bank,)
    result=run((ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes(),FakeProvider([json.dumps(output)]),
               escalation_provider=FakeProvider([error],model='TEST_ONLY-strong'))
    captured=caplog.text+str(capsys.readouterr())+repr(result)
    assert secret not in captured and bank not in captured
    assert result.metadata.attempts[-1].error_code=='RATE_LIMIT'


def test_mixed_document_keeps_independently_verified_native_line_net():
    with pymupdf.open(stream=(ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes(),filetype='pdf') as native, pymupdf.open(stream=(ROOT/'tests/fixtures/SCAN_CONFLICT.pdf').read_bytes(),filetype='pdf') as scan:
        native.insert_pdf(scan)
        document=inspect_pdf(native.tobytes())
    invoice,claims=parse_response(json.dumps(wire()))
    grounded=ground_evidence(invoice,claims,document)
    assert grounded.lines[0].net==Decimal('48000')
    assert next(ref for ref in grounded.evidence if ref.field=='lines[0].net').evidence_state=='NATIVE_VERIFIED'


def test_invalid_escalation_flag_cannot_accidentally_enable_calls(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','TEST_ONLY-key')
    monkeypatch.setenv('GEMINI_ESCALATION_ENABLED','tru')
    with pytest.raises(ExtractionError,match='CONFIGURATION'):GeminiSettings.from_environment()



def test_enabled_configured_escalation_still_uses_same_schema(monkeypatch):
    from app.ai import gemini
    seen,schemas=[],[]
    partial=wire()
    partial['net']=None
    async def get(**kwargs):
        seen.append(('metadata',kwargs['model']))
        return SimpleNamespace(name='models/'+kwargs['model'],version='TEST_ONLY',supported_actions=['generateContent'])
    async def generate(**kwargs):
        seen.append(('generation',kwargs['model']))
        schemas.append(kwargs['config'].response_json_schema)
        payload=partial if kwargs['model']=='gemini-3.5-flash-lite' else wire()
        return SimpleNamespace(usage_metadata=None,candidates=[],text=json.dumps(payload),model_version='TEST_ONLY-'+kwargs['model'])
    async def close():pass
    client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(get=get,generate_content=generate),aclose=close),close=lambda:None)
    monkeypatch.setenv('GEMINI_API_KEY','TEST_ONLY-key')
    monkeypatch.setenv('GEMINI_ESCALATION_ENABLED','true')
    monkeypatch.setenv('GEMINI_SCAN_MODEL','gemini-3.5-flash-lite')
    monkeypatch.setattr(gemini,'make_client',lambda settings:client)
    result=asyncio.run(gemini.extract_configured_pdf((ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes()))
    assert seen==[('metadata','gemini-3.5-flash-lite'),('generation','gemini-3.5-flash-lite'),('metadata','gemini-3.6-flash'),('generation','gemini-3.6-flash')]
    assert result.metadata.model_calls==2
    assert result.metadata.selected_model_id=='gemini-3.6-flash'
    assert not result.metadata.retained_primary
    assert schemas[0]==schemas[1]
    assert all(ref.evidence_state=='NATIVE_VERIFIED' for ref in result.invoice.evidence)


def test_metadata_deadline_does_not_count_an_unstarted_inference():
    async def get(**kwargs):
        await asyncio.sleep(5)
    async def generate(**kwargs):
        raise AssertionError('Generation must not start after metadata timeout')
    client=SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(get=get,generate_content=generate)))
    output=wire()
    output['tax']=None
    primary=FakeProvider([json.dumps(output)])
    optional=GeminiProvider(client,'TEST_ONLY-strong',verify_access=True)
    result=run((ROOT/'tests/fixtures/HAPPY_CLEAN.pdf').read_bytes(),primary,
               escalation_provider=optional,model_timeout_seconds=.02)
    assert result.metadata.retained_primary
    assert result.metadata.model_calls==1
    assert result.metadata.attempts[-1].inference_called is False
    assert result.metadata.attempts[-1].error_code=='PROVIDER_TIMEOUT'
