from fastapi import HTTPException

from app.evidence_research_v41 import router, summary


def test_v41_summary_is_read_only_and_keeps_bank_validation_blocked():
    result = summary()
    assert result["validation_status"] == "EVIDENCE_AI_VALIDATION_BLOCKED"
    assert result["routing_authorized"] is False
    assert result["approval_authorized"] is False
    assert result["read_only"] is True
    assert result["synthetic_only"] is True
    assert result["status"] == "POST_UNBLINDING_EXPLORATORY"
    assert result["models"]["M2_XGBOOST"]["availability"] == "BLOCKED_DEPENDENCY"
    assert len(result["model_artifacts"]) == 5
    assert {row["source_type"] for row in result["sources"]} == {"statement", "payroll", "merchant"}
    assert all(route.methods == {"GET"} for route in router.routes)


def test_v41_summary_contains_only_registered_scenario_rows():
    result = summary()
    assert len(result["scenarios"]) == 7
    assert {row["scenario"] for row in result["scenarios"]} == {
        "C1_GROSS_NET_PERIODS", "C2_SAME_PERIOD_CORRUPTION", "C3_CORRECTION_LINEAGE",
        "C4_TIME_VALIDITY", "C5_NONCOMPARABLE_SUBJECT_ACCOUNT",
        "C6_TRUE_COMPARABLE_CONFLICT", "C7_HELD_OUT_SOURCE_PAIR",
    }
    assert "canonical_truth" not in result
    assert "gold_labels" not in result
