from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from research.v4_2.tools.audit_d1_1 import audit_dataset


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = ROOT / "research/v4_2/schemas"
EXAMPLE_DIR = ROOT / "research/v4_2/examples"


def _schemas():
    schemas = {path.name: json.loads(path.read_text(encoding="utf-8")) for path in SCHEMA_DIR.glob("*.schema.json")}
    registry = Registry()
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry


def test_all_schemas_and_illustrative_cases_validate():
    schemas, registry = _schemas()
    validator = Draft202012Validator(schemas["evidence_bundle.schema.json"], registry=registry, format_checker=FormatChecker())
    examples = sorted(EXAMPLE_DIR.glob("*.json"))
    assert len(examples) >= 11
    for path in examples:
        bundle = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(bundle), key=lambda error: list(error.path))
        assert not errors, f"{path.name}: {[error.message for error in errors]}"
        claim_ids = {claim["claim_id"] for claim in bundle["claims"]}
        assert all(claim["case_id"] == bundle["case_id"] for claim in bundle["claims"])
        assert bundle["case_action"]["case_id"] == bundle["case_id"]
        for pair in bundle["pairs"]:
            assert pair["case_id"] == bundle["case_id"]
            assert set(pair["claim_ids"]) <= claim_ids
            assert {row["claim_id"] for row in pair["document_attribution"]} <= set(pair["claim_ids"])
            if pair["relationship"] == "SUPERSEDES":
                direction = pair["supersedes_direction"]
                assert direction["superseded_claim_id"] in pair["claim_ids"]
                assert direction["superseding_claim_id"] in pair["claim_ids"]
                assert direction["superseded_claim_id"] != direction["superseding_claim_id"]


def test_contradiction_does_not_automatically_attribute_error():
    bundle = json.loads((EXAMPLE_DIR / "same_period_conflict_unresolved_attribution.json").read_text(encoding="utf-8"))
    pair = bundle["pairs"][0]
    assert pair["relationship"] == "CONTRADICTORY"
    assert {item["status"] for item in pair["document_attribution"]} == {"UNRESOLVED"}
    assert bundle["case_action"]["reference_action"] == "HUMAN_REVIEW"


def test_unknown_currency_is_not_coerced_to_zero_or_non_conflict():
    bundle = json.loads((EXAMPLE_DIR / "missing_currency_unknown.json").read_text(encoding="utf-8"))
    assert bundle["claims"][1]["amount"] == {
        "state": "KNOWN", "value": 1000, "currency_state": "MISSING", "currency": None,
        "unit_state": "MISSING", "unit": None
    }
    assert bundle["pairs"][0]["comparability"] == "UNKNOWN"
    assert bundle["pairs"][0]["relationship"] == "UNRESOLVED"
    assert bundle["case_action"]["reference_action"] == "REQUEST_MORE_EVIDENCE"


def test_schema_rejects_conflict_attribution_without_independent_evidence():
    schemas, registry = _schemas()
    validator = Draft202012Validator(schemas["evidence_bundle.schema.json"], registry=registry, format_checker=FormatChecker())
    bundle = json.loads((EXAMPLE_DIR / "same_period_conflict_unresolved_attribution.json").read_text(encoding="utf-8"))
    bundle["pairs"][0]["document_attribution"][0]["status"] = "VERIFIED_INCORRECT"
    assert not validator.is_valid(bundle)


def test_schema_rejects_contradiction_when_comparability_is_unknown():
    schemas, registry = _schemas()
    validator = Draft202012Validator(schemas["evidence_bundle.schema.json"], registry=registry, format_checker=FormatChecker())
    bundle = json.loads((EXAMPLE_DIR / "missing_currency_unknown.json").read_text(encoding="utf-8"))
    bundle["pairs"][0]["relationship"] = "CONTRADICTORY"
    assert not validator.is_valid(bundle)


def test_d1_1_counts_and_proposals_are_source_backed_and_unapproved():
    report, rows = audit_dataset()
    assert report["stale_as_current_records"] == 200
    assert report["candidate_critical_omissions"] == 100
    assert report["expected_omissions_match"] is True
    assert {name: values["candidate_critical_omissions"] for name, values in report["counts_by_split"].items()} == {
        "train": 60, "validation": 15, "calibration": 15, "locked_test": 10
    }
    pending = [row for row in rows if row["candidate_label_status"] == "PENDING_ADJUDICATION"]
    assert len(pending) == 100
    assert all(row["approved_gold"] == "NO" for row in pending)
    assert all(row["reviewer_status"] == "PENDING_INDEPENDENT_POLICY_ADJUDICATION" for row in pending)
    assert report["generator_c_modified"] is False
    assert report["generator_c_predictions_or_metrics_modified"] is False


def test_edge_case_fixtures_keep_period_timestamp_and_claim_linkage_explicit():
    missing_period = json.loads((EXAMPLE_DIR / "missing_applicable_period.json").read_text(encoding="utf-8"))
    assert missing_period["claims"][0]["period"]["state"] == "MISSING"
    assert missing_period["pairs"][0]["comparability"] == "UNKNOWN"
    assert missing_period["pairs"][0]["relationship"] == "UNRESOLVED"

    timestamp_case = json.loads((EXAMPLE_DIR / "conflicting_source_timestamps.json").read_text(encoding="utf-8"))
    timestamps = {c["source"]["source_issued_at"] for c in timestamp_case["claims"]}
    assert len(timestamps) == 2
    assert timestamp_case["pairs"][0]["comparability"] == "UNKNOWN"

    multi_record = json.loads((EXAMPLE_DIR / "multiple_records_one_claim.json").read_text(encoding="utf-8"))
    assert len({c["claim_group_id"] for c in multi_record["claims"]}) == 1
    assert len({c["document"]["document_id"] for c in multi_record["claims"]}) == 2

    corroboration = json.loads((EXAMPLE_DIR / "third_source_corroboration.json").read_text(encoding="utf-8"))
    assert len(corroboration["claims"]) == 3
    assert all(pair["claim_ids"][0] != pair["claim_ids"][1] for pair in corroboration["pairs"])
    assert all(item["status"] == "UNRESOLVED" for item in corroboration["pairs"][0]["document_attribution"])


def test_source_timestamp_missingness_is_not_implicit():
    schemas, registry = _schemas()
    validator = Draft202012Validator(schemas["evidence_bundle.schema.json"], registry=registry, format_checker=FormatChecker())
    bundle = json.loads((EXAMPLE_DIR / "conflicting_source_timestamps.json").read_text(encoding="utf-8"))
    bundle["claims"][0]["source"]["source_timestamp_state"] = "UNKNOWN"
    assert not validator.is_valid(bundle)


def test_adjudication_csv_has_100_blank_reviewer_decisions():
    import csv
    review_path = ROOT / "research/v4_2/D1_1_LABEL_REVIEW.csv"
    with review_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 100
    assert all(row["adjudication_status"] == "PENDING_ADJUDICATION" for row in rows)
    assert all(row["approved_gold"] == "NO" for row in rows)
    assert all(not row["reviewer_decision"] and not row["reviewer_name"] and not row["review_date"] for row in rows)


def test_audit_outputs_use_lf_for_reproducible_artifact_hashes(tmp_path):
    import hashlib

    from research.v4_2.tools.audit_d1_1 import write_audit

    report = write_audit(tmp_path)
    csv_bytes = (tmp_path / "D1_1_PROPOSED_CHANGELOG.csv").read_bytes()
    json_bytes = (tmp_path / "D1_1_AUDIT_SUMMARY.json").read_bytes()
    assert b"\r\n" not in csv_bytes
    assert b"\r\n" not in json_bytes
    assert report["proposal_csv_sha256"] == hashlib.sha256(csv_bytes).hexdigest()


def test_artifact_manifest_excludes_test_runtime_caches():
    from research.v4_2.tools.make_artifact_manifest import build

    cache_dirs = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".hypothesis"}
    assert all(not (set(Path(item["path"]).parts) & cache_dirs) for item in build()["files"])


def test_claim_group_linkage_keeps_distinct_records_and_documents():
    bundle = json.loads((EXAMPLE_DIR / "multiple_records_one_claim.json").read_text(encoding="utf-8"))
    grouped = [claim for claim in bundle["claims"] if claim["claim_group_id"] == "financial-claim-001"]
    assert len(grouped) == 2
    assert {claim["case_id"] for claim in grouped} == {bundle["case_id"]}
    assert len({claim["claim_id"] for claim in grouped}) == 2
    assert len({claim["document"]["document_id"] for claim in grouped}) == 2


def test_metric_denominators_separate_pair_document_and_case_units():
    from research.v4_2.tools.metric_contracts import case_denominators, document_attribution_denominators, pair_confusion

    matrix = pair_confusion(["COMPARABLE", "UNKNOWN", "NOT_COMPARABLE"], ["COMPARABLE", "NOT_COMPARABLE", "NOT_COMPARABLE"])
    assert matrix["UNKNOWN"]["NOT_COMPARABLE"] == 1
    docs = document_attribution_denominators([
        {"gold_status": "VERIFIED_INCORRECT"}, {"gold_status": "UNRESOLVED"}, {"gold_status": "VERIFIED_CORRECT"}
    ])
    assert docs["eligible_rows"] == 2
    assert docs["incorrect_document_denominator"] == 1
    assert docs["excluded_unresolved_or_unverified"] == 1

    cases = case_denominators([
        {"gold_critical": "CRITICAL", "predicted_action": "NO_FLAG"},
        {"gold_critical": "CRITICAL", "predicted_action": "HUMAN_REVIEW"},
        {"gold_critical": "NONCRITICAL", "predicted_action": "REQUEST_MORE_EVIDENCE"},
        {"gold_critical": "NONCRITICAL", "predicted_action": "NO_FLAG"},
    ])
    assert cases["critical_case_denominator"] == 2
    assert cases["cleared_case_denominator"] == 2
    assert cases["action_workload_numerator"] == 2
    assert cases["review_numerator"] == 1 and cases["request_numerator"] == 1
    assert cases["critical_miss_rate_all_critical"] == 0.5
    assert cases["critical_miss_rate_among_cleared"] == 0.5
    assert cases["action_workload_rate"] == 0.5


def test_metric_denominators_return_none_for_empty_target_population():
    from research.v4_2.tools.metric_contracts import case_denominators
    assert case_denominators([])["action_workload_rate"] is None
    assert case_denominators([{"gold_critical": "NONCRITICAL", "predicted_action": "NO_FLAG"}])["critical_miss_rate_all_critical"] is None


def test_release_integrity_audit_uses_repository_case_for_v4_manifest():
    from research.v4_2.tools.audit_release_integrity import v4_status

    result = v4_status()
    assert result["path"] == "reports/evidence-v4/final_manifest.json"
    assert result["total"] == 96
