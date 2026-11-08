"""Export development hard-negative pairs with semantic and temporal evidence labels."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from evidence_ai.semantic_evidence import FIELD_THRESHOLDS, source_comparability, time_validity
from ml.contracts import ROOT, sha, write_json

DEV = ROOT / "reports/evidence-v4.1/data/development-d1.1"
OUT = ROOT / "reports/evidence-v4.1/data/development-d1.1/HARD_NEGATIVE_PAIRS.csv"


def build():
    cases = json.loads((DEV / "observed.json").read_text(encoding="utf-8-sig"))
    gold_rows = json.loads((DEV / "gold_labels.json").read_text(encoding="utf-8-sig"))
    labels = {row["case_id"]: {item["record_id"]: item for item in row["records"]} for row in gold_rows}
    rows = []
    for case in cases:
        for i, left in enumerate(case["records"]):
            for right in case["records"][i+1:]:
                comparison = source_comparability(left, right)
                left_validity = time_validity(left, case["request"])
                right_validity = time_validity(right, case["request"])
                left_defect = int(labels[case["case_id"]][left["record_id"]]["material_defect"])
                right_defect = int(labels[case["case_id"]][right["record_id"]]["material_defect"])
                left_value, right_value = left["normalized_value"], right["normalized_value"]
                delta = abs(float(left_value) - float(right_value)) if left_value is not None and right_value is not None else None
                threshold = FIELD_THRESHOLDS[left["field_type"]] if left["field_type"] == right["field_type"] else None
                pair_conflict = bool(comparison["status"] == "COMPARABLE" and delta is not None and threshold is not None and delta >= threshold)
                stale_present = left_validity["state"] == "STALE_AS_CURRENT" or right_validity["state"] == "STALE_AS_CURRENT"
                valid_negative = left_defect == right_defect == 0
                rows.append({
                    "case_id": case["case_id"], "customer_group": case["customer_group"], "scenario": case["scenario"],
                    "left_record_id": left["record_id"], "right_record_id": right["record_id"],
                    "left_field": left["field_type"], "right_field": right["field_type"],
                    "left_meaning": left["financial_meaning"], "right_meaning": right["financial_meaning"],
                    "left_source": left["source_type"], "right_source": right["source_type"],
                    "left_original_value": left["original_value"], "left_original_unit": left["original_unit"],
                    "right_original_value": right["original_value"], "right_original_unit": right["original_unit"],
                    "left_normalized_value_vnd": left_value, "right_normalized_value_vnd": right_value,
                    "left_basis": left["gross_net_basis"], "right_basis": right["gross_net_basis"],
                    "left_direction": left["transaction_direction"], "right_direction": right["transaction_direction"],
                    "left_effective_period": json.dumps(left["effective_period"], ensure_ascii=False),
                    "right_effective_period": json.dumps(right["effective_period"], ensure_ascii=False),
                    "left_correction_status": left["correction_status"], "right_correction_status": right["correction_status"],
                    "comparability_status": comparison["status"], "comparability_reason": comparison["reason"],
                    "absolute_difference_vnd": delta, "registered_field_tolerance_vnd": threshold,
                    "pairwise_numeric_conflict": pair_conflict,
                    "left_material_defect": left_defect, "right_material_defect": right_defect,
                    "record_defect_present": int(bool(left_defect or right_defect)),
                    "stale_as_current_present": stale_present,
                    "left_time_validity": left_validity["state"], "right_time_validity": right_validity["state"],
                    "legitimate_hard_negative": valid_negative and (comparison["status"] != "COMPARABLE" or not pair_conflict or scenario_is_valid(case["scenario"])),
                    "interpretation": interpretation(case["scenario"], comparison["status"], pair_conflict,
                                                      valid_negative, stale_present),
                })
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_json(DEV / "HARD_NEGATIVE_MANIFEST.json", {
        "dataset_id": "semantic-evidence-development-d1.1",
        "pair_rows": len(rows), "source_development_manifest_sha256": sha(DEV / "dataset_manifest.json"),
        "hard_negative_pairs_sha256": sha(OUT),
        "pair_material_error_is_not_inferred_from_value_difference": True,
        "pair_numeric_conflict_requires_comparable_semantics": True,
        "stale_as_current_is_separately_labeled": True,
        "labels_are_development_synthetic_gold": True,
    })
    return {"pair_rows": len(rows), "sha256": sha(OUT)}


def scenario_is_valid(scenario):
    return scenario in {"D1_PERIOD_VARIATION", "D2_GROSS_NET", "D3_CORRECTION_LINEAGE",
                        "D4_HISTORICAL_VALIDITY", "D6_ACCOUNT_DIRECTION"}


def interpretation(scenario, status, pair_conflict, valid_negative, stale_present):
    if stale_present:
        return "TIME_VALIDITY_DEFECT" if not valid_negative else "STALE_AS_CURRENT_LABEL_REVIEW"
    if pair_conflict and status == "COMPARABLE":
        return "GENUINE_COMPARABLE_CONTRADICTION" if not valid_negative else "PAIR_FLAGS_VALID_PEER_OF_CORRUPT_RECORD"
    if status == "NOT_COMPARABLE":
        return "LEGITIMATE_DIFFERENCE_NO_CONTRADICTION"
    if status == "UNKNOWN":
        return "INSUFFICIENT_SEMANTIC_INFORMATION_NO_CONTRADICTION"
    return "COMPARABLE_WITHOUT_MATERIAL_CONFLICT"


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
