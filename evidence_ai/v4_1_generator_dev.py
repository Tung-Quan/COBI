"""Development-only semantic evidence generator for V4.1 training."""
from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path

import numpy as np

from evidence_ai.semantic_evidence import SOURCE_TYPES
from ml.contracts import ROOT, canonical, sha, write_json

OUT = ROOT / "reports/evidence-v4.1/data/development-d1.1"
DEV_SEED = 2026110801
SCENARIOS = ("D1_PERIOD_VARIATION", "D2_GROSS_NET", "D3_CORRECTION_LINEAGE",
             "D4_HISTORICAL_VALIDITY", "D5_COMPARABLE_CONFLICT", "D6_ACCOUNT_DIRECTION")
FIELDS = ("income", "debt", "purchase")
MEANING = {"income": "salary", "debt": "recurring_debt", "purchase": "purchase_amount"}
FIELD_THRESHOLD = {"income": 500_000.0, "debt": 250_000.0, "purchase": 500_000.0}


def _period(start: date, days: int = 29):
    return {"start": start.isoformat(), "end": (start + timedelta(days=days)).isoformat()}


def _make_record(rng, group_idx, case_idx, doc_idx, field, value, period, source, *,
                 basis="NET", direction="INFLOW", account=None, subject=None, correction="NONE",
                 correction_of=None, asserted_current=True, age=20, observed_at=None, verified="VERIFIED",
                 missingness="NONE", uncertainty=None, meaning=None):
    record_id = f"D-rec-g{group_idx:04d}-c{case_idx}-r{doc_idx}"
    observed_at = observed_at or date(2026, 8, 1) + timedelta(days=(group_idx + case_idx + doc_idx) % 30)
    val = None if missingness == "REQUIRED_VALUE_MISSING" else int(value)
    return {
        "record_id": record_id,
        "subject_ref": subject or f"D-subject-{group_idx:04d}",
        "account_ref": account or f"D-account-{group_idx:04d}-{field}",
        "field_type": field,
        "financial_meaning": meaning or MEANING[field],
        "effective_period": period,
        "source_type": source,
        "provenance": {"document_ref": f"D-doc-{group_idx:04d}-{case_idx}-{doc_idx}",
                       "page": int(doc_idx + 1), "extraction_version": "semantic-parser-sim-1"},
        "original_value": val,
        "original_unit": "VND",
        "normalized_value": val,
        "normalized_unit": "VND" if val is not None else "UNKNOWN",
        "gross_net_basis": basis,
        "transaction_direction": direction,
        "correction_status": correction,
        "correction_of": correction_of,
        "verification_status": verified,
        "missingness": missingness,
        "uncertainty": float(uncertainty if uncertainty is not None else rng.uniform(.01, .18)),
        "asserted_as_current": bool(asserted_current),
        "observed_at": observed_at.isoformat(),
        "age_days": int(age),
        "ocr_quality": float(rng.uniform(.60, .99)),
        "text": f"{source} {MEANING[field]} {basis.lower()} amount {val if val is not None else 'missing'} period {period['start']} to {period['end']}",
    }


def _base_amounts(rng):
    return {"income": int(rng.integers(6_000_000, 24_000_001)),
            "debt": int(rng.integers(500_000, 8_000_001)),
            "purchase": int(rng.integers(2_000_000, 20_000_001))}


def _make_case(rng, scenario, group_idx, case_idx):
    field = FIELDS[(group_idx + case_idx) % len(FIELDS)]
    base = _base_amounts(rng)[field]
    ref_month = date(2026, 1 + ((group_idx + case_idx) % 6), 1)
    request_period = _period(ref_month)
    request = {"period": request_period, "requested_at": (ref_month + timedelta(days=31)).isoformat(),
               "purpose": "current_underwriting_evidence", "required_fields": [field]}
    records, gold, truth = [], [], []

    def add(value, period, source, **kwargs):
        doc = _make_record(rng, group_idx, case_idx, len(records), field, value, period, source, **kwargs)
        records.append(doc)
        return doc

    material_idx = None
    critical_idx = None
    if scenario == "D1_PERIOD_VARIATION":
        previous = _period(ref_month - timedelta(days=31))
        add(int(base * .86), request_period, "payroll", basis="NET")
        add(int(base * 1.12), previous, "statement", basis="NET", asserted_current=False, age=70)
    elif scenario == "D2_GROSS_NET":
        gross = int(base * 1.25)
        add(gross, request_period, "payroll", basis="GROSS")
        add(int(gross * .80), request_period, "statement", basis="NET")
    elif scenario == "D3_CORRECTION_LINEAGE":
        original = add(base, request_period, "statement", direction="OUTFLOW", correction="SUPERSEDED")
        corrected = add(int(base * .96), request_period, "merchant", direction="OUTFLOW",
                        correction="CORRECTED", correction_of=original["record_id"])
        original["correction_of"] = corrected["record_id"]
    elif scenario == "D4_HISTORICAL_VALIDITY":
        old_period = _period(ref_month - timedelta(days=365))
        if case_idx % 2 == 0:
            request_period = old_period
            request["period"] = old_period
            request["requested_at"] = (ref_month + timedelta(days=31)).isoformat()
            add(base, old_period, "statement", asserted_current=False, age=270)
            add(int(base * 1.03), old_period, "payroll", asserted_current=False, age=250)
        else:
            add(base, old_period, "statement", asserted_current=True, age=270)
            faulty = add(int(base * .50), old_period, "payroll", asserted_current=True, age=250)
            material_idx = len(records) - 1
            critical_idx = material_idx
    elif scenario == "D5_COMPARABLE_CONFLICT":
        valid = add(base, request_period, "statement", basis="NET")
        if rng.random() < .35:
            bad_value = int(base + 2.5 * FIELD_THRESHOLD[field])
            add(bad_value, request_period, "payroll", basis="NET")
            material_idx = len(records) - 1
            critical_idx = material_idx
        else:
            add(int(base + rng.uniform(-.6, .6) * FIELD_THRESHOLD[field]), request_period, "payroll", basis="NET")
    elif scenario == "D6_ACCOUNT_DIRECTION":
        add(base, request_period, "statement", direction="OUTFLOW")
        add(int(base * 1.8), request_period, "merchant", direction="INFLOW",
            account=f"D-other-account-{group_idx:04d}")
    else:
        raise ValueError(scenario)

    # Add a neutral third record in a different field to prevent a fixed 2-row cue.
    side_field = next(f for f in FIELDS if f != field)
    side_value = _base_amounts(rng)[side_field]
    side_period = request_period
    side = _make_record(rng, group_idx, case_idx, len(records), side_field, side_value, side_period,
                        SOURCE_TYPES[(group_idx + case_idx) % len(SOURCE_TYPES)], basis="NET",
                        direction="OUTFLOW" if side_field == "debt" else "INFLOW")
    records.append(side)

    for i, record in enumerate(records):
        material = int(i == material_idx)
        critical = int(i == critical_idx)
        gold.append({"record_id": record["record_id"], "material_defect": material, "critical_defect": critical})
        expected = record["normalized_value"]
        if material and expected is not None:
            expected = int(base)
        truth.append({"record_id": record["record_id"], "expected_normalized_value": expected,
                      "generation_event": "synthetic_corruption" if material else "valid_observation",
                      "material_defect": material, "critical_defect": critical})
    return {
        "case_id": f"D-case-g{group_idx:04d}-{case_idx}", "customer_group": f"D-group-{group_idx:04d}",
        "scenario": scenario, "request": request, "records": records,
    }, gold, truth


def generate_development(seed: int = DEV_SEED, groups_per_scenario: int = 100):
    rng = np.random.default_rng(seed)
    cases, labels, truths = [], [], []
    for scenario_idx, scenario in enumerate(SCENARIOS):
        for group_in_scenario in range(groups_per_scenario):
            global_group = scenario_idx * groups_per_scenario + group_in_scenario
            for case_idx in range(2):
                case, gold, truth = _make_case(rng, scenario, global_group, case_idx)
                cases.append(case)
                labels.append({"case_id": case["case_id"], "records": gold})
                truths.append({"case_id": case["case_id"], "customer_group": case["customer_group"],
                               "scenario": scenario, "records": truth})
    return cases, labels, truths


def freeze_development(out: Path = OUT):
    cases, labels, truths = generate_development()
    out.mkdir(parents=True, exist_ok=True)
    payloads = {"observed.json": cases, "gold_labels.json": labels, "canonical_truth.json": truths}
    for name, payload in payloads.items():
        path = out / name
        encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if path.exists() and path.read_text(encoding="utf-8-sig") != encoded:
            raise ValueError(f"Development data already frozen and differs: {name}")
        if not path.exists():
            path.write_text(encoded, encoding="utf-8")
    groups = sorted({case["customer_group"] for case in cases})
    splits = {"train": [], "validation": [], "calibration": [], "locked_test": []}
    rng = np.random.default_rng(2026110804)
    for scenario in SCENARIOS:
        scenario_groups = [group for group in groups if any(case["customer_group"] == group and case["scenario"] == scenario for case in cases)]
        rng.shuffle(scenario_groups)
        n = len(scenario_groups)
        n_train, n_val, n_cal = int(.60*n), int(.15*n), int(.15*n)
        parts = (scenario_groups[:n_train], scenario_groups[n_train:n_train+n_val],
                 scenario_groups[n_train+n_val:n_train+n_val+n_cal], scenario_groups[n_train+n_val+n_cal:])
        for key, part in zip(splits, parts, strict=True):
            splits[key].extend(case["case_id"] for case in cases if case["customer_group"] in set(part))
    for partition, case_ids in splits.items():
        write_json(out / f"split_{partition}.json", {"case_ids": sorted(case_ids)})
    file_hashes = {name: sha(out / name) for name in [*payloads, *(f"split_{k}.json" for k in splits)]}
    manifest = {
        "dataset_id": "semantic-evidence-development-d1.1", "generator_id": "semantic-ledger-dev-v1.1",
        "generator_seed": DEV_SEED, "split_seed": 2026110804,
        "cases": len(cases), "groups": len(groups), "documents": sum(len(case["records"]) for case in cases),
        "scenario_counts": {scenario: {"cases": sum(case["scenario"] == scenario for case in cases),
                                        "groups": groups_per, "documents": sum(len(case["records"]) for case in cases if case["scenario"] == scenario)}
                            for scenario, groups_per in ((s, 100) for s in SCENARIOS)},
        "split_counts": {key: {"cases": len(ids), "groups": len({case["customer_group"] for case in cases if case["case_id"] in set(ids)})}
                         for key, ids in splits.items()},
        "file_sha256": file_hashes, "labels_are_programmatic_synthetic_gold": True,
        "canonical_truth_used_as_feature": False,
    }
    write_json(out / "dataset_manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(freeze_development(), indent=2))
