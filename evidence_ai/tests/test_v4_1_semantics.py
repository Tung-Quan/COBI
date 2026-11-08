from datetime import date, timedelta

from evidence_ai.semantic_evidence import (
    FEATURE_NAMES, case_feature_array, semantic_validation, source_comparability, time_validity,
)
from evidence_ai.v4_1_generator_c import generate


def _record(record_id="r1", value=10_000_000, **changes):
    start = date(2026, 1, 1)
    row = {
        "record_id": record_id, "subject_ref": "borrower-1", "account_ref": "account-1",
        "field_type": "income", "financial_meaning": "salary",
        "effective_period": {"start": start.isoformat(), "end": (start + timedelta(days=29)).isoformat()},
        "source_type": "statement", "provenance": {"document_ref": "doc-1", "page": 1, "extraction_version": "test"},
        "original_value": value, "original_unit": "VND", "normalized_value": value, "normalized_unit": "VND",
        "gross_net_basis": "NET", "transaction_direction": "INFLOW", "correction_status": "NONE",
        "correction_of": None, "verification_status": "VERIFIED", "missingness": "NONE", "uncertainty": .1,
        "asserted_as_current": True, "observed_at": "2026-02-01", "age_days": 20,
        "ocr_quality": .95, "text": "income record",
    }
    row.update(changes)
    return row


def _request(period=None):
    if period is None:
        start = date(2026, 1, 1)
        period = {"start": start.isoformat(), "end": (start + timedelta(days=29)).isoformat()}
    return {"period": period, "requested_at": "2026-02-01", "purpose": "test", "required_fields": ["income"]}


def test_same_semantic_period_is_comparable():
    assert source_comparability(_record(), _record("r2", source_type="payroll"))["status"] == "COMPARABLE"


def test_gross_net_and_different_periods_are_not_comparable():
    gross = _record("r2", gross_net_basis="GROSS")
    assert source_comparability(_record(), gross)["reason"] == "GROSS_NET_BASIS_MISMATCH"
    old = _record("r3", effective_period={"start": "2025-01-01", "end": "2025-01-30"})
    assert source_comparability(_record(), old)["reason"] == "NON_OVERLAPPING_EFFECTIVE_PERIODS"


def test_missing_account_and_high_uncertainty_return_unknown():
    assert source_comparability(_record(), _record("r2", account_ref=None))["status"] == "UNKNOWN"
    assert source_comparability(_record(), _record("r2", uncertainty=.9))["status"] == "UNKNOWN"


def test_correction_link_is_not_a_contradiction():
    old = _record("old", correction_status="SUPERSEDED", correction_of="new")
    new = _record("new", value=4_000_000, correction_status="CORRECTED", correction_of="old")
    assert source_comparability(old, new)["reason"] == "CORRECTION_LINEAGE_SUPERSEDES_PRIOR_VERSION"


def test_historical_evidence_can_remain_applicable_and_stale_current_is_critical():
    old_period = {"start": "2025-01-01", "end": "2025-01-30"}
    historical = _record(effective_period=old_period, asserted_as_current=False, age_days=400)
    assert time_validity(historical, _request(old_period))["state"] == "HISTORICAL_APPLICABLE"
    stale = _record(effective_period=old_period, asserted_as_current=True, age_days=400)
    result = time_validity(stale, _request())
    assert result["state"] == "STALE_AS_CURRENT" and result["critical"] is True


def test_numeric_difference_only_alerts_for_comparable_pair():
    left = _record("left")
    right = _record("right", 12_000_000, source_type="payroll")
    case = {"request": _request(), "records": [left, right]}
    assert any(a["reason"] == "COMPARABLE_VALUE_CONFLICT" for a in semantic_validation(case)["documents"]["left"]["alerts"])
    right["gross_net_basis"] = "GROSS"
    result = semantic_validation(case)
    assert not any(a["reason"] == "COMPARABLE_VALUE_CONFLICT" for item in result["documents"].values() for a in item["alerts"])


def test_feature_contract_and_c_generator_are_reproducible():
    case = {"case_id": "case", "customer_group": "group", "scenario": "test",
            "request": _request(), "records": [_record()]}
    x, mask, _ = case_feature_array([case], capacity=2)
    assert x.shape == (1, 2, len(FEATURE_NAMES)) and mask.sum() == 1
    a = generate(seed=2026110802, groups_per_scenario=2)
    b = generate(seed=2026110802, groups_per_scenario=2)
    assert a == b
    observed, labels, _ = a
    assert len(observed) == 28 and len(labels) == 28
    assert all(2 <= len(case["records"]) <= 6 for case in observed)
    c7_pairs = [tuple(record["source_type"] for record in case["records"][:2])
                for case in observed if case["scenario"] == "C7_HELD_OUT_SOURCE_PAIR"]
    assert set(c7_pairs) == {("payroll", "merchant")}
