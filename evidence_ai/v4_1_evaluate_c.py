"""One-time, post-freeze evaluation of Generator C; never tunes models or thresholds."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss

from evidence_ai.semantic_evidence import source_comparability
from evidence_ai.v4_1_training import _json
from ml.contracts import ROOT, sha, write_json

C_DIR = ROOT / "reports/evidence-v4.1/data/generator-c-v1"
PREDICTION_CSV = C_DIR / "C_PREDICTIONS_FROZEN.csv"
BOOTSTRAP_DRAWS = 500
BOOTSTRAP_SEED = 2026110803
LEGITIMATE_DIAGNOSTIC_SCENARIOS = {"C1_GROSS_NET_PERIODS", "C3_CORRECTION_LINEAGE", "C5_NONCOMPARABLE_SUBJECT_ACCOUNT"}


def _read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _float_or_none(value):
    return float(value) if value not in (None, "") else None


def _metric(rows, indexes=None, case_override=None):
    if indexes is None:
        indexes = np.arange(len(rows))
    if len(indexes) == 0:
        return {"documents": 0, "material_errors": 0, "critical_errors": 0}
    subset = [rows[int(i)] for i in indexes]
    y = np.asarray([int(row["material_defect"]) for row in subset], dtype=int)
    critical = np.asarray([int(row["critical_defect"]) for row in subset], dtype=int)
    scores = np.asarray([float(row["score"]) for row in subset], dtype=float)
    threshold = float(subset[0]["threshold"])
    flagged = scores >= threshold
    cases = [case_override[i] for i in range(len(subset))] if case_override is not None else [row["case_id"] for row in subset]
    flagged_cases = len({cases[i] for i in range(len(subset)) if flagged[i]})
    unique_cases = len(set(cases))
    legitimate = y == 0
    scenario = np.asarray([row["scenario"] for row in subset], dtype=object)
    discrepancy = legitimate & np.isin(scenario, list(LEGITIMATE_DIAGNOSTIC_SCENARIOS))
    stale = np.asarray([row["scenario"] == "C4_TIME_VALIDITY" for row in subset]) & (critical == 1)
    probability_scores = subset[0]["score_kind"] == "CALIBRATED_PROBABILITY"
    return {
        "documents": len(subset), "material_errors": int(y.sum()), "critical_errors": int(critical.sum()),
        "critical_false_negatives": int((~flagged & (critical == 1)).sum()),
        "critical_recall": float((flagged & (critical == 1)).sum() / critical.sum()) if critical.sum() else None,
        "critical_fnr": float((~flagged & (critical == 1)).sum() / critical.sum()) if critical.sum() else None,
        "material_average_precision": float(average_precision_score(y, scores)) if len(np.unique(y)) == 2 else None,
        "critical_average_precision": float(average_precision_score(critical, scores)) if len(np.unique(critical)) == 2 else None,
        "legitimate_discrepancy_fpr": float((flagged & discrepancy).sum() / discrepancy.sum()) if discrepancy.sum() else None,
        "legitimate_discrepancy_support": int(discrepancy.sum()),
        "aggregate_legitimate_fpr": float((flagged & legitimate).sum() / legitimate.sum()) if legitimate.sum() else None,
        "aggregate_legitimate_support": int(legitimate.sum()),
        "stale_as_current_recall": float((flagged & stale).sum() / stale.sum()) if stale.sum() else None,
        "stale_as_current_support": int(stale.sum()),
        "review_workload": float(flagged_cases / unique_cases) if unique_cases else None,
        "flagged_cases": flagged_cases, "case_count": unique_cases,
        "brier": float(brier_score_loss(y, scores)) if probability_scores else None,
        "log_loss": float(log_loss(y, np.clip(scores, 1e-7, 1-1e-7), labels=[0, 1]))
                    if probability_scores and len(np.unique(y)) == 2 else None,
        "score_kind": subset[0]["score_kind"], "frozen_threshold": threshold,
    }


def _stratified_group_bootstrap(rows, draws=BOOTSTRAP_DRAWS, seed=BOOTSTRAP_SEED):
    groups_by_scenario = {}
    indexes_by_group = {}
    for i, row in enumerate(rows):
        indexes_by_group.setdefault(row["customer_group"], []).append(i)
        groups_by_scenario.setdefault(row["scenario"], set()).add(row["customer_group"])
    rng = np.random.default_rng(seed)
    sampled_indexes = []
    sampled_cases = []
    for draw in range(draws):
        index_list, case_list = [], []
        for scenario in sorted(groups_by_scenario):
            groups = sorted(groups_by_scenario[scenario])
            sample = rng.choice(groups, size=len(groups), replace=True)
            for occurrence, group in enumerate(sample):
                for index in indexes_by_group[group]:
                    index_list.append(index)
                    case_list.append(f"{draw}:{scenario}:{occurrence}:{rows[index]['case_id']}")
        sampled_indexes.append(np.asarray(index_list, dtype=int))
        sampled_cases.append(case_list)
    return sampled_indexes, sampled_cases


def _bootstrap_intervals(model_rows, sampled_indexes, sampled_cases):
    names = ("material_average_precision", "critical_recall", "legitimate_discrepancy_fpr",
             "stale_as_current_recall", "review_workload", "brier", "log_loss")
    values = {name: [] for name in names}
    for indexes, case_ids in zip(sampled_indexes, sampled_cases, strict=True):
        metric = _metric(model_rows, indexes, case_ids)
        for name in names:
            if metric.get(name) is not None:
                values[name].append(metric[name])
    result = {}
    for name, draws in values.items():
        result[name] = {"lower_95": float(np.quantile(draws, .025)) if draws else None,
                        "upper_95": float(np.quantile(draws, .975)) if draws else None,
                        "valid_draws": len(draws), "requested_draws": len(sampled_indexes)}
    return result


def _posthoc_threshold_diagnostic(rows):
    """Exploratory threshold-transfer diagnostic; never written into frozen models."""
    y = np.asarray([int(row["material_defect"]) for row in rows], dtype=int)
    critical = np.asarray([int(row["critical_defect"]) for row in rows], dtype=int)
    scores = np.asarray([float(row["score"]) for row in rows], dtype=float)
    thresholds = np.unique(np.r_[0.0, scores, 1.0 + 1e-9])
    feasible = []
    for threshold in thresholds:
        flagged = scores >= threshold
        legit = y == 0
        fpr = float((flagged & legit).sum() / legit.sum()) if legit.sum() else 0.0
        recall = float((flagged & (critical == 1)).sum() / critical.sum()) if critical.sum() else None
        if fpr <= .20 and recall is not None:
            feasible.append((recall, threshold, fpr))
    metric = _metric(rows)
    if not feasible:
        return {"diagnostic_status": "NO_THRESHOLD_AT_FPR_20", "frozen_critical_recall": metric["critical_recall"],
                "best_critical_recall_at_legitimate_fpr_le_20": None,
                "posthoc_threshold": None, "threshold_transfer_gap": None,
                "use": "EXPLORATORY_ONLY_NOT_USED_FOR_TUNING_OR_ACCEPTANCE"}
    recall, threshold, fpr = max(feasible, key=lambda item: (item[0], -item[1]))
    return {"diagnostic_status": "EXPLORATORY_THRESHOLD_SWEEP",
            "frozen_critical_recall": metric["critical_recall"],
            "best_critical_recall_at_legitimate_fpr_le_20": recall,
            "posthoc_threshold": float(threshold), "posthoc_legitimate_fpr": fpr,
            "threshold_transfer_gap": float(recall - metric["critical_recall"]),
            "use": "EXPLORATORY_ONLY_NOT_USED_FOR_TUNING_OR_ACCEPTANCE"}


def evaluate():
    access_path = C_DIR / "LABEL_ACCESS_STATUS.json"
    access = _json(access_path)
    if access.get("labels_opened_for_evaluation"):
        raise RuntimeError("Generator C labels were already opened; one-time evaluation guard stopped this run")
    if access.get("predictions_frozen") is not True:
        raise RuntimeError("Cannot open Generator C labels before predictions are frozen")
    prediction_manifest = _json(C_DIR / "C_PREDICTION_MANIFEST.json")
    if prediction_manifest["status"] != "PREDICTIONS_FROZEN_LABELS_NOT_OPENED":
        raise RuntimeError("Generator C prediction freeze status is invalid")
    if sha(PREDICTION_CSV) != prediction_manifest["prediction_sha256"]:
        raise ValueError("Frozen Generator C predictions changed")
    if sha(C_DIR / "C_PREDICTION_MANIFEST.json") != access["prediction_manifest_sha256"]:
        raise ValueError("Prediction manifest changed after freeze")

    # First and only opening of the C gold-label file.
    observed = _json(C_DIR / "observed.json")
    gold = _json(C_DIR / "gold_labels.json")
    gold_by_case = {case["case_id"]: {row["record_id"]: row for row in case["records"]} for case in gold}
    observed_by_case = {case["case_id"]: case for case in observed}
    records = _read_csv(PREDICTION_CSV)
    for row in records:
        case = observed_by_case[row["case_id"]]
        target = gold_by_case[row["case_id"]][row["record_id"]]
        source = next(record for record in case["records"] if record["record_id"] == row["record_id"])
        row["customer_group"] = case["customer_group"]
        row["material_defect"] = int(target["material_defect"])
        row["critical_defect"] = int(target["critical_defect"])
        row["source_type"] = source["source_type"]

    model_names = sorted({row["model"] for row in records})
    by_model = {name: [row for row in records if row["model"] == name] for name in model_names}
    aggregate, scenario_rows, source_rows, ci_rows, threshold_rows = {}, [], [], [], []
    bootstrap_indexes, bootstrap_cases = _stratified_group_bootstrap(by_model[model_names[0]])
    # Data ordering is identical for each model; re-use cluster draws to compare models.
    for model_name, model_records in by_model.items():
        aggregate[model_name] = _metric(model_records)
        threshold_rows.append({"model": model_name, **_posthoc_threshold_diagnostic(model_records)})
        ci = _bootstrap_intervals(model_records, bootstrap_indexes, bootstrap_cases)
        ci_rows.extend({"model": model_name, "metric": metric, **interval,
                        "cluster_unit": "customer_group", "stratified_by": "scenario",
                        "bootstrap_seed": BOOTSTRAP_SEED}
                       for metric, interval in ci.items())
        for scenario in sorted({row["scenario"] for row in model_records}):
            subset = [row for row in model_records if row["scenario"] == scenario]
            scenario_rows.append({"model": model_name, "scenario": scenario, **_metric(subset)})
        for source in sorted({row["source_type"] for row in model_records}):
            subset = [row for row in model_records if row["source_type"] == source]
            source_rows.append({"model": model_name, "source_type": source, **_metric(subset)})

    available_baselines = [name for name in ("M0_CS_V2", "M1_LOGISTIC", "M2_XGBOOST", "M3_DEEP_SETS")
                           if name in aggregate]
    # XGBoost rows are omitted because that model could not be replayed.
    best_available_baseline = max((aggregate[name]["critical_recall"] for name in available_baselines
                                   if aggregate[name].get("critical_recall") is not None), default=None)
    hybrid = aggregate["SEMANTIC_HYBRID"]
    c4 = next(row for row in scenario_rows if row["model"] == "SEMANTIC_HYBRID" and row["scenario"] == "C4_TIME_VALIDITY")
    c7 = next(row for row in scenario_rows if row["model"] == "SEMANTIC_HYBRID" and row["scenario"] == "C7_HELD_OUT_SOURCE_PAIR")
    diag_fpr = hybrid["legitimate_discrepancy_fpr"]
    acceptance = {
        "semantic_hybrid_aggregate_critical_recall_min_0_90": hybrid["critical_recall"] is not None and hybrid["critical_recall"] >= .90,
        "C4_stale_recall_min_0_90": c4["stale_as_current_recall"] is not None and c4["stale_as_current_recall"] >= .90,
        "C1_C3_C5_legitimate_fpr_max_0_20": diag_fpr is not None and diag_fpr <= .20,
        "C7_critical_recall_min_0_85": c7["critical_recall"] is not None and c7["critical_recall"] >= .85,
        "aggregate_recall_degradation_vs_best_complete_frozen_baseline_max_0_02": "UNASSESSABLE_XGBOOST_REPLAY_BLOCKED",
        "best_available_baseline_critical_recall_partial": best_available_baseline,
        "full_registered_acceptance_status": "INCOMPLETE_XGBOOST_DEPENDENCY_BLOCKER",
    }

    # Semantic comparison/alert counts provide a model-independent failure audit.
    explanation = _json(C_DIR / "C_SEMANTIC_EXPLANATIONS.json")["records"]
    explanation_by_id = explanation
    failure_rows, gallery = [], []
    for model_name, model_records in by_model.items():
        for row in model_records:
            target_error = bool(row["material_defect"])
            critical = bool(row["critical_defect"])
            flagged = str(row["flagged"]).lower() in {"true", "1"}
            if not ((flagged and not target_error) or (critical and not flagged)):
                continue
            details = explanation_by_id.get(row["record_id"], {})
            comp_statuses = sorted({pair["status"] for pair in details.get("comparisons", [])})
            alert_reasons = sorted({alert["reason"] for alert in details.get("alerts", [])})
            if flagged and not target_error:
                if "COMPARABLE_VALUE_CONFLICT" in alert_reasons:
                    category = "PAIR_LEVEL_REVIEW_FLAGS_VALID_PEER"
                elif "STALE_AS_CURRENT" in alert_reasons:
                    category = "SEMANTIC_TIME_RULE_FLAGGED_UNLABELED_RECORD"
                elif "UNKNOWN" in comp_statuses:
                    category = "LEARNED_FLAG_WITH_UNKNOWN_COMPARABILITY"
                elif not alert_reasons:
                    category = "LEARNED_SCORE_FALSE_POSITIVE_OR_THRESHOLD_TRANSFER"
                else:
                    category = "OTHER_SEMANTIC_ALERT_FALSE_POSITIVE"
            else:
                category = "CRITICAL_FALSE_NEGATIVE_BELOW_FROZEN_THRESHOLD"
            failure_rows.append({"model": model_name, "scenario": row["scenario"], "case_id": row["case_id"],
                                 "customer_group": row["customer_group"], "record_id": row["record_id"],
                                 "source_type": row["source_type"], "score": row["score"],
                                 "threshold": row["threshold"], "flagged": flagged,
                                 "material_defect": row["material_defect"], "critical_defect": row["critical_defect"],
                                 "failure_category": category, "comparability_statuses": comp_statuses,
                                 "semantic_alert_reasons": alert_reasons})
            if model_name in {"SEMANTIC_HYBRID", "SEMANTIC_RULE", "SEMANTIC_LOGISTIC", "SEMANTIC_DEEP_SETS"}:
                gallery.append(failure_rows[-1])

    # Record registered hard-negative pair labels from C without exposing canonical truth.
    pair_counts = {"COMPARABLE": 0, "NOT_COMPARABLE": 0, "UNKNOWN": 0}
    pair_error_counts = {key: 0 for key in pair_counts}
    case_label_by_id = gold_by_case
    for case in observed:
        labels_by_id = case_label_by_id[case["case_id"]]
        for i, left in enumerate(case["records"]):
            for right in case["records"][i+1:]:
                result = source_comparability(left, right)
                pair_counts[result["status"]] += 1
                left_bad = bool(labels_by_id[left["record_id"]]["material_defect"])
                right_bad = bool(labels_by_id[right["record_id"]]["material_defect"])
                pair_error_counts[result["status"]] += int(left_bad or right_bad)

    result = {
        "protocol_id": "cobi-evidence-v4.1-c1.0", "generator_id": "semantic-ledger-c-v1.0",
        "status": "PARTIAL_INDEPENDENT_SYNTHETIC_EVALUATION",
        "labels_opened_after_prediction_freeze": True,
        "prediction_sha256_verified_before_label_access": prediction_manifest["prediction_sha256"],
        "generator_c_manifest_sha256": sha(C_DIR / "dataset_manifest.json"),
        "model_release_sha256": prediction_manifest["frozen_model_release_sha256"],
        "cases": len(observed), "groups": len({case["customer_group"] for case in observed}),
        "documents": len({row["record_id"] for row in records}),
        "model_availability": prediction_manifest["model_availability"],
        "aggregate_metrics": aggregate, "acceptance_assessment": acceptance,
        "by_scenario": scenario_rows, "by_source": source_rows,
        "grouped_confidence_interval_method": {"unit": "customer_group", "scenario_stratified": True,
                                                "draws": BOOTSTRAP_DRAWS, "seed": BOOTSTRAP_SEED,
                                                "interval": "percentile 95%"},
        "semantic_pair_status_counts": pair_counts, "pairs_with_any_material_defect_by_status": pair_error_counts,
        "posthoc_threshold_transfer_diagnostic": threshold_rows,
        "posthoc_threshold_diagnostics_are_exploratory": True,
        "failure_taxonomy": failure_rows,
        "critical_limitation": "Complete registered baseline comparison and acceptance are unavailable because frozen XGBoost replay could not run in this offline environment.",
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
        "routing_authorized": False, "approval_authorized": False,
        "checkout_consumes_research_outputs": False,
    }
    write_json(C_DIR / "GENERATOR_C_RESULTS.json", result)
    write_json(C_DIR / "ABLACTION_STUDY.json", {
        "registered_ablations": ["ABLATION_NO_TEMPORAL", "ABLATION_NO_COMPARABILITY", "ABLATION_NO_SOURCE_PROVENANCE"],
        "metrics_by_ablation": {name: aggregate[name] for name in ("ABLATION_NO_TEMPORAL", "ABLATION_NO_COMPARABILITY", "ABLATION_NO_SOURCE_PROVENANCE")},
        "full_model": aggregate["SEMANTIC_LOGISTIC"], "interpretation": "Ablations are fixed-threshold C evaluation; no retraining or threshold changes on C."})
    _write_csv(C_DIR / "SCENARIO_METRICS.csv", scenario_rows)
    _write_csv(C_DIR / "SOURCE_METRICS.csv", source_rows)
    _write_csv(C_DIR / "GROUPED_CONFIDENCE_INTERVALS.csv", ci_rows)
    _write_csv(C_DIR / "FAILURE_TAXONOMY.csv", failure_rows)
    gallery_sample, gallery_counts = [], {}
    for row in gallery:
        key = (row["model"], row["scenario"], row["failure_category"])
        if gallery_counts.get(key, 0) >= 2:
            continue
        gallery_sample.append(row)
        gallery_counts[key] = gallery_counts.get(key, 0) + 1
    _write_csv(C_DIR / "FAILURE_CASE_GALLERY.csv", gallery_sample)
    _write_csv(C_DIR / "THRESHOLD_TRANSFER_DIAGNOSTIC_EXPLORATORY.csv", threshold_rows)
    result_hashes = {path.name: sha(path) for path in sorted(C_DIR.iterdir()) if path.is_file()
                     and path.name not in {"gold_labels.json", "canonical_truth.json", "LABEL_ACCESS_STATUS.json"}}
    write_json(C_DIR / "C_EVALUATION_MANIFEST.json", {
        "status": "LABELS_OPENED_EVALUATION_COMPLETE", "prediction_sha256": prediction_manifest["prediction_sha256"],
        "gold_labels_sha256": sha(C_DIR / "gold_labels.json"), "evaluation_code_sha256": sha(Path(__file__)),
        "results_sha256": result_hashes, "metrics_computed_without_model_tuning": True,
        "generator_c_labels_used_for_threshold_change": False,
    })
    write_json(access_path, {"labels_opened_for_evaluation": True, "predictions_frozen": True,
               "prediction_sha256": prediction_manifest["prediction_sha256"],
               "evaluation_manifest_sha256": sha(C_DIR / "C_EVALUATION_MANIFEST.json"),
               "status": "EVALUATION_COMPLETE_LABELS_NOT_TO_BE_REOPENED"})
    return result


def _write_csv(path, rows):
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            cooked = {key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                      for key, value in row.items()}
            writer.writerow(cooked)


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps({"status": result["status"], "aggregate_metrics": result["aggregate_metrics"],
                      "acceptance_assessment": result["acceptance_assessment"]}, indent=2))
