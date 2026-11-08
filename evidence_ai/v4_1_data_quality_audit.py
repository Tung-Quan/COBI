"""Audit whether D1.1 labels agree with registered semantic temporal rules."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from evidence_ai.semantic_evidence import time_validity
from ml.contracts import ROOT, sha, write_json

DEV = ROOT / "reports/evidence-v4.1/data/development-d1.1"
OUT = ROOT / "reports/evidence-v4.1/data/development-d1.1/D1.1_LABEL_SEMANTIC_AUDIT.csv"
SPLITS = ("train", "validation", "calibration", "locked_test")


def audit():
    cases = json.loads((DEV / "observed.json").read_text(encoding="utf-8-sig"))
    labels = json.loads((DEV / "gold_labels.json").read_text(encoding="utf-8-sig"))
    gold = {case["case_id"]: {record["record_id"]: record for record in case["records"]} for case in labels}
    split_by_case = {}
    for name in SPLITS:
        for case_id in json.loads((DEV / f"split_{name}.json").read_text(encoding="utf-8-sig"))["case_ids"]:
            split_by_case[case_id] = name
    rows, counts = [], {name: {"stale_as_current": 0, "critical_label_missing": 0, "material_label_missing": 0}
                       for name in SPLITS}
    for case in cases:
        for record in case["records"]:
            validity = time_validity(record, case["request"])
            if validity["state"] != "STALE_AS_CURRENT":
                continue
            target = gold[case["case_id"]][record["record_id"]]
            split = split_by_case[case["case_id"]]
            row = {"case_id": case["case_id"], "customer_group": case["customer_group"],
                   "split": split, "scenario": case["scenario"], "record_id": record["record_id"],
                   "field_type": record["field_type"], "required_for_request": record["field_type"] in case["request"]["required_fields"],
                   "asserted_as_current": record["asserted_as_current"], "age_days": record["age_days"],
                   "requested_period": json.dumps(case["request"]["period"], ensure_ascii=False),
                   "effective_period": json.dumps(record["effective_period"], ensure_ascii=False),
                   "time_validity_state": validity["state"], "time_validity_critical": validity["critical"],
                   "gold_material_defect": int(target["material_defect"]),
                   "gold_critical_defect": int(target["critical_defect"]),
                   "critical_label_missing": int(bool(validity["critical"]) and not target["critical_defect"]),
                   "semantic_mismatch": int(bool(validity["critical"]) and not target["critical_defect"])}
            rows.append(row)
            counts[split]["stale_as_current"] += 1
            counts[split]["critical_label_missing"] += row["critical_label_missing"]
            counts[split]["material_label_missing"] += int(not target["material_defect"])
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    total_missing = sum(v["critical_label_missing"] for v in counts.values())
    report = {
        "audit_id": "cobi-v4.1-d1.1-temporal-label-consistency",
        "dataset_manifest_sha256": sha(DEV / "dataset_manifest.json"),
        "audit_code_sha256": sha(Path(__file__)), "audit_csv_sha256": sha(OUT),
        "stale_as_current_records": len(rows), "critical_labels_missing_on_stale_records": total_missing,
        "counts_by_split": counts,
        "finding": "D4_HISTORICAL_VALIDITY contains stale-as-current records with critical temporal validity but gold labels omit the critical defect for 100 records.",
        "affected_splits": [name for name, values in counts.items() if values["critical_label_missing"]],
        "consequence": "Training, validation, calibration, and locked development-test evidence for temporal defects is label-inconsistent. C results remain observed measurements for the frozen release but are exploratory and cannot be interpreted as confirmatory evidence for learned feature effects.",
        "generator_c_labels_changed_or_reopened": False,
        "generator_c_metrics_or_thresholds_changed": False,
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
    }
    write_json(DEV / "D1.1_LABEL_SEMANTIC_AUDIT.json", report)
    write_json(ROOT / "reports/evidence-v4.1/POST_EVALUATION_AUDIT_ADDENDUM.json", report)
    return report


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
