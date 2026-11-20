"""Strict values and redacted, field-level diagnostics for Gemini wire replies."""
from decimal import Decimal
import json

import pytest

from app.documents.schema import parse_response
from app.documents.types import ExtractionError
from test_document_engine import wire


@pytest.mark.parametrize("value", ["0", "1234.50", "-1.123456", "999999999999999999.000001"])
def test_decimal_string_is_exact(value):
    reply = wire()
    reply["net"] = value
    reply["evidence"][0]["field"] = "lines[0].qty"
    invoice, claims = parse_response(json.dumps(reply))
    assert invoice.net.as_tuple() == Decimal(value).as_tuple()
    assert claims[0].field == "lines[0].qty"


@pytest.mark.parametrize("value", ["NaN", "1000 USD", "12,34", "1e3", "1.1234567", "1.2.3", 1000])
def test_invalid_money_is_rejected(value):
    reply = wire()
    reply["net"] = value
    with pytest.raises(ExtractionError, match="MODEL_OUTPUT_SCHEMA"):
        parse_response(json.dumps(reply))


def test_schema_logs_only_safe_field_paths_and_value_shapes(caplog):
    reply = wire()
    reply["net"] = "1,234.50"
    reply["evidence"][0].update(field="lines[0].quantity", raw_value="sensitive-invoice-content")
    reply["confidential-provider-key"] = "sensitive-account-number"

    with pytest.raises(ExtractionError, match="MODEL_OUTPUT_SCHEMA"):
        parse_response(json.dumps(reply))

    assert "$.net issue=string_pattern_mismatch constraint=decimal_string" in caplog.text
    assert "markers=comma" in caplog.text
    assert "$.evidence[0].field issue=string_pattern_mismatch constraint=evidence_field_key" in caplog.text
    assert "bracketed_line:quantity" in caplog.text
    assert "$.<unknown> issue=extra_forbidden" in caplog.text
    for private_value in ("1,234.50", "lines[0].quantity", "confidential-provider-key",
                          "sensitive-invoice-content", "sensitive-account-number"):
        assert private_value not in caplog.text
