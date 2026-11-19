from types import SimpleNamespace

import pytest

from postfix_v1 import BUDGET, MAX_ATTEMPTS, ORDER, diagnostics, skip_reason


@pytest.mark.parametrize("remaining,expected", [(0, True), (1, True), (2, False), (8, False)])
def test_full_ordinary_retry_capacity_required(remaining, expected):
    state = SimpleNamespace(limit=BUDGET, calls=BUDGET - remaining)
    assert bool(skip_reason(True, state, live=True)) is expected


def test_live_preselection_order_and_cap():
    assert MAX_ATTEMPTS == 2 and BUDGET == 8
    assert [case for _, case in ORDER] == ["H04", "OVERBILLED_PARTIAL", "H01", "H05", "H03", "H06"]
    assert skip_reason(False, None, live=True)[0] == "ineligible"
    assert skip_reason(True, None, live=True)[0] == "not_executed"


def test_failed_processing_has_no_field_evidence_or_findings():
    snapshot = SimpleNamespace(decision=None, extracted_invoice=None)
    row = {"case_id": "controlled", "model_calls": 0}
    assert diagnostics(snapshot, row, b"", {}, None) == {
        "case_id": "controlled", "fields": [], "findings": [], "trust_regressions": [], "integrity_flags": [],
    }
