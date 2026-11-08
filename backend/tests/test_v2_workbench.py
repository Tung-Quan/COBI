from copy import deepcopy

import pytest

from app.calculations import calculate_application, financial_features, payment, validate_weights
from app.db import connect, get_calculation_result


def test_new_fixture_exact_calculations(client):
    case = client.get("/api/applications/DEMO-001").json()
    result = case["assessment"]
    assert result["fixture_version"] == "demo-001-v2.0"
    assert case["purchase_amount_vnd"] == case["loan_amount_vnd"] + case["own_funds_vnd"] == 6_000_000
    assert result["features"]["income_p25_vnd"] == 11_250_000
    assert result["confidence"]["score"] == pytest.approx(0.820938, abs=1e-6)
    assert result["affordability"]["dti_capacity_vnd"] == pytest.approx(2_906_250)
    assert result["affordability"]["residual_capacity_vnd"] == pytest.approx(4_842_187.5)
    assert result["affordability"]["pmt_vnd"] == 1_250_000
    assert result["expected_loss"]["ead_assumption_vnd"] == 5_000_000
    assert result["expected_loss"]["amount_vnd"] == pytest.approx(result["risk"]["score"] * 0.45 * 5_000_000)
    assert result["checkout_pd"] is None
    assert result["expected_loss"]["actual_expected_loss_status"] == "EL_NOT_ESTIMABLE"
    assert len(result["expected_loss"]["sensitivity"]) == 9


def test_legacy_fixture_retains_purchase_and_exact_contract_payment(baseline):
    result = calculate_application(baseline)
    assert result.assessment["affordability"]["pmt_vnd"] == 2_400_000
    assert result.assessment["expected_loss"]["ead_assumption_vnd"] == 9_600_000
    assert result.assessment["fixture_version"] == "legacy-or-submitted"


def test_affordability_stress_and_payment_numerics(baseline):
    case = baseline | {"monthly_income_vnd": [2_000_000, 2_000_000, 24_000_000, 24_000_000]}
    assert financial_features(case)["income_p25_vnd"] == 2_000_000
    result = calculate_application(case)
    assert result.assessment["affordability"]["dti_capacity_vnd"] > 0
    assert result.assessment["affordability"]["stressed_payment_capacity_vnd"] == 0
    assert "FAST_TRACK_CANDIDATE" not in result.routing["eligible_routes"]
    assert payment(5_000_000, 0, 4) == 1_250_000
    assert payment(5_000_000, 1e-20, 4) == pytest.approx(1_250_000)
    assert payment(5_000_000, 0.12, 4) == pytest.approx(1_281_405.47, abs=0.01)
    with pytest.raises(ValueError):
        validate_weights({"coverage": float("nan"), "consistency": .3, "recency": .2, "verification": .2})


@pytest.mark.parametrize("change", [
    {"consent": False}, {"identity_verified": False}, {"source_permission": False}, {"funding_reconciled": False},
    {"loan_amount_vnd": 99_000_000}, {"own_funds_vnd": 1_000_000},
])
def test_each_gate_is_fail_closed(baseline, change):
    result = calculate_application(baseline | change, {"FAST_TRACK_CANDIDATE": 0})
    assert result.assessment["scoring_performed"] is False
    assert all(result.assessment[key] is None for key in ("confidence", "risk", "expected_loss", "checkout_pd"))
    assert result.routing["eligible_routes"] == ["HOLD_FOR_HUMAN_HANDLING"]


def test_evidence_verification_separate_and_future_data_blocked(baseline):
    case = deepcopy(baseline)
    case["evidence"]["extraction_confidence"] = 1.0
    result = calculate_application(case)
    assert result.assessment["evidence_trace"]["extraction_confidence"] == 1
    assert result.assessment["confidence"]["subscores"]["verification"] == 0.9
    case["evidence"]["sources"][0]["feature_event_at"] = "2026-11-09T00:00:00+07:00"
    assert not calculate_application(case).assessment["scoring_performed"]
    case["evidence"]["sources"][0]["feature_event_at"] = "2026-11-06T00:00:00+07:00"
    assert calculate_application(case).assessment["scoring_performed"]
    case["evidence"]["critical_failure"] = True
    assert not calculate_application(case).assessment["scoring_performed"]


def test_incompatible_benchmark_isolated_from_scenario(client):
    url = "/api/assessments/simulate"
    before = client.post(url, json={"application_id": "DEMO-001"}).json()
    after = client.post(url, json={"application_id": "DEMO-001", "benchmark_model_id": "uci350-v2.0-selected"}).json()
    assert after["assessment"]["pd_status"] == "PD_UNAVAILABLE_SCHEMA_MISMATCH"
    assert after["assessment"]["checkout_pd"] is None
    assert after["assessment"]["risk_source"] == "SYNTHETIC_HEURISTIC"
    assert after["assessment"]["risk"] == before["assessment"]["risk"]
    assert after["routing"] == before["routing"]
    assert not after["persisted"]
    assert client.post(url, json={"application_id": "DEMO-001", "route_costs_vnd": {"UNKNOWN": 0}}).status_code == 422
    assert client.post(url, json={"application_id": "DEMO-001", "route_costs_vnd": {"STANDARD_REVIEW": -1}}).status_code == 422
    assert client.post(url, content='{"application_id":"DEMO-001","existing_monthly_debt_vnd":NaN}',
                       headers={"Content-Type": "application/json"}).status_code == 422


def test_consent_revocation_and_audit_are_sticky(client):
    path = "/api/applications/DEMO-001"
    before = client.get("/api/assessments/DEMO-001/explanation").json()
    review = client.post(path + "/review", json={"action": "confirm_route", "reason": "Reviewed synthetic funding and capacity."}).json()
    assert review["event"]["details"]["input_sha256"] == before["trace"]["input_sha256"]
    assert review["event"]["details"]["policy_version"] == "cobi-checkout-policy-v2.0"
    assert review["event"]["details"]["model_version"] == "synthetic-logistic-v2.0"
    revoked = client.post(path + "/revoke-consent", json={"reason": "Synthetic applicant withdrew permission."})
    assert revoked.status_code == 200
    assert get_calculation_result("DEMO-001") is None
    assert client.get("/api/assessments/DEMO-001/explanation").json()["inputs"] is None
    scenario = client.post(path + "/simulate", json={"consent": True}).json()
    assert scenario["assessment"]["scoring_performed"] is False
    assert client.post(path + "/revoke-consent", json={"reason": "Same withdrawal received a second time."}).status_code == 409
    with connect() as connection, pytest.raises(Exception, match="append-only"):
        connection.execute("DELETE FROM audit_events WHERE application_id = 'DEMO-001'")
