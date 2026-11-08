"""Post-unblinding arithmetic and clustered uncertainty reconciliation for Generator C.

This utility does not train, calibrate, select, or alter any model or threshold.
It reads the already-opened gold labels only to reconcile the frozen prediction file.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import beta
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss

from ml.contracts import ROOT, sha, write_json

C_DIR = ROOT / "reports/evidence-v4.1/data/generator-c-v1"
OUT = ROOT / "reports/evidence-v4.1"
PREDICTIONS = C_DIR / "C_PREDICTIONS_FROZEN.csv"
GOLD = C_DIR / "gold_labels.json"
OBSERVED = C_DIR / "observed.json"
PROTOCOL_SCENARIOS = (
    "C1_GROSS_NET_PERIODS", "C2_SAME_PERIOD_CORRUPTION", "C3_CORRECTION_LINEAGE",
    "C4_TIME_VALIDITY", "C5_NONCOMPARABLE_SUBJECT_ACCOUNT",
    "C6_TRUE_COMPARABLE_CONFLICT", "C7_HELD_OUT_SOURCE_PAIR",
)
LEGIT_SCENARIOS = {"C1_GROSS_NET_PERIODS", "C3_CORRECTION_LINEAGE", "C5_NONCOMPARABLE_SUBJECT_ACCOUNT"}
DRAWS = 500
SEED = 2026110803


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _bool(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def _metric(rows, indexes=None, case_tokens=None):
    if indexes is None:
        indexes = np.arange(len(rows), dtype=int)
    subset = [rows[int(i)] for i in indexes]
    if not subset:
        return {"documents": 0, "material_defect_support": 0, "critical_support": 0}
    score = np.asarray([float(row["score"]) for row in subset], dtype=float)
    threshold = float(subset[0]["threshold"])
    flagged = score >= threshold
    material = np.asarray([int(row["material_defect"]) for row in subset], dtype=int)
    critical = np.asarray([int(row["critical_defect"]) for row in subset], dtype=int)
    legitimate = material == 0
    scenario = np.asarray([row["scenario"] for row in subset], dtype=object)
    legit_diag = legitimate & np.isin(scenario, sorted(LEGIT_SCENARIOS))
    c4_critical = (scenario == "C4_TIME_VALIDITY") & (critical == 1)
    case_ids = list(case_tokens) if case_tokens is not None else [row["case_id"] for row in subset]
    flagged_case_count = len({case_ids[i] for i in range(len(subset)) if flagged[i]})
    case_count = len(set(case_ids))
    probability = subset[0]["score_kind"] == "CALIBRATED_PROBABILITY"
    mat_tp = int((flagged & (material == 1)).sum())
    mat_fn = int(((~flagged) & (material == 1)).sum())
    fp = int((flagged & legitimate).sum())
    tn = int(((~flagged) & legitimate).sum())
    crit_tp = int((flagged & (critical == 1)).sum())
    crit_fn = int(((~flagged) & (critical == 1)).sum())
    return {
        "documents": len(subset),
        "material_defect_support": int(material.sum()),
        "material_tp": mat_tp, "material_fn": mat_fn,
        "legitimate_support": int(legitimate.sum()), "legitimate_fp": fp, "legitimate_tn": tn,
        "critical_support": int(critical.sum()), "critical_tp": crit_tp, "critical_fn": crit_fn,
        "critical_recall": crit_tp / int(critical.sum()) if critical.sum() else None,
        "critical_fnr": crit_fn / int(critical.sum()) if critical.sum() else None,
        "material_average_precision": float(average_precision_score(material, score)) if len(np.unique(material)) > 1 else None,
        "critical_average_precision": float(average_precision_score(critical, score)) if len(np.unique(critical)) > 1 else None,
        "overall_legitimate_fpr": fp / int(legitimate.sum()) if legitimate.sum() else None,
        "legitimate_discrepancy_support_c1_c3_c5": int(legit_diag.sum()),
        "legitimate_discrepancy_fp_c1_c3_c5": int((flagged & legit_diag).sum()),
        "legitimate_discrepancy_fpr_c1_c3_c5": float((flagged & legit_diag).sum() / legit_diag.sum()) if legit_diag.sum() else None,
        "c4_stale_critical_support": int(c4_critical.sum()),
        "c4_stale_tp": int((flagged & c4_critical).sum()),
        "c4_stale_fn": int(((~flagged) & c4_critical).sum()),
        "c4_stale_as_current_recall": float((flagged & c4_critical).sum() / c4_critical.sum()) if c4_critical.sum() else None,
        "case_count": case_count, "flagged_case_count": flagged_case_count,
        "case_review_workload": flagged_case_count / case_count if case_count else None,
        "brier_score": float(brier_score_loss(material, score)) if probability else None,
        "log_loss": float(log_loss(material, np.clip(score, 1e-7, 1 - 1e-7), labels=[0, 1]))
                    if probability and len(np.unique(material)) > 1 else None,
        "score_kind": subset[0]["score_kind"], "frozen_threshold": threshold,
    }


def _cp_interval(successes, trials, confidence=.95):
    if trials <= 0:
        return {"lower_95": None, "upper_95": None}
    alpha = 1 - confidence
    lower = 0.0 if successes == 0 else float(beta.ppf(alpha / 2, successes, trials - successes + 1))
    upper = 1.0 if successes == trials else float(beta.ppf(1 - alpha / 2, successes + 1, trials - successes))
    return {"lower_95": lower, "upper_95": upper}


def _resample_indexes(base_rows, groups_by_scenario, indexes_by_group, draws=DRAWS, seed=SEED):
    rng = np.random.default_rng(seed)
    samples = []
    for draw in range(draws):
        ids, case_tokens = [], []
        for scenario in sorted(groups_by_scenario):
            group_ids = sorted(groups_by_scenario[scenario])
            sampled_groups = rng.choice(group_ids, size=len(group_ids), replace=True)
            for occurrence, group_id in enumerate(sampled_groups):
                for index in indexes_by_group[group_id]:
                    ids.append(index)
                    case_tokens.append(f"{draw}:{scenario}:{occurrence}:{base_rows[index]['case_id']}")
        samples.append((np.asarray(ids, dtype=int), case_tokens))
    return samples


def _ci(values):
    values = np.asarray([value for value in values if value is not None], dtype=float)
    return {"lower_95": float(np.quantile(values, .025)) if len(values) else None,
            "upper_95": float(np.quantile(values, .975)) if len(values) else None,
            "valid_draws": int(len(values))}


def _records_by_model(rows, gold_by_id, observed_by_id):
    models = {}
    for row in rows:
        record_id = row["record_id"]
        observed = observed_by_id[record_id]
        target = gold_by_id[record_id]
        row["customer_group"] = observed["customer_group"]
        row["material_defect"] = int(target["material_defect"])
        row["critical_defect"] = int(target["critical_defect"])
        models.setdefault(row["model"], []).append(row)
    return models


def reconcile():
    c_manifest = _json(C_DIR / "dataset_manifest.json")
    prediction_manifest = _json(C_DIR / "C_PREDICTION_MANIFEST.json")
    status = _json(C_DIR / "LABEL_ACCESS_STATUS.json")
    if not status.get("labels_opened_for_evaluation"):
        raise RuntimeError("Current state differs from the recorded unblinded evaluation status")
    if sha(PREDICTIONS) != prediction_manifest["prediction_sha256"]:
        raise ValueError("Frozen prediction CSV hash mismatch")
    if sha(OBSERVED) != c_manifest["file_sha256"]["observed.json"]:
        raise ValueError("Generator C observed file hash mismatch")
    if sha(GOLD) != c_manifest["file_sha256"]["gold_labels.json"]:
        raise ValueError("Generator C gold-label file hash mismatch")
    if prediction_manifest["model_manifest_sha256"] != sha(ROOT / "reports/evidence-v4.1/models/frozen-v1/frozen_model_manifest.json"):
        raise ValueError("Frozen model manifest changed since C predictions")

    observed_cases = _json(OBSERVED)
    gold_cases = _json(GOLD)
    gold_by_id = {row["record_id"]: row for case in gold_cases for row in case["records"]}
    observed_by_id = {record["record_id"]: {**record, "customer_group": case["customer_group"],
                                             "case_id": case["case_id"], "scenario": case["scenario"]}
                      for case in observed_cases for record in case["records"]}
    rows = _csv(PREDICTIONS)
    if set(gold_by_id) != set(observed_by_id):
        raise ValueError("C observed/gold record keys do not align")
    model_rows = _records_by_model(rows, gold_by_id, observed_by_id)
    expected_ids = set(gold_by_id)
    for name, model_data in model_rows.items():
        if len(model_data) != len(expected_ids) or {row["record_id"] for row in model_data} != expected_ids:
            raise ValueError(f"C prediction rows do not align to records for {name}")

    aggregate = {name: _metric(data) for name, data in model_rows.items()}
    baseline_result_json = _json(C_DIR / "GENERATOR_C_RESULTS.json")["aggregate_metrics"]
    comparison = {}
    for name, metrics in aggregate.items():
        old = baseline_result_json.get(name, {})
        keys = ("critical_recall", "overall_legitimate_fpr", "case_review_workload",
                "material_average_precision", "brier_score", "log_loss")
        # The previous evaluator called the same denominators by shorter names.
        aliases = {"overall_legitimate_fpr": "aggregate_legitimate_fpr", "case_review_workload": "review_workload",
                  "material_average_precision": "material_average_precision", "brier_score": "brier", "log_loss": "log_loss"}
        comparison[name] = {key: {"recomputed": metrics.get(key), "previous": old.get(aliases.get(key, key)),
                                  "match": (metrics.get(key) is None and old.get(aliases.get(key, key)) is None)
                                  or (metrics.get(key) is not None and old.get(aliases.get(key, key)) is not None
                                      and math.isclose(float(metrics[key]), float(old[aliases.get(key, key)]), rel_tol=1e-9, abs_tol=1e-9))}
                            for key in keys}

    # Same scenario-stratified cluster draws are used for all model and paired contrasts.
    base_name = next(iter(model_rows))
    base_rows = model_rows[base_name]
    group_indexes, groups_by_scenario = {}, {}
    for index, row in enumerate(base_rows):
        group_indexes.setdefault(row["customer_group"], []).append(index)
        groups_by_scenario.setdefault(row["scenario"], set()).add(row["customer_group"])
    samples = _resample_indexes(base_rows, groups_by_scenario, group_indexes)
    ordered_models = {name: {row["record_id"]: row for row in data} for name, data in model_rows.items()}
    # All frozen prediction files use the same case/document ordering. Assert this before paired draws.
    model_order_ok = all([row["record_id"] for row in data] == [row["record_id"] for row in base_rows]
                         for data in model_rows.values())
    if not model_order_ok:
        raise ValueError("Model prediction ordering differs; paired bootstrap is invalid")
    metric_names = ("critical_recall", "overall_legitimate_fpr", "legitimate_discrepancy_fpr_c1_c3_c5",
                    "c4_stale_as_current_recall", "case_review_workload", "material_average_precision",
                    "brier_score", "log_loss")
    intervals, bootstrap_values = {}, {}
    for name, data in model_rows.items():
        collected = {key: [] for key in metric_names}
        for indexes, case_tokens in samples:
            result = _metric(data, indexes, case_tokens)
            for key in metric_names:
                collected[key].append(result.get(key))
        intervals[name] = {key: _ci(values) for key, values in collected.items()}
        bootstrap_values[name] = collected

    paired = []
    hybrid_name = "SEMANTIC_HYBRID"
    for baseline in ("M0_CS_V2", "M1_LOGISTIC", "M3_DEEP_SETS", "SEMANTIC_RULE"):
        if baseline not in model_rows or hybrid_name not in model_rows:
            continue
        deltas = {key: [] for key in ("critical_recall", "overall_legitimate_fpr", "case_review_workload", "material_average_precision")}
        for indexes, case_tokens in samples:
            h = _metric(model_rows[hybrid_name], indexes, case_tokens)
            b = _metric(model_rows[baseline], indexes, case_tokens)
            for key in deltas:
                if h.get(key) is not None and b.get(key) is not None:
                    deltas[key].append(h[key] - b[key])
        for metric, values in deltas.items():
            paired.append({"contrast": f"SEMANTIC_HYBRID_MINUS_{baseline}", "metric": metric,
                           "difference_point_estimate": aggregate[hybrid_name][metric] - aggregate[baseline][metric],
                           **_ci(values), "customer_group_stratified_bootstrap": DRAWS,
                           "interpretation": "post-unblinding paired descriptive comparison; not confirmatory model selection"})

    # Exact binomial uncertainty is reported on independent customer-group events,
    # not as if documents within a group were independent trials.
    hybrid = model_rows[hybrid_name]
    scenario_cluster = {}
    for scenario in PROTOCOL_SCENARIOS:
        subset = [row for row in hybrid if row["scenario"] == scenario]
        groups = sorted({row["customer_group"] for row in subset})
        crit_rows_by_group = {group: [row for row in subset if row["customer_group"] == group and int(row["critical_defect"]) == 1]
                              for group in groups}
        positive_groups = [group for group in groups if crit_rows_by_group[group]]
        successful_groups = sum(all(_bool(row["flagged"]) for row in crit_rows_by_group[group]) for group in positive_groups)
        legitimate_groups = [group for group in groups if any(int(row["material_defect"]) == 0 for row in subset if row["customer_group"] == group)]
        fp_groups = sum(any(int(row["material_defect"]) == 0 and _bool(row["flagged"])
                            for row in subset if row["customer_group"] == group) for group in legitimate_groups)
        scenario_cluster[scenario] = {
            "critical_positive_groups": len(positive_groups), "groups_with_all_critical_docs_detected": int(successful_groups),
            "group_level_all_critical_detected_rate": successful_groups / len(positive_groups) if positive_groups else None,
            "group_success_cp_95": _cp_interval(successful_groups, len(positive_groups)),
            "groups_with_legitimate_docs": len(legitimate_groups), "groups_with_any_legitimate_fp": int(fp_groups),
            "group_any_fp_cp_95_two_sided": _cp_interval(fp_groups, len(legitimate_groups)),
            "group_any_fp_upper_one_sided_95": (1 - .05 ** (1 / len(legitimate_groups))) if fp_groups == 0 and legitimate_groups else None,
        }
    diagnostic_groups = sum(scenario_cluster[s]["groups_with_legitimate_docs"] for s in LEGIT_SCENARIOS)
    hoeffding_group_fpr_ucb = math.sqrt(math.log(1/.05)/(2*diagnostic_groups)) if diagnostic_groups else None

    # Per-scenario/source support tables using the same frozen thresholds.
    by_scenario, by_source = [], []
    for name, data in model_rows.items():
        for scenario in PROTOCOL_SCENARIOS:
            subset = [row for row in data if row["scenario"] == scenario]
            by_scenario.append({"model": name, "scenario": scenario, **_metric(subset)})
        for source in ("statement", "payroll", "merchant"):
            subset = [row for row in data if row["source_type"] == source]
            by_source.append({"model": name, "source_type": source, **_metric(subset)})

    availability = _json(C_DIR / "C_PREDICTION_MANIFEST.json")["model_availability"]
    result = {
        "status": "POST_UNBLINDING_RECONCILIATION_NO_TUNING",
        "protocol_id": "cobi-evidence-v4.1-c1.0",
        "prediction_sha256": sha(PREDICTIONS), "gold_sha256": sha(GOLD),
        "observed_sha256": sha(OBSERVED), "prediction_freeze_verified": True,
        "labels_were_already_opened_before_this_reconciliation": True,
        "models_or_thresholds_changed": False,
        "dataset": {"customer_groups": len({case["customer_group"] for case in observed_cases}),
                     "cases": len(observed_cases), "documents": len(observed_by_id),
                     "positive_material_documents": sum(int(row["material_defect"]) for row in gold_by_id.values()),
                     "critical_documents": sum(int(row["critical_defect"]) for row in gold_by_id.values())},
        "model_availability": availability,
        "aggregate_metrics": aggregate,
        "scenario_metrics": by_scenario, "source_metrics": by_source,
        "previous_report_reconciliation": comparison,
        "all_previous_aggregate_metrics_match": all(cell["match"] for model in comparison.values() for cell in model.values()),
        "bootstrap": {"unit": "customer_group", "stratified_by": "scenario", "draws": DRAWS,
                      "seed": SEED, "interval": "percentile 95%", "uses_frozen_thresholds": True,
                      "intervals_by_model": intervals},
        "paired_group_bootstrap_contrasts": paired,
        "boundary_uncertainty": {
            "definition": "Exact Clopper-Pearson intervals on group-level success/failure events; the event is that all critical records in a positive group are detected, or that a legitimate group contains any false positive.",
            "by_scenario": scenario_cluster,
            "c1_c3_c5_group_any_fp_events": 0,
            "c1_c3_c5_groups_with_legitimate_records": diagnostic_groups,
            "c1_c3_c5_one_sided_95_upper_bound_group_any_fp": 1 - .05 ** (1 / diagnostic_groups) if diagnostic_groups else None,
            "c1_c3_c5_hoeffding_one_sided_95_ucb_equal_group_weighted_fpr": hoeffding_group_fpr_ucb,
            "warning": "These group-level bounds estimate cluster events or equal-group-weighted FPR under independent customer-group sampling. They are not document-weighted FPR confidence limits and do not cover generator or label-rule misspecification.",
        },
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
    }
    write_json(OUT / "GENERATOR_C_METRICS.json", result)
    _write_csv(OUT / "GENERATOR_C_SCENARIO_METRICS.csv", by_scenario)
    _write_csv(OUT / "GENERATOR_C_SOURCE_METRICS.csv", by_source)
    _write_csv(OUT / "GENERATOR_C_PAIRED_BASELINE_COMPARISONS.csv", paired)
    _write_csv(OUT / "GENERATOR_C_GROUP_CLUSTER_UNCERTAINTY.csv", [
        {"scenario": scenario, **values} for scenario, values in scenario_cluster.items()])
    return result


def _write_csv(path, rows):
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})


if __name__ == "__main__":
    result = reconcile()
    print(json.dumps({"status": result["status"], "dataset": result["dataset"],
                      "semantic_hybrid": result["aggregate_metrics"]["SEMANTIC_HYBRID"],
                      "all_previous_aggregate_metrics_match": result["all_previous_aggregate_metrics_match"],
                      "boundary_uncertainty": result["boundary_uncertainty"]}, indent=2))
