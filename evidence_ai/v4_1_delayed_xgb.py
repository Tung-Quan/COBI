"""Delayed replay of the exact frozen V3 XGBoost baseline on inspected C.

This module never fits, calibrates, selects, or changes a model. Generator C labels
were already opened before this replay; every result is explicitly post-unblinding.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import xgboost as xgb
from scipy.special import expit, logit

from evidence_ai.evaluation import calibrate
from evidence_ai.features import NAMES, apply_scaler, build_arrays
from evidence_ai.replay import predict_frozen, read
from evidence_ai.train import RELEASE
from evidence_ai.v4_1_evaluate_c import (
    BOOTSTRAP_DRAWS, BOOTSTRAP_SEED, _bootstrap_intervals, _metric, _read_csv,
    _stratified_group_bootstrap,
)
from evidence_ai.v4_1_predict_c import _legacy_projection
from evidence_ai.v4_experiments import metrics as legacy_metrics
from evidence_ai.v4_generator import OUT as B_DIR
from ml.contracts import ROOT, sha, write_json

C_DIR = ROOT / "reports/evidence-v4.1/data/generator-c-v1"
OUT_CSV = C_DIR / "C_DELAYED_BASELINE_XGBOOST_PREDICTIONS.csv"
OUT_MANIFEST = C_DIR / "C_DELAYED_BASELINE_XGBOOST_MANIFEST.json"
OUT_RESULTS = C_DIR / "C_DELAYED_BASELINE_XGBOOST_RESULTS.json"
OUT_PAIRED = C_DIR / "C_DELAYED_BASELINE_XGBOOST_PAIRED.csv"
V3_DIR = RELEASE / "synthetic"
V4_PROTECTED = ROOT / "reports/evidence-v4/ARTIFACT_MANIFEST.json"
BASELINE_NAME = "M2_XGBOOST"
THRESHOLD = 0.9236921847680296


def _artifact_lock() -> tuple[dict, dict, dict]:
    lock = read(V3_DIR / "selection_lock.json")
    manifest = read(V3_DIR / "model/manifest.json")
    protected = read(V4_PROTECTED)
    protected_hashes = {row["path"]: row["sha256"] for row in protected["artifacts"]}
    if lock.get("xgb_depth") != 4:
        raise ValueError("Frozen V3 selection lock no longer selects the registered depth-4 XGBoost ensemble")
    if not np.isclose(float(lock["all_thresholds"][BASELINE_NAME]), THRESHOLD, rtol=0, atol=1e-15):
        raise ValueError("Frozen XGBoost threshold differs from the V4 registered operating point")
    if BASELINE_NAME not in lock.get("all_model_calibrators", {}):
        raise ValueError("Frozen XGBoost calibrator is missing")
    if manifest.get("seeds") != [13, 29, 43] or manifest.get("feature_names") != NAMES:
        raise ValueError("Frozen V3 model or feature contract differs from the recorded release")
    xgb_paths, xgb_hashes = [], {}
    for seed in manifest["seeds"]:
        rel = f"reports/evidence-v3/synthetic/xgb-d{lock['xgb_depth']}-s{seed}.json"
        path = V3_DIR / Path(rel).name
        digest = sha(path)
        if protected_hashes.get(rel) != digest:
            raise ValueError(f"Protected V4 baseline hash mismatch: {rel}")
        xgb_paths.append(path)
        xgb_hashes[rel] = digest
    if xgb.__version__ != "3.0.5":
        raise RuntimeError(f"Expected the recorded xgboost==3.0.5 runtime; found {xgb.__version__}")
    return lock, {"manifest": manifest, "paths": xgb_paths, "hashes": xgb_hashes}, protected


def _verify_generator_b_replay() -> dict:
    """Prove exact inference reproduction against V4's already-published B metrics."""
    cases = read(B_DIR / "observed.json")
    labels = read(B_DIR / "gold_labels.json")
    data, probabilities, _, lock = predict_frozen(cases, labels, V3_DIR)
    actual = legacy_metrics(data, probabilities[BASELINE_NAME], float(lock["all_thresholds"][BASELINE_NAME]))
    expected = read(ROOT / "reports/evidence-v4/E2_RESULTS.json")["models"][BASELINE_NAME]
    keys = ("cases", "documents", "material_errors", "critical_errors", "critical_false_negatives",
            "critical_recall", "critical_fnr", "average_precision", "brier", "log_loss",
            "document_flag_rate", "review_workload", "flagged_cases", "false_positive_documents")
    comparisons = {}
    for key in keys:
        left, right = actual.get(key), expected.get(key)
        matches = left == right if isinstance(left, int) and isinstance(right, int) else (
            bool(np.isclose(left, right, rtol=1e-7, atol=1e-8)) if left is not None and right is not None else left == right
        )
        comparisons[key] = {"replay": left, "published": right, "matches": matches}
        if not matches:
            raise ValueError(f"Exact frozen XGBoost replay failed on B for {key}: {left} != {right}")
    return {"status": "PASS", "dataset": "previously inspected Generator B",
            "xgboost_version": xgb.__version__, "metrics_checked": comparisons,
            "interpretation": "Inference reproduction check only; B is already inspected."}


def freeze_predictions() -> dict:
    """Score C observed inputs only, and hash the supplemental scores before label use."""
    lock, frozen, _ = _artifact_lock()
    c_manifest = read(C_DIR / "dataset_manifest.json")
    observed_path = C_DIR / "observed.json"
    if sha(observed_path) != c_manifest["file_sha256"]["observed.json"]:
        raise ValueError("Generator C observed input checksum mismatch")
    b_check = _verify_generator_b_replay()
    cases = read(observed_path)
    projected, dummy_targets = _legacy_projection(cases)
    data = build_arrays(projected, dummy_targets)
    scaler = read(V3_DIR / "model/preprocessing.json")
    data = apply_scaler(data, scaler)
    dmatrix = xgb.DMatrix(data["x"][data["mask"]])
    raw_seed_scores = []
    for path in frozen["paths"]:
        booster = xgb.Booster(params={"nthread": 1})
        booster.load_model(path)
        raw_seed_scores.append(booster.predict(dmatrix))
    raw = np.mean(raw_seed_scores, axis=0)
    scores = calibrate(raw, lock["all_model_calibrators"][BASELINE_NAME])
    threshold = float(lock["all_thresholds"][BASELINE_NAME])

    rows = []
    cursor = 0
    for case in cases:
        for record in case["records"]:
            score = float(scores[cursor])
            rows.append({"model": BASELINE_NAME, "case_id": case["case_id"],
                         "customer_group": case["customer_group"], "scenario": case["scenario"],
                         "record_id": record["record_id"], "source_type": record["source_type"],
                         "score": score, "score_kind": "CALIBRATED_PROBABILITY",
                         "threshold": threshold, "flagged": str(score >= threshold).lower()})
            cursor += 1
    if cursor != len(scores):
        raise ValueError("XGBoost C projection/score alignment mismatch")
    C_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    v3_paths = [V3_DIR / "selection_lock.json", V3_DIR / "model/manifest.json",
                V3_DIR / "model/preprocessing.json", V3_DIR / "logistic.json", *frozen["paths"]]
    manifest = {
        "status": "DELAYED_FROZEN_BASELINE_PREDICTIONS_POST_UNBLINDING",
        "blinded_confirmatory": False,
        "generator_c_labels_already_opened_before_replay": True,
        "generator_c_observed_sha256": sha(observed_path),
        "generator_c_dataset_manifest_sha256": sha(C_DIR / "dataset_manifest.json"),
        "prediction_sha256": sha(OUT_CSV), "prediction_rows": len(rows),
        "case_count": len(cases), "document_count": len(rows),
        "model": BASELINE_NAME, "model_artifact_sha256": frozen["hashes"],
        "selection_lock_sha256": sha(V3_DIR / "selection_lock.json"),
        "preprocessing_sha256": sha(V3_DIR / "model/preprocessing.json"),
        "feature_contract": NAMES, "xgboost_version": xgb.__version__,
        "frozen_threshold": threshold, "threshold_source": "reports/evidence-v3/synthetic/selection_lock.json",
        "calibrator": lock["all_model_calibrators"][BASELINE_NAME],
        "prediction_replay_validation": b_check,
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
        "routing_authorized": False, "approval_authorized": False,
        "checkout_consumes_research_outputs": False,
    }
    write_json(OUT_MANIFEST, manifest)
    manifest["prediction_manifest_sha256"] = sha(OUT_MANIFEST)
    return manifest


def _load_labeled_model_rows(prediction_path: Path, prediction_hash: str) -> list[dict]:
    if sha(prediction_path) != prediction_hash:
        raise ValueError("Delayed baseline predictions changed after freeze")
    observed = read(C_DIR / "observed.json")
    gold = read(C_DIR / "gold_labels.json")
    gold_by_case = {case["case_id"]: {r["record_id"]: r for r in case["records"]} for case in gold}
    observed_by_case = {case["case_id"]: case for case in observed}
    rows = _read_csv(prediction_path)
    for row in rows:
        target = gold_by_case[row["case_id"]][row["record_id"]]
        case = observed_by_case[row["case_id"]]
        row["material_defect"] = int(target["material_defect"])
        row["critical_defect"] = int(target["critical_defect"])
        row["customer_group"] = case["customer_group"]
    return rows


def evaluate_predictions() -> dict:
    """Delayed post-unblinding metric computation; never changes scores or cutoffs."""
    manifest = read(OUT_MANIFEST)
    if manifest.get("status") != "DELAYED_FROZEN_BASELINE_PREDICTIONS_POST_UNBLINDING":
        raise ValueError("Delayed baseline prediction freeze status is invalid")
    if sha(OUT_CSV) != manifest["prediction_sha256"]:
        raise ValueError("Delayed baseline prediction checksum mismatch")
    xgb_rows = _load_labeled_model_rows(OUT_CSV, manifest["prediction_sha256"])
    base_rows = _read_csv(C_DIR / "C_PREDICTIONS_FROZEN.csv")
    access = read(C_DIR / "LABEL_ACCESS_STATUS.json")
    # The original one-time evaluation has already unblinded C. This addendum is
    # explicitly post-unblinding and does not claim a fresh confirmatory test.
    if access.get("labels_opened_for_evaluation") is not True:
        raise RuntimeError("Expected the recorded prior Generator C unblinding state")

    observed = read(C_DIR / "observed.json")
    gold = read(C_DIR / "gold_labels.json")
    gold_by_case = {case["case_id"]: {r["record_id"]: r for r in case["records"]} for case in gold}
    observed_by_case = {case["case_id"]: case for case in observed}
    for row in base_rows:
        target = gold_by_case[row["case_id"]][row["record_id"]]
        row["material_defect"] = int(target["material_defect"])
        row["critical_defect"] = int(target["critical_defect"])
        row["customer_group"] = observed_by_case[row["case_id"]]["customer_group"]

    def detailed_metric(rows: list[dict]) -> dict:
        point = _metric(rows)
        y = np.asarray([int(r["material_defect"]) for r in rows], dtype=int)
        critical = np.asarray([int(r["critical_defect"]) for r in rows], dtype=int)
        flagged = np.asarray([str(r["flagged"]).lower() in {"true", "1"} for r in rows])
        scenario = np.asarray([r["scenario"] for r in rows], dtype=object)
        legitimate = y == 0
        discrepancy = legitimate & np.isin(scenario, [
            "C1_GROSS_NET_PERIODS", "C3_CORRECTION_LINEAGE", "C5_NONCOMPARABLE_SUBJECT_ACCOUNT"])
        c4_stale = (scenario == "C4_TIME_VALIDITY") & (critical == 1)
        point.update({
            "material_true_positives": int((flagged & (y == 1)).sum()),
            "material_false_negatives": int((~flagged & (y == 1)).sum()),
            "critical_true_positives": int((flagged & (critical == 1)).sum()),
            "critical_false_negatives": int((~flagged & (critical == 1)).sum()),
            "legitimate_false_positives": int((flagged & legitimate).sum()),
            "legitimate_true_negatives": int((~flagged & legitimate).sum()),
            "C1_C3_C5_false_positives": int((flagged & discrepancy).sum()),
            "C1_C3_C5_legitimate_support": int(discrepancy.sum()),
            "C4_stale_true_positives": int((flagged & c4_stale).sum()),
            "C4_stale_critical_support": int(c4_stale.sum()),
            "flagged_documents": int(flagged.sum()),
        })
        return point

    point = detailed_metric(xgb_rows)
    scenarios, sources = [], []
    for scenario in sorted({r["scenario"] for r in xgb_rows}):
        scenarios.append({"scenario": scenario, **detailed_metric([r for r in xgb_rows if r["scenario"] == scenario])})
    for source in sorted({r["source_type"] for r in xgb_rows}):
        sources.append({"source_type": source, **detailed_metric([r for r in xgb_rows if r["source_type"] == source])})

    def score_distribution(rows: list[dict]) -> dict:
        values = np.asarray([float(r["score"]) for r in rows], dtype=float)
        labels = np.asarray([int(r["material_defect"]) for r in rows], dtype=int)
        flags = np.asarray([str(r["flagged"]).lower() in {"true", "1"} for r in rows])
        return {"support": len(rows), "minimum": float(values.min()), "p05": float(np.quantile(values, .05)),
                "median": float(np.median(values)), "p95": float(np.quantile(values, .95)),
                "maximum": float(values.max()), "flagged_fraction": float(flags.mean()),
                "threshold": float(rows[0]["threshold"]),
                "positive_support": int(labels.sum()), "negative_support": int((labels == 0).sum())}

    score_distributions = {
        "all": score_distribution(xgb_rows),
        "by_material_label": {
            "material_defect": score_distribution([r for r in xgb_rows if int(r["material_defect"]) == 1]),
            "legitimate": score_distribution([r for r in xgb_rows if int(r["material_defect"]) == 0]),
        },
        "by_scenario": {scenario: score_distribution([r for r in xgb_rows if r["scenario"] == scenario])
                        for scenario in sorted({r["scenario"] for r in xgb_rows})},
    }

    available = {r["model"]: [] for r in base_rows}
    for row in base_rows:
        available[row["model"]].append(row)
    available[BASELINE_NAME] = xgb_rows
    bootstrap_indexes, bootstrap_cases = _stratified_group_bootstrap(
        xgb_rows, draws=BOOTSTRAP_DRAWS, seed=BOOTSTRAP_SEED)
    model_ci = _bootstrap_intervals(xgb_rows, bootstrap_indexes, bootstrap_cases)
    aggregate_fpr_draws = [
        _metric(xgb_rows, indexes, case_ids)["aggregate_legitimate_fpr"]
        for indexes, case_ids in zip(bootstrap_indexes, bootstrap_cases, strict=True)
    ]
    model_ci["aggregate_legitimate_fpr"] = {
        "lower_95": float(np.quantile(aggregate_fpr_draws, .025)),
        "upper_95": float(np.quantile(aggregate_fpr_draws, .975)),
        "valid_draws": len(aggregate_fpr_draws), "requested_draws": BOOTSTRAP_DRAWS,
    }
    hybrid = available.get("SEMANTIC_HYBRID")
    paired = None
    if hybrid:
        def key(row): return (row["case_id"], row["record_id"])
        if [key(r) for r in hybrid] != [key(r) for r in xgb_rows]:
            raise ValueError("Paired baseline rows are not aligned to frozen C predictions")
        fields = ("critical_recall", "aggregate_legitimate_fpr", "legitimate_discrepancy_fpr",
                  "stale_as_current_recall", "review_workload", "material_average_precision", "brier", "log_loss")
        draws = {name: [] for name in fields}
        for indexes, case_ids in zip(bootstrap_indexes, bootstrap_cases, strict=True):
            left = _metric(hybrid, indexes, case_ids)
            right = _metric(xgb_rows, indexes, case_ids)
            for name in fields:
                if left.get(name) is not None and right.get(name) is not None:
                    draws[name].append(left[name] - right[name])
        paired = {name: {"hybrid_minus_xgboost": float(_metric(hybrid)[name] - point[name]),
                         "lower_95": float(np.quantile(draws[name], .025)),
                         "upper_95": float(np.quantile(draws[name], .975)),
                         "valid_draws": len(draws[name]), "unit": "customer_group",
                         "scenario_stratified": True}
                  for name in fields if draws[name]}

    result = {
        "status": "DELAYED_FROZEN_BASELINE_EVALUATION_POST_UNBLINDING",
        "blinded_confirmatory": False,
        "model": BASELINE_NAME,
        "prediction_sha256": manifest["prediction_sha256"],
        "prediction_manifest_sha256": sha(OUT_MANIFEST),
        "gold_was_already_opened_before_prediction_replay": True,
        "metrics": point, "grouped_confidence_intervals": model_ci,
        "scenario_metrics": scenarios, "source_metrics": sources,
        "score_distributions": score_distributions,
        "paired_hybrid_contrasts": paired,
        "uncertainty": {"method": "scenario-stratified percentile bootstrap", "cluster_unit": "customer_group",
                        "draws": BOOTSTRAP_DRAWS, "seed": BOOTSTRAP_SEED,
                        "paired_rows": "same C records and same resampled customer groups for both models"},
        "model_artifacts_unchanged": manifest["model_artifact_sha256"],
        "threshold_unchanged": manifest["frozen_threshold"],
        "limitations": ["C labels were opened before this delayed baseline evaluation",
                        "synthetic structured records only; no external banking validation",
                        "metrics condition on one finite synthetic generator and frozen operating point"],
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
        "routing_authorized": False, "approval_authorized": False,
        "checkout_consumes_research_outputs": False,
    }
    write_json(OUT_RESULTS, result)
    _write_csv(C_DIR / "C_DELAYED_BASELINE_XGBOOST_SCENARIO_METRICS.csv", scenarios)
    _write_csv(C_DIR / "C_DELAYED_BASELINE_XGBOOST_SOURCE_METRICS.csv", sources)
    _write_csv(OUT_PAIRED, [
        {"metric": name, **values} for name, values in (paired or {}).items()
    ])
    return result


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("predict", "evaluate"))
    action = parser.parse_args().action
    result = freeze_predictions() if action == "predict" else evaluate_predictions()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
