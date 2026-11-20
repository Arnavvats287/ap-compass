"""Controlled checks for parser-owned header reconciliation and live call admission."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.ai import gemini
from app.documents.schema import parse_response, provider_schema
from app.documents.types import ExtractionError
from source_layout_fixtures import source_layout
from test_document_engine import ROOT, wire
from test_payable_semantics import invoice_pdf
from test_source_generalization import assess, claim


def test_exact_native_value_row_supports_independently_paired_header_fields():
    pdf, reply = source_layout(column_order=True, statement=True)
    for field in ("po_reference", "currency"):
        claim(reply, field)["quote"] = "PO-6001 INR"
    # Formatting of a decimal claim may differ. The saved evidence should use
    # the exact denomination, grouping and value observed in the PDF.
    claim(reply, "total")["raw_value"] = "5900"
    states, decision = assess(pdf, reply)
    assert {states[field] for field in ("po_reference", "currency", "total")} == {"NATIVE_VERIFIED"}
    assert decision.outcome == "READY_FOR_AP"


@pytest.mark.parametrize("field,raw,quote", [
    ("po_reference", "PO-6001", "PO-6001 USD"),  # fabricated context
    ("po_reference", "PO-6001", "PO-6001"),  # naked identifier
    ("total", "USD 5900", "Grand Total INR 5,900.00"),  # inconsistent denomination
    ("total", "5900", "Combined account balance INR 7,700.00"),  # unrelated source row
])
def test_hybrid_header_does_not_promote_conflicted_or_unrelated_claims(field, raw, quote):
    pdf, reply = source_layout(column_order=True, statement=True)
    claim(reply, field).update(raw_value=raw, quote=quote)
    states, decision = assess(pdf, reply)
    assert states[field] != "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


def test_hybrid_header_cannot_select_a_disputed_gross():
    pdf, reply = source_layout(conflict="same_page")
    claim(reply, "total")["raw_value"] = "5900"
    states, decision = assess(pdf, reply)
    assert states["total"] != "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


def test_conflicting_invoice_specific_payable_in_summary_is_not_ignored():
    pdf, reply = invoice_pdf("Grand total", split=True, appendix=(
        (1, 112, 230, "Account summary", None),
        (1, 112, 208, "Payable for this invoice", "INR 4,750.00"),
    ))
    states, decision = assess(pdf, reply)
    assert states["total"] != "NATIVE_VERIFIED"
    assert decision.outcome == "REVIEW_REQUIRED"


@pytest.mark.parametrize("bad_reply,expected", [
    ("{", "MODEL_OUTPUT_JSON"),
    ("{}", "MODEL_OUTPUT_SCHEMA"),
    (json.dumps({field: [] if field in ("lines", "evidence") else None for field in wire()}),
     "MODEL_OUTPUT_UNUSABLE"),
])
def test_runtime_attempts_generation_once_for_distinct_model_output_errors(monkeypatch, bad_reply, expected):
    monkeypatch.setenv("GEMINI_API_KEY", "TEST_ONLY-dummy")
    monkeypatch.setenv("GEMINI_PRIMARY_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_ESCALATION_ENABLED", "false")
    calls = []

    async def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=bad_reply, usage_metadata=None, candidates=[], model_version="TEST_ONLY")

    async def close():
        pass

    sdk = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate), aclose=close),
                          close=lambda: None)
    monkeypatch.setattr(gemini, "make_client", lambda _: sdk)
    with pytest.raises(ExtractionError, match=expected) as error:
        asyncio.run(gemini.extract_runtime_pdf((ROOT / "tests/fixtures/HAPPY_CLEAN.pdf").read_bytes()))
    assert error.value.calls == len(calls) == 1
    assert error.value.attempts[0].error_code == expected
    assert calls[0]["config"].http_options.retry_options.attempts == 1

def test_generation_grammar_explains_decimal_and_evidence_field_formats_without_relaxing_checks():
    schema = provider_schema()
    assert "1234.50" in schema["properties"]["net"]["anyOf"][0]["description"]
    assert "lines[0].qty" in schema["$defs"]["SourceClaim"]["properties"]["field"]["description"]
    for mutation in (lambda payload: payload.update(net="48,000.00"),
                     lambda payload: payload["evidence"][0].update(field="lines.0.qty")):
        payload = wire()
        mutation(payload)
        with pytest.raises(ExtractionError, match="MODEL_OUTPUT_SCHEMA"):
            parse_response(json.dumps(payload))
