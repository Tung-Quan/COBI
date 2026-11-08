from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.calculations_v1 import (
    CS_WEIGHTS,
    CalculationBundle,
    calculate_application,
    confidence_score,
    financial_features,
    route_application,
    validate_weights,
)


def test_demo_001_regression_values(baseline):
    result = calculate_application(baseline)
    assert isinstance(result, CalculationBundle)
    assert result.assessment["features"]["mean_income_vnd"] == pytest.approx(12_000_000)
    assert result.assessment["confidence"]["score"] == pytest.approx(0.820938, abs=1e-6)
    assert result.assessment["risk"]["score"] == pytest.approx(0.039675, abs=1e-7)
    assert result.assessment["affordability"]["stressed_payment_capacity_vnd"] == pytest.approx(2_906_250)
    assert result.assessment["expected_loss"]["amount_vnd"] == pytest.approx(119_024, abs=1)
    assert result.routing["recommended_route"] == "FAST_TRACK_CANDIDATE"


def test_confidence_weights_are_validated_and_result_is_bounded(baseline):
    assert validate_weights() == CS_WEIGHTS
    assert 0 <= confidence_score(baseline)["score"] <= 1
    with pytest.raises(ValueError, match="sum to 1"):
        validate_weights({"coverage": 0.3, "consistency": 0.3, "recency": 0.2, "verification": 0.1})


def test_features_are_deterministic_and_traceable(baseline):
    features = financial_features(baseline)
    assert features["mean_income_vnd"] == pytest.approx(12_000_000)
    assert features["history_months"] == 11
    assert features["history_coverage"] == pytest.approx(11 / 12)
    assert features["existing_dti_ratio"] == pytest.approx(1_293_750 / 12_000_000)


def test_failed_mandatory_gate_blocks_all_automated_scores(baseline):
    case = {**baseline, "consent": False}
    result = calculate_application(case)
    assert not result.assessment["scoring_performed"]
    assert result.assessment["confidence"] is None
    assert result.assessment["risk"] is None
    assert result.assessment["expected_loss"] is None
    assert result.routing["eligible_routes"] == ["HOLD_FOR_HUMAN_HANDLING"]
    assert result.routing["recommended_route"] == "HOLD_FOR_HUMAN_HANDLING"


def test_low_pd_cannot_override_affordability_or_evidence(baseline):
    case = {**baseline, "proposed_installment_vnd": 4_000_000}
    result = calculate_application(case)
    assert result.assessment["risk"]["score"] < 0.10
    assert not result.assessment["affordability"]["installment_eligible"]
    assert "FAST_TRACK_CANDIDATE" not in result.routing["eligible_routes"]
    low_evidence = {**baseline, "evidence": {**baseline["evidence"], "reconciliation_fields_consistent": 1}}
    constrained = calculate_application(low_evidence)
    assert constrained.assessment["risk"]["score"] < 0.10
    assert constrained.routing["recommended_route"] != "FAST_TRACK_CANDIDATE"


def test_route_cost_selection_is_deterministic_and_only_eligible_routes_win(baseline):
    result = calculate_application(baseline)
    repeated = calculate_application(baseline)
    assert result.routing == repeated.routing
    for route in result.routing["eligible_routes"]:
        assert result.routing["estimated_route_costs_vnd"][result.routing["recommended_route"]] <= result.routing["estimated_route_costs_vnd"][route]
    failed = calculate_application({**baseline, "identity_verified": False})
    assert failed.routing["recommended_route"] in failed.routing["eligible_routes"]
    cheaper_standard = calculate_application(baseline, {"FAST_TRACK_CANDIDATE": 300_000, "STANDARD_REVIEW": 1})
    assert cheaper_standard.routing["recommended_route"] == "STANDARD_REVIEW"


def test_demo_risk_never_claims_training_or_calibration(baseline):
    risk = calculate_application(baseline).assessment["risk"]
    assert risk["label"] == "DEMO_RISK_SCORE_NOT_CALIBRATED"
    assert risk["calibration_status"] == "NOT_TRAINED_OR_CALIBRATED"
    assert risk["reference_parity"] == "UNVERIFIED_REFERENCE_FILES_MISSING"


def test_seed_covers_the_requested_synthetic_scenarios():
    path = Path(__file__).parents[1] / "data" / "seed_applications.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    assert len(cases) >= 6
    assert {tag for item in cases for tag in item["tags"]} >= {
        "Consent missing", "Insufficient evidence", "Affordability failure",
        "High-risk indicators", "Critical verification failure",
    }


def test_seed_scenarios_cover_expected_guardrails():
    path = Path(__file__).parents[1] / "data" / "seed_applications.json"
    cases = {item["application_id"]: item for item in json.loads(path.read_text(encoding="utf-8"))}
    evidence_limited = calculate_application(cases["SYN-003"])
    assert evidence_limited.assessment["confidence"]["score"] < 0.50
    assert evidence_limited.routing["recommended_route"] == "ENHANCED_REVIEW"
    affordability_failed = calculate_application(cases["SYN-004"])
    assert not affordability_failed.assessment["affordability"]["installment_eligible"]
    assert "FAST_TRACK_CANDIDATE" not in affordability_failed.routing["eligible_routes"]
    high_risk = calculate_application(cases["SYN-005"])
    assert high_risk.assessment["risk"]["score"] > 0.25
    assert high_risk.routing["recommended_route"] == "ENHANCED_REVIEW"
    critical = calculate_application(cases["SYN-006"])
    assert not critical.assessment["scoring_performed"]
