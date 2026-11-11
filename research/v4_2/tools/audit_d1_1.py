"""Read-only, audit-only proposal report for the archived V4.1 D1.1 labels.

This module never writes to reports/evidence-v4.1. Its CLI writes only into
research/v4_2, and its proposed labels remain pending independent adjudication.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evidence_ai.semantic_evidence import time_validity


INPUT_DIR = REPO_ROOT / "reports/evidence-v4.1/data/development-d1.1"
OUTPUT_DIR = REPO_ROOT / "research/v4_2"
SPLITS = ("train", "validation", "calibration", "locked_test")
EXPECTED_MISSING_BY_SPLIT = {"train": 60, "validation": 15, "calibration": 15, "locked_test": 10}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def audit_dataset(input_dir: Path = INPUT_DIR) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return an audit report and candidate rows without modifying source data."""
    observed_path = input_dir / "observed.json"
    gold_path = input_dir / "gold_labels.json"
    manifest_path = input_dir / "dataset_manifest.json"
    cases = _load_json(observed_path)
    labels = _load_json(gold_path)
    manifest = _load_json(manifest_path)
    gold_by_case = {
        item["case_id"]: {row["record_id"]: row for row in item["records"]}
        for item in labels
    }
    split_by_case: dict[str, str] = {}
    split_hashes: dict[str, str] = {}
    for split in SPLITS:
        split_path = input_dir / f"split_{split}.json"
        split_hashes[split_path.name] = sha256(split_path)
        for case_id in _load_json(split_path)["case_ids"]:
            if case_id in split_by_case:
                raise ValueError(f"case {case_id} appears in multiple split manifests")
            split_by_case[case_id] = split

    rows: list[dict[str, Any]] = []
    stale_counts: Counter[str] = Counter()
    missing_counts: Counter[str] = Counter()
    for case in cases:
        case_id = case["case_id"]
        if case_id not in split_by_case:
            raise ValueError(f"case {case_id} has no development split assignment")
        split = split_by_case[case_id]
        for record in case["records"]:
            temporal = time_validity(record, case["request"])
            if temporal["state"] != "STALE_AS_CURRENT":
                continue
            old = gold_by_case[case_id][record["record_id"]]
            old_critical = int(bool(old["critical_defect"]))
            candidate_critical = int(bool(temporal["critical"]))
            mismatch = candidate_critical == 1 and old_critical == 0
            stale_counts[split] += 1
            missing_counts[split] += int(mismatch)
            evidence = {
                "asserted_as_current": record.get("asserted_as_current"),
                "age_days": record.get("age_days"),
                "requested_period": case["request"].get("period"),
                "effective_period": record.get("effective_period"),
                "time_validity_state": temporal["state"],
                "time_validity_critical": temporal["critical"],
                "time_validity_reason": temporal["reason"],
                "required_for_request": record.get("field_type") in case["request"].get("required_fields", []),
            }
            rows.append({
                "case_id": case_id,
                "customer_group": case["customer_group"],
                "split": split,
                "scenario": case["scenario"],
                "record_id": record["record_id"],
                "old_material_defect": int(bool(old["material_defect"])),
                "old_critical_defect": old_critical,
                "candidate_critical_defect": candidate_critical if mismatch else old_critical,
                "candidate_label_status": "PENDING_ADJUDICATION" if mismatch else "UNCHANGED",
                "rationale_code": "STALE_CURRENT_OVER_180D_GOLD_OMISSION_D1_1" if mismatch else "NO_CRITICAL_LABEL_OMISSION",
                "supporting_observations_json": json.dumps(evidence, sort_keys=True, separators=(",", ":")),
                "evidence_pointers": json.dumps([
                    f"reports/evidence-v4.1/data/development-d1.1/observed.json#case_id={case_id}&record_id={record['record_id']}",
                    f"reports/evidence-v4.1/data/development-d1.1/gold_labels.json#case_id={case_id}&record_id={record['record_id']}",
                    f"reports/evidence-v4.1/data/development-d1.1/split_{split}.json#case_id={case_id}",
                    "evidence_ai/semantic_evidence.py#time_validity",
                    "evidence_ai/v4_1_generator_dev.py#_make_case:D4_HISTORICAL_VALIDITY",
                ], separators=(",", ":")),
                "uncertainty_status": "POLICY_DEPENDENT_PENDING_REVIEW" if mismatch else "RULE_LABEL_MATCH_ONLY",
                "reviewer_status": "PENDING_INDEPENDENT_POLICY_ADJUDICATION" if mismatch else "NOT_ADJUDICATED_UNCHANGED",
                "approved_gold": "NO",
            })

    missing_by_split = {split: missing_counts[split] for split in SPLITS}
    report = {
        "audit_id": "cobi-v4.2-read-only-d1.1-proposal-audit",
        "status": "AUDIT_ONLY_NO_LABELS_CHANGED",
        "input_dataset_id": manifest["dataset_id"],
        "input_hashes": {
            "dataset_manifest.json": sha256(manifest_path),
            "observed.json": sha256(observed_path),
            "gold_labels.json": sha256(gold_path),
            **split_hashes,
            "time_validity_source": sha256(REPO_ROOT / "evidence_ai/semantic_evidence.py"),
            "development_generator_source": sha256(REPO_ROOT / "evidence_ai/v4_1_generator_dev.py"),
        },
        "stale_as_current_records": sum(stale_counts.values()),
        "candidate_critical_omissions": sum(missing_counts.values()),
        "counts_by_split": {
            split: {"stale_as_current_records": stale_counts[split], "candidate_critical_omissions": missing_by_split[split]}
            for split in SPLITS
        },
        "expected_omissions_match": missing_by_split == EXPECTED_MISSING_BY_SPLIT,
        "proposal_rule": "Candidate critical=1 when the registered V4.1 time_validity rule yields STALE_AS_CURRENT and age_days >= 180; this is a semantic consistency proposal, not approved ground truth.",
        "root_cause_evidence": "D1.1 generator D4 marks only the second deliberately altered record through critical_idx; time_validity independently marks both current-asserted records in each stale case as critical. The first stale record is therefore omitted by generated gold.",
        "approval_status": "PENDING_INDEPENDENT_ADJUDICATION_AND_POLICY_APPROVAL",
        "generator_c_modified": False,
        "generator_c_predictions_or_metrics_modified": False,
    }
    return report, rows


def write_audit(output_dir: Path = OUTPUT_DIR, input_dir: Path = INPUT_DIR) -> dict[str, Any]:
    report, rows = audit_dataset(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "D1_1_PROPOSED_CHANGELOG.csv"
    json_path = output_dir / "D1_1_AUDIT_SUMMARY.json"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report["proposal_csv_sha256"] = sha256(csv_path)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    report = write_audit(args.output_dir)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["expected_omissions_match"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
