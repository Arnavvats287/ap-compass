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
    reply["net"] = "12,34.50"
    reply["evidence"][0].update(field="lines[0].quantity", raw_value="sensitive-invoice-content")
    reply["confidential-provider-key"] = "sensitive-account-number"

    with pytest.raises(ExtractionError, match="MODEL_OUTPUT_SCHEMA"):
        parse_response(json.dumps(reply))

    assert "$.net issue=string_pattern_mismatch constraint=decimal_string" in caplog.text
    assert "markers=comma" in caplog.text
    assert "$.evidence[0].field issue=string_pattern_mismatch constraint=evidence_field_key" in caplog.text
    assert "bracketed_line:quantity" in caplog.text
    assert "$.<unknown> issue=extra_forbidden" in caplog.text
    for private_value in ("12,34.50", "lines[0].quantity", "confidential-provider-key",
                          "sensitive-invoice-content", "sensitive-account-number"):
        assert private_value not in caplog.text

@pytest.mark.parametrize("printed,exact", [
    ("17,000.00", "17000.00"),
    ("1,25,000.50", "125000.50"),
    (" INR 20,060.00 ", "20060.00"),
    ("-1,500.50", "-1500.50"),
    ("Rs. 5,400.00", "5400.00"),
    ("\u20b9 5,400.00", "5400.00"),
])
def test_grouped_model_amounts_are_normalized_without_losing_precision(printed, exact):
    reply = wire()
    reply["net"] = printed
    reply["lines"][0]["net"] = printed
    invoice, claims = parse_response(json.dumps(reply))
    assert invoice.net.as_tuple() == invoice.lines[0].net.as_tuple() == Decimal(exact).as_tuple()
    assert all(claim.model_dump() == original for claim, original in zip(claims, reply["evidence"], strict=True))


@pytest.mark.parametrize("value", ["USD 1,000.00", "INR 1.234,56", "1,000.0000001", "1,234,567,890,123,456,789.00"])
def test_normalization_rejects_conflicting_or_out_of_bounds_amounts(value):
    reply = wire()
    reply["net"] = value
    with pytest.raises(ExtractionError, match="MODEL_OUTPUT_SCHEMA"):
        parse_response(json.dumps(reply))


def test_denomination_cannot_supply_invoice_currency_or_be_used_as_quantity():
    reply = wire()
    reply["currency"] = None
    reply["net"] = "INR 1,000"
    with pytest.raises(ExtractionError, match="MODEL_OUTPUT_SCHEMA"):
        parse_response(json.dumps(reply))
    reply = wire()
    reply["lines"][0]["qty"] = "INR 1,000"
    with pytest.raises(ExtractionError, match="MODEL_OUTPUT_SCHEMA"):
        parse_response(json.dumps(reply))
    reply["lines"][0]["qty"] = None
    invoice, _ = parse_response(json.dumps(reply))
    assert invoice.lines[0].qty is None
