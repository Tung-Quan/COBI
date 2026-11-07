from __future__ import annotations

from app.db import get_calculation_result


def test_portfolio_and_demo_detail_are_seeded(client):
    response = client.get("/api/applications")
    assert response.status_code == 200
    assert response.json()["total"] >= 6
    detail = client.get("/api/applications/DEMO-001")
    assert detail.status_code == 200
    assert detail.json()["routing"]["recommended_route"] == "FAST_TRACK_CANDIDATE"


def test_simulation_changes_inputs_and_is_not_persisted(client):
    before = client.get("/api/applications/DEMO-001").json()
    saved_before = get_calculation_result("DEMO-001")
    response = client.post("/api/applications/DEMO-001/simulate", json={
        "existing_monthly_debt_vnd": 2_000_000,
        "evidence_quality": 0.55,
        "consent": True,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["persisted"] is False
    assert result["assessment"]["features"]["existing_monthly_debt_vnd"] == 2_000_000
    assert result["scenario_inputs"]["existing_monthly_debt_vnd"] == 2_000_000
    assert result["assessment"]["confidence"]["score"] != before["assessment"]["confidence"]["score"]
    after = client.get("/api/applications/DEMO-001").json()
    assert after["existing_monthly_debt_vnd"] == before["existing_monthly_debt_vnd"]
    saved_after = get_calculation_result("DEMO-001")
    assert saved_after["assessment"] == saved_before["assessment"]
    assert saved_after["routing"] == saved_before["routing"]


def test_case_assessment_is_persisted_in_results_table(client):
    assert client.get("/api/applications/DEMO-001").status_code == 200
    stored = get_calculation_result("DEMO-001")
    assert stored is not None
    assert stored["assessment"]["risk"]["label"] == "DEMO_RISK_SCORE_NOT_CALIBRATED"
    assert stored["routing"]["recommended_route"] == "FAST_TRACK_CANDIDATE"


def test_simulator_mandatory_failure_blocks_scores(client):
    response = client.post("/api/applications/DEMO-001/simulate", json={"consent": False})
    assert response.status_code == 200
    assert response.json()["assessment"]["risk"] is None
    assert response.json()["routing"]["recommended_route"] == "HOLD_FOR_HUMAN_HANDLING"


def test_review_reason_required_and_override_must_be_eligible(client):
    missing_reason = client.post("/api/applications/DEMO-001/review", json={"action": "confirm_route", "reason": "short"})
    assert missing_reason.status_code == 422
    blocked_override = client.post("/api/applications/DEMO-001/review", json={
        "action": "override_route", "route": "HOLD_FOR_HUMAN_HANDLING", "reason": "This route should not be selected here."
    })
    assert blocked_override.status_code == 422


def test_eligible_override_requires_and_records_explanation(client):
    response = client.post("/api/applications/DEMO-001/review", json={
        "action": "override_route",
        "route": "STANDARD_REVIEW",
        "reason": "Officer selected standard review after checking the case notes.",
    })
    assert response.status_code == 200
    event = response.json()["event"]
    assert event["action"] == "override_route"
    assert event["route"] == "STANDARD_REVIEW"
    assert "case notes" in event["reason"]
    assert event["details"]["loan_approval_created"] is False


def test_audit_history_is_appended_and_human_confirmation_is_not_loan_approval(client):
    for reason in ("Evidence source checked by the simulated officer.", "Affordability notes reviewed in this case."):
        result = client.post("/api/applications/DEMO-001/review", json={"action": "confirm_route", "reason": reason})
        assert result.status_code == 200
        assert result.json()["loan_approval_created"] is False
    history = client.get("/api/applications/DEMO-001").json()["review_history"]
    assert [event["reason"] for event in history[:2]] == [
        "Affordability notes reviewed in this case.", "Evidence source checked by the simulated officer."
    ]
    assert len({event["event_id"] for event in history}) == 2


def test_export_and_evaluation_label_hypothetical_metrics(client):
    evaluation = client.get("/api/evaluation").json()
    assert evaluation["measured_model_performance"] is False
    assert client.get("/api/export").json()["data_classification"] == "Synthetic demonstration data only"
    assert client.get("/api/metrics").json()["synthetic_operational_snapshot"] is True
