"""Independent locked challenge generator; has no import path to B or D generators."""
from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path

import numpy as np

from ml.contracts import ROOT, sha, write_json

OUT = ROOT / "reports/evidence-v4.1/data/generator-c-v1"
SEED = 2026110802
SCENARIOS = (
    "C1_GROSS_NET_PERIODS", "C2_SAME_PERIOD_CORRUPTION", "C3_CORRECTION_LINEAGE",
    "C4_TIME_VALIDITY", "C5_NONCOMPARABLE_SUBJECT_ACCOUNT",
    "C6_TRUE_COMPARABLE_CONFLICT", "C7_HELD_OUT_SOURCE_PAIR",
)
SOURCES = ("statement", "payroll", "merchant")
FIELDS = ("income", "debt", "purchase")
MEANING = {"income": "salary", "debt": "recurring_debt", "purchase": "purchase_amount"}
THRESHOLD = {"income": 500_000.0, "debt": 250_000.0, "purchase": 500_000.0}


def _period(start: date, days: int = 27):
    return {"start": start.isoformat(), "end": (start + timedelta(days=days)).isoformat()}


def _record(rng, group, case, ordinal, field, amount, period, source, *, basis="NET",
            direction="INFLOW", subject=None, account=None, correction="NONE", correction_of=None,
            current=True, age=None, value_unit="VND", verified="VERIFIED", missingness="NONE"):
    amount = None if missingness == "REQUIRED_VALUE_MISSING" else int(amount)
    record_id = f"C-DOC-{group:04d}-{case}-{ordinal:02d}"
    observed_at = date(2026, 9, 1) + timedelta(days=int(rng.integers(0, 60)))
    age = int(age if age is not None else rng.integers(2, 75))
    return {
        "record_id": record_id,
        "subject_ref": subject or f"ORG-{group:04d}",
        "account_ref": account or f"ACCT-{group:04d}-{field}",
        "field_type": field,
        "financial_meaning": MEANING[field],
        "effective_period": period,
        "source_type": source,
        "provenance": {"document_ref": f"C-ARCHIVE-{group:04d}-{case}-{ordinal:02d}",
                       "page": int(rng.integers(1, 9)), "extraction_version": "c-ledger-parser-1.0"},
        "original_value": amount,
        "original_unit": value_unit,
        "normalized_value": amount,
        "normalized_unit": "VND" if amount is not None else "UNKNOWN",
        "gross_net_basis": basis,
        "transaction_direction": direction,
        "correction_status": correction,
        "correction_of": correction_of,
        "verification_status": verified,
        "missingness": missingness,
        "uncertainty": round(float(rng.uniform(.005, .22)), 5),
        "asserted_as_current": bool(current),
        "observed_at": observed_at.isoformat(),
        "age_days": age,
        "ocr_quality": round(float(rng.uniform(.55, .995)), 5),
        "text": f"{source} {MEANING[field]} {basis.lower()} value {amount if amount is not None else 'missing'} effective {period['start']} through {period['end']}",
    }


def _base_value(rng, field):
    ranges = {"income": (8_000_000, 32_000_000), "debt": (400_000, 9_000_000),
              "purchase": (1_000_000, 26_000_000)}
    low, high = ranges[field]
    return int(rng.integers(low, high + 1))


def _scenario_pair(rng, scenario, group, case):
    field = FIELDS[int(rng.integers(0, len(FIELDS)))]
    base = _base_value(rng, field)
    month = int(rng.integers(1, 11))
    requested = date(2026, month, 1)
    current_period = _period(requested)
    request = {"period": current_period, "requested_at": (requested + timedelta(days=31)).isoformat(),
               "purpose": "current_financial_review", "required_fields": [field]}
    records, defect_index, critical_index = [], None, None

    if scenario == "C1_GROSS_NET_PERIODS":
        if (group + case) % 2:
            prior = _period(requested - timedelta(days=90))
            records.append(_record(rng, group, case, 0, field, int(base * .81), current_period, "payroll", basis="NET"))
            records.append(_record(rng, group, case, 1, field, int(base * 1.34), prior, "statement", basis="NET", current=False, age=118))
        else:
            gross = int(base * 1.32)
            records.append(_record(rng, group, case, 0, field, gross, current_period, "payroll", basis="GROSS"))
            records.append(_record(rng, group, case, 1, field, int(gross * .76), current_period, "statement", basis="NET"))
    elif scenario == "C2_SAME_PERIOD_CORRUPTION":
        left_source, right_source = ("statement", "payroll") if group % 2 else ("merchant", "statement")
        records.append(_record(rng, group, case, 0, field, base, current_period, left_source))
        if (group + case) % 3 == 0:
            # A valid same-period agreement is included as a hard negative.
            other = int(base + rng.integers(-1, 2) * THRESHOLD[field] * .15)
        else:
            other = int(base + THRESHOLD[field] * rng.uniform(2.4, 4.2))
            defect_index = critical_index = 1
        records.append(_record(rng, group, case, 1, field, other, current_period, right_source))
    elif scenario == "C3_CORRECTION_LINEAGE":
        old = _record(rng, group, case, 0, field, base, current_period, "statement",
                      correction="SUPERSEDED", direction="OUTFLOW")
        records.append(old)
        corrected = _record(rng, group, case, 1, field, int(base * .71), current_period, "merchant",
                            correction="CORRECTED", correction_of=old["record_id"], direction="OUTFLOW")
        old["correction_of"] = corrected["record_id"]
        records.append(corrected)
    elif scenario == "C4_TIME_VALIDITY":
        prior = _period(requested - timedelta(days=430))
        if case == 0:
            request["period"] = prior
            records.append(_record(rng, group, case, 0, field, base, prior, "statement", current=False, age=438))
            records.append(_record(rng, group, case, 1, field, int(base * 1.01), prior, "payroll", current=False, age=432))
        else:
            records.append(_record(rng, group, case, 0, field, base, current_period, "statement", current=True, age=18))
            records.append(_record(rng, group, case, 1, field, int(base * .48), prior, "payroll", current=True, age=432))
            defect_index = critical_index = 1
    elif scenario == "C5_NONCOMPARABLE_SUBJECT_ACCOUNT":
        records.append(_record(rng, group, case, 0, field, base, current_period, "statement"))
        records.append(_record(rng, group, case, 1, field, int(base * 1.9), current_period, "merchant",
                               subject=f"OTHER-ORG-{group:04d}", account=f"OTHER-ACCT-{group:04d}-{field}"))
    elif scenario == "C6_TRUE_COMPARABLE_CONFLICT":
        source_pair = (("statement", "merchant") if group % 2 else ("payroll", "statement"))
        records.append(_record(rng, group, case, 0, field, base, current_period, source_pair[0]))
        if (group + case) % 2:
            other = int(base + rng.uniform(-.3, .3) * THRESHOLD[field])
        else:
            other = int(base + THRESHOLD[field] * rng.uniform(2.1, 3.8))
            defect_index = critical_index = 1
        records.append(_record(rng, group, case, 1, field, other, current_period, source_pair[1]))
    elif scenario == "C7_HELD_OUT_SOURCE_PAIR":
        # Payroll+merchant never co-occur as a source pair in development D.
        records.append(_record(rng, group, case, 0, field, base, current_period, "payroll"))
        if group % 2 == 0:
            other = int(base + rng.uniform(-.2, .2) * THRESHOLD[field])
        else:
            other = int(base + THRESHOLD[field] * rng.uniform(2.2, 3.4))
            defect_index = critical_index = 1
        records.append(_record(rng, group, case, 1, field, other, current_period, "merchant"))
    else:
        raise ValueError(f"Unknown scenario {scenario}")

    # Add up to four irrelevant documents with different field semantics. These are
    # observable evidence only and carry no defect, correction-event, or label marker.
    count = int(rng.integers(2, 7))
    while len(records) < count:
        unused = [name for name in FIELDS if name not in {r["field_type"] for r in records}]
        side_field = unused[0] if unused else FIELDS[len(records) % len(FIELDS)]
        direction = "OUTFLOW" if side_field == "debt" else "INFLOW"
        source = SOURCES[int(rng.integers(0, len(SOURCES)))]
        records.append(_record(rng, group, case, len(records), side_field, _base_value(rng, side_field),
                               current_period, source, direction=direction,
                               subject=f"NEUTRAL-ORG-{group:04d}-{case}-{len(records)}",
                               account=f"NEUTRAL-ACCT-{group:04d}-{case}-{len(records)}"))
    return request, records, defect_index, critical_index


def generate(seed: int = SEED, groups_per_scenario: int = 120):
    rng = np.random.default_rng(seed)
    observed, labels, truth = [], [], []
    for scenario_idx, scenario in enumerate(SCENARIOS):
        for local_group in range(groups_per_scenario):
            group = scenario_idx * groups_per_scenario + local_group
            for case_idx in range(2):
                request, records, defect_idx, critical_idx = _scenario_pair(rng, scenario, group, case_idx)
                case_id = f"C-{group:04d}-{case_idx}"
                observed.append({"case_id": case_id, "customer_group": f"C-GROUP-{group:04d}",
                                 "scenario": scenario, "request": request, "records": records})
                gold_rows, truth_rows = [], []
                for idx, record in enumerate(records):
                    defect = int(idx == defect_idx)
                    critical = int(idx == critical_idx)
                    gold_rows.append({"record_id": record["record_id"], "material_defect": defect,
                                      "critical_defect": critical})
                    truth_rows.append({"record_id": record["record_id"],
                                       "expected_normalized_value": int(record["normalized_value"] * .5) if defect else record["normalized_value"],
                                       "event_code": "C-INDEPENDENT-ALTERATION" if defect else "C-VALID-RECORD",
                                       "material_defect": defect, "critical_defect": critical})
                labels.append({"case_id": case_id, "records": gold_rows})
                truth.append({"case_id": case_id, "customer_group": f"C-GROUP-{group:04d}",
                              "scenario": scenario, "records": truth_rows})
    return observed, labels, truth


def freeze(out: Path = OUT):
    observed, labels, truth = generate()
    out.mkdir(parents=True, exist_ok=True)
    payloads = {"observed.json": observed, "gold_labels.json": labels, "canonical_truth.json": truth}
    for filename, payload in payloads.items():
        path = out / filename
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if path.exists() and path.read_text(encoding="utf-8-sig") != text:
            raise ValueError(f"Generator C artifact already exists and differs: {filename}")
        if not path.exists():
            path.write_text(text, encoding="utf-8")
    manifest = {
        "dataset_id": "cobi-evidence-generator-c-v1.0", "generator_id": "semantic-ledger-c-v1.0",
        "seed": SEED, "groups_per_scenario": 120, "cases_per_group": 2,
        "case_count": len(observed), "group_count": len({case["customer_group"] for case in observed}),
        "document_count": sum(len(case["records"]) for case in observed),
        "scenario_counts": {scenario: {"cases": sum(case["scenario"] == scenario for case in observed),
                                        "groups": 120,
                                        "documents": sum(len(case["records"]) for case in observed if case["scenario"] == scenario)}
                            for scenario in SCENARIOS},
        "source_types": list(SOURCES), "held_out_source_pair": ["payroll", "merchant"],
        "dev_pair_overlap_check": "The payroll+merchant source pair does not occur in D1.1 observed records.",
        "generator_source_sha256": sha(Path(__file__)),
        "protocol_sha256": sha(ROOT / "reports/evidence-v4.1/experiment_protocol_c.json"),
        "model_release_sha256": sha(ROOT / "reports/evidence-v4.1/models/frozen-v1/frozen_release.json"),
        "canonical_truth_used_as_feature": False, "event_code_used_as_feature": False,
        "labels_accessed_for_generation_or_prediction": False,
        "file_sha256": {filename: sha(out / filename) for filename in payloads},
    }
    write_json(out / "dataset_manifest.json", manifest)
    write_json(out / "LABEL_ACCESS_STATUS.json", {"labels_opened_for_evaluation": False,
               "predictions_frozen": False, "status": "GENERATION_COMPLETE_EVALUATION_NOT_STARTED"})
    return manifest


if __name__ == "__main__":
    print(json.dumps(freeze(), indent=2))
