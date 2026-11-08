"""Replay frozen V3 evidence models for registered COBI V4 experiments."""
from __future__ import annotations

import csv
from itertools import combinations
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import average_precision_score, log_loss

from evidence_ai.features import NAMES
from evidence_ai.replay import predict_frozen, read
from evidence_ai.synthetic import DATA as V3_DATA
from evidence_ai.train import RELEASE
from evidence_ai.v4_generator import OUT as B_DATA, SCENARIOS, freeze, validate_observed_schema
from ml.contracts import ROOT, sha, write_json

OUT = ROOT / "reports/evidence-v4"
MODELS = ("M0_CS_V2", "M1_LOGISTIC", "M2_XGBOOST", "M3_DEEP_SETS")
METRIC_KEYS = ("critical_recall", "critical_fnr", "average_precision", "brier", "log_loss",
               "review_workload", "document_flag_rate", "precision_at_threshold", "critical_fn_per_case")
COLORS = {"M0_CS_V2": "#8c7960", "M1_LOGISTIC": "#4777a2", "M2_XGBOOST": "#247465", "M3_DEEP_SETS": "#a45428"}
LABELS = {"M0_CS_V2": "CS V2", "M1_LOGISTIC": "Logistic regression", "M2_XGBOOST": "XGBoost", "M3_DEEP_SETS": "Deep Sets"}


def _data_slice(data: dict, indexes: np.ndarray) -> dict:
    return {key: value[indexes] if isinstance(value, np.ndarray) and value.shape[:1] == data["mask"].shape[:1]
            else value for key, value in data.items()}


def _verify_protected_v2_v3_artifacts() -> dict:
    manifest = read(OUT / "ARTIFACT_MANIFEST.json")
    if manifest.get("manifest_type") != "protected_v2_v3_baseline":
        raise ValueError("Protected baseline manifest is missing or invalid")
    for item in manifest["artifacts"]:
        path = ROOT / item["path"].replace("/", "\\")
        if not path.is_file() or sha(path) != item["sha256"]:
            raise ValueError(f"Protected V2/V3 artifact changed: {item['path']}")
    return manifest


def metrics(data: dict, probabilities: np.ndarray, threshold: float) -> dict:
    mask = data["mask"]
    valid_cases = mask.any(axis=1)
    y = data["y"][mask].astype(int)
    critical = data["critical"][mask].astype(bool)
    p = probabilities[mask].astype(float)
    flagged = (probabilities >= threshold) & mask
    flagged_docs = int(flagged.sum())
    critical_total = int(critical.sum())
    critical_missed = int((critical & ~flagged[mask]).sum())
    case_flagged = (flagged.any(axis=1) & valid_cases)
    predicted = flagged[mask]
    brier = float(np.mean(np.square(p - y))) if len(y) else None
    ll = float(log_loss(y, p, labels=[0, 1])) if len(y) else None
    ap = float(average_precision_score(y, p)) if len(np.unique(y)) == 2 else None
    recall = (critical_total - critical_missed) / critical_total if critical_total else None
    return {
        "cases": int(valid_cases.sum()), "documents": int(mask.sum()), "material_errors": int(y.sum()),
        "critical_errors": critical_total, "critical_false_negatives": critical_missed,
        "critical_recall": float(recall) if recall is not None else None,
        "critical_fnr": float(critical_missed / critical_total) if critical_total else None,
        "average_precision": ap, "brier": brier, "log_loss": ll,
        "document_flag_rate": float(flagged_docs / max(1, int(mask.sum()))),
        "precision_at_threshold": float((predicted & (y == 1)).sum() / flagged_docs) if flagged_docs else None,
        "flagged_documents": flagged_docs,
        "false_positive_documents": int((predicted & (y == 0)).sum()),
        "flagged_cases": int(case_flagged.sum()),
        "review_workload": float(case_flagged.sum() / max(1, int(valid_cases.sum()))),
        "flagged_cases_per_100": float(100 * case_flagged.sum() / max(1, int(valid_cases.sum()))),
        "critical_fn_per_case": float(critical_missed / max(1, int(valid_cases.sum()))),
    }


def _ci(values: list[float]) -> list[float] | None:
    finite = np.asarray([value for value in values if value is not None and np.isfinite(value)], dtype=float)
    if len(finite) < 50:
        return None
    return [float(np.quantile(finite, .025)), float(np.quantile(finite, .975))]


def bootstrap(data: dict, predictions: dict[str, np.ndarray], thresholds: dict[str, float], groups: list[str],
              draws: int, seed: int, strata: list[str] | None = None) -> dict:
    """Paired cluster bootstrap; optional strata preserve the B scenario mix."""
    if len(groups) != data["mask"].shape[0]:
        raise ValueError("Customer-group vector is not aligned with cases")
    group_indexes: dict[str, np.ndarray] = {}
    for group in dict.fromkeys(groups):
        group_indexes[group] = np.flatnonzero(np.asarray(groups) == group)
    rng = np.random.default_rng(seed)
    if strata is not None:
        if len(strata) != len(groups):
            raise ValueError("Stratum vector is not aligned with cases")
        group_stratum: dict[str, str] = {}
        for group, stratum in zip(groups, strata, strict=True):
            if group in group_stratum and group_stratum[group] != stratum:
                raise ValueError("A customer group spans bootstrap strata")
            group_stratum[group] = stratum
        stratum_groups = {
            stratum: list(dict.fromkeys(group for group, value in zip(groups, strata, strict=True) if value == stratum))
            for stratum in dict.fromkeys(strata)
        }
    else:
        stratum_groups = {"all": list(group_indexes)}

    values = {model: {metric: [] for metric in METRIC_KEYS} for model in predictions}
    pair_values = {f"{left}_minus_{right}": {metric: [] for metric in METRIC_KEYS}
                   for left, right in combinations(predictions, 2)}
    for _ in range(draws):
        sampled_groups: list[str] = []
        for members in stratum_groups.values():
            sampled_groups.extend(rng.choice(members, size=len(members), replace=True).tolist())
        row_indexes = np.concatenate([group_indexes[group] for group in sampled_groups])
        sample = _data_slice(data, row_indexes)
        sampled = {model: prediction[row_indexes] for model, prediction in predictions.items()}
        result = {model: metrics(sample, sampled[model], thresholds[model]) for model in predictions}
        for model, row in result.items():
            for key in METRIC_KEYS:
                value = row[key]
                if value is not None and np.isfinite(value):
                    values[model][key].append(float(value))
        for left, right in combinations(predictions, 2):
            name = f"{left}_minus_{right}"
            for key in METRIC_KEYS:
                a, b = result[left][key], result[right][key]
                if a is not None and b is not None and np.isfinite(a) and np.isfinite(b):
                    pair_values[name][key].append(float(a - b))

    return {
        "draws": draws, "seed": seed, "unit": "customer_group", "stratified": strata is not None,
        "model_ci95": {model: {key: _ci(draws_for_key) for key, draws_for_key in rows.items()}
                       for model, rows in values.items()},
        "paired_difference_ci95": {pair: {key: _ci(draws_for_key) for key, draws_for_key in rows.items()}
                                    for pair, rows in pair_values.items()},
        "_values": values,
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _v3_test():
    _verify_protected_v2_v3_artifacts()
    cases = read(V3_DATA / "observed.json")
    labels = read(V3_DATA / "technical_labels.json")
    split = read(V3_DATA / "locked_split.json")
    selected = set(split["test"])
    test_cases = [case for case in cases if case["case_key"] in selected]
    if len(test_cases) != len(selected):
        raise ValueError("V3 locked test IDs do not resolve to observed cases")
    case_groups = {case["case_key"]: case["customer_group"] for case in cases}
    cohort_groups = {name: {case_groups[case_key] for case_key in case_keys} for name, case_keys in split.items()}
    for left_index, left in enumerate(cohort_groups):
        for right in list(cohort_groups)[left_index + 1:]:
            if cohort_groups[left] & cohort_groups[right]:
                raise ValueError(f"V3 customer groups overlap: {left}/{right}")
    data, p, _, lock = predict_frozen(test_cases, labels, RELEASE / "synthetic")
    report = read(RELEASE / "synthetic/report.json")
    for name in MODELS:
        reproduced = metrics(data, p[name], lock["all_thresholds"][name])
        expected = report["models"][name]["test"]
        for key in ("cases", "documents", "material_errors", "critical_errors", "critical_recall", "critical_fnr",
                    "average_precision", "brier", "log_loss", "document_flag_rate", "review_workload"):
            if expected.get(key) is not None and not np.isclose(reproduced[key], expected[key], rtol=1e-7, atol=1e-8):
                raise ValueError(f"V3 replay mismatch for {name}.{key}: {reproduced[key]} != {expected[key]}")
    return test_cases, data, p, lock


def run_e1(protocol: dict, test_cases=None, data=None, predictions=None, lock=None) -> dict:
    if test_cases is None:
        test_cases, data, predictions, lock = _v3_test()
    thresholds = {name: float(lock["all_thresholds"][name]) for name in MODELS}
    results = {name: metrics(data, predictions[name], thresholds[name]) for name in MODELS}
    groups = [case["customer_group"] for case in test_cases]
    boot = bootstrap(data, {name: predictions[name] for name in MODELS}, thresholds, groups,
                     int(protocol["bootstrap"]["draws"]), int(protocol["bootstrap"]["seed"]))
    for name in MODELS:
        results[name]["ci95"] = boot["model_ci95"][name]
        results[name]["frozen_threshold"] = thresholds[name]
        results[name]["threshold_source"] = "V3 calibration selection lock"

    tradeoff = []
    for name in MODELS:
        row = results[name]
        tradeoff.append({"model": name, "critical_recall": row["critical_recall"],
                         "critical_recall_ci_low": row["ci95"]["critical_recall"][0],
                         "critical_recall_ci_high": row["ci95"]["critical_recall"][1],
                         "critical_fn": row["critical_false_negatives"], "critical_support": row["critical_errors"],
                         "average_precision": row["average_precision"], "ap_ci_low": row["ci95"]["average_precision"][0],
                         "ap_ci_high": row["ci95"]["average_precision"][1], "brier": row["brier"],
                         "log_loss": row["log_loss"], "case_workload": row["review_workload"],
                         "workload_ci_low": row["ci95"]["review_workload"][0],
                         "workload_ci_high": row["ci95"]["review_workload"][1],
                         "flagged_cases": row["flagged_cases"], "cases": row["cases"],
                         "threshold": thresholds[name], "threshold_source": row["threshold_source"]})
    _write_csv(OUT / "tables/model_tradeoff_table.csv", tradeoff)

    prediction_rows = []
    for case_index, case in enumerate(test_cases):
        for doc_index, doc in enumerate(case["documents"]):
            if not data["mask"][case_index, doc_index]:
                continue
            row = {"dataset": "V3_locked_test_retrospective", "customer_group": case["customer_group"],
                   "case_key": case["case_key"], "document_key": doc["document_key"],
                   "material_defect": int(data["y"][case_index, doc_index]),
                   "critical_defect": int(data["critical"][case_index, doc_index])}
            for name in MODELS:
                row[f"{name}_probability"] = float(predictions[name][case_index, doc_index])
                row[f"{name}_flagged"] = int(predictions[name][case_index, doc_index] >= thresholds[name])
            prediction_rows.append(row)
    _write_csv(OUT / "tables/e1_prediction_level.csv", prediction_rows)

    frontier_rows = []
    for name in MODELS:
        valid = predictions[name][data["mask"]]
        grid = np.unique(np.quantile(valid, np.linspace(0, 1, 101)))
        grid = np.unique(np.r_[0.0, grid, 1.0, thresholds[name]])
        for threshold in grid:
            point = metrics(data, predictions[name], float(threshold))
            frontier_rows.append({"dataset": "previously_inspected_V3_test",
                                  "evaluation_unit_x": "fraction of cases flagged",
                                  "evaluation_unit_y": "fraction of critical-defect documents detected",
                                  "model": name, "threshold": float(threshold),
                                  "critical_recall": point["critical_recall"],
                                  "case_workload": point["review_workload"],
                                  "sweep_status": "retrospective_descriptive_only",
                                  "frozen_operating_point": bool(np.isclose(threshold, thresholds[name]))})
    _write_csv(OUT / "tables/e1_frontier_curve.csv", frontier_rows)

    fig_dir = OUT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                         "axes.spines.right": False, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(8.2, 5.2), layout="constrained")
    for name in MODELS:
        rows = [row for row in frontier_rows if row["model"] == name]
        rows.sort(key=lambda item: item["case_workload"])
        ax.plot([r["case_workload"] for r in rows], [r["critical_recall"] for r in rows],
                color=COLORS[name], alpha=.58, linewidth=1.6, label=LABELS[name])
        row = results[name]
        ax.errorbar(row["review_workload"], row["critical_recall"],
                    xerr=[[row["review_workload"] - row["ci95"]["review_workload"][0]],
                          [row["ci95"]["review_workload"][1] - row["review_workload"]]],
                    yerr=[[row["critical_recall"] - row["ci95"]["critical_recall"][0]],
                          [row["ci95"]["critical_recall"][1] - row["critical_recall"]]],
                    color=COLORS[name], marker="o", capsize=3, linestyle="none")
    ax.set(xlabel="Case review workload (fraction of 192 cases)", ylabel="Critical-defect recall (fraction of 200 documents)",
           title="Cost–safety frontier — previously inspected V3 synthetic test")
    ax.text(.01, -.24, "Curves are descriptive test-set threshold sweeps and were not used to select thresholds. Points show frozen V3 thresholds; bars are 95% customer-cluster bootstrap intervals.",
            transform=ax.transAxes, fontsize=8, wrap=True)
    ax.grid(alpha=.18)
    ax.legend(frameon=False)
    for ext in ("svg", "png"):
        fig.savefig(fig_dir / f"cost_safety_frontier.{ext}", dpi=220, facecolor="white")
    plt.close(fig)

    for key, filename, title in (("critical_recall", "critical_recall_comparison", "Critical-defect recall"),
                                 ("review_workload", "review_workload_comparison", "Case review workload")):
        fig, ax = plt.subplots(figsize=(7.6, 4.2), layout="constrained")
        for i, name in enumerate(MODELS):
            value = results[name][key]
            low, high = results[name]["ci95"][key]
            ax.errorbar(value, i, xerr=[[value-low], [high-value]], marker="o", capsize=4,
                        color=COLORS[name], label=LABELS[name])
            ax.annotate(f"{value:.3f}", (value, i), xytext=(6, 1), textcoords="offset points", fontsize=9)
        ax.set(yticks=range(len(MODELS)), yticklabels=[LABELS[name] for name in MODELS], ylim=(3.5, -.5),
               xlabel=f"{title} (fraction)", title=f"{title} — V3 locked test; frozen thresholds")
        ax.text(.01, -.18, "Synthetic-only, retrospective result; 95% customer-cluster bootstrap intervals.",
                transform=ax.transAxes, fontsize=8)
        ax.grid(axis="x", alpha=.2)
        for ext in ("svg", "png"):
            fig.savefig(fig_dir / f"{filename}.{ext}", dpi=220, facecolor="white")
        plt.close(fig)

    report = {
        "experiment_id": "cobi-evidence-v4-e1",
        "status": "RETROSPECTIVE_SYNTHETIC_TECHNICAL_ONLY",
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
        "dataset": {"id": "evidence-synthetic-v3.0", "cases": int(data["mask"].shape[0]),
                    "customer_groups": len(set(groups)), "documents": int(data["mask"].sum()),
                    "material_defects": int(data["y"][data["mask"]].sum()),
                    "critical_defects": int(data["critical"][data["mask"]].sum()),
                    "previously_inspected": True},
        "models": results, "pairwise_differences": boot["paired_difference_ci95"],
        "bootstrap": {"draws": boot["draws"], "seed": boot["seed"], "unit": boot["unit"],
                      "conditions_on": ["frozen models", "frozen V3 calibrators", "frozen V3 thresholds"]},
        "threshold_sweep": "retrospective_descriptive_only",
        "limitations": ["V3 test has previously been inspected", "synthetic programmatic labels",
                        "intervals condition on fitted models and thresholds", "not bank validation"],
    }
    write_json(OUT / "E1_RESULTS.json", report)
    md = ["# E1 Cost–Safety Frontier", "", "**Status:** retrospective V3 synthetic replay; not a new confirmatory test.", "",
          "The four frozen models were replayed at the thresholds registered in the V3 selection lock. The output includes document-level predictions, case-level workload, model metrics, paired cluster-bootstrap intervals, and a descriptive retrospective threshold sweep.", "",
          "| Model | Critical recall | Critical FN / support | AP | Brier | Log loss | Case workload |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name in MODELS:
        row = results[name]
        md.append(f"| {LABELS[name]} | {row['critical_recall']:.3f} | {row['critical_false_negatives']} / {row['critical_errors']} | {row['average_precision']:.4f} | {row['brier']:.4f} | {row['log_loss']:.4f} | {row['review_workload']:.4f} |")
    md += ["", "The test contains 192 cases from 96 customer groups and 753 documents (293 material, 200 critical). The frontier sweep was computed only as a retrospective description and was not used to alter thresholds or choose a model.", "",
           "**Interpretation:** On this previously inspected synthetic test, XGBoost has the lowest observed workload (70.8%) and strongest observed AP (0.9828), while its critical recall is 90.5%. This is conditional evidence within the V3 generator; it does not establish bank performance or safety.", "",
           "**Outputs:** `E1_RESULTS.json`, `tables/e1_prediction_level.csv`, `tables/model_tradeoff_table.csv`, `tables/e1_frontier_curve.csv`, and the three SVG/PNG figures under `figures/`."]
    (OUT / "E1_COST_SAFETY_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report, {"test_cases": test_cases, "data": data, "predictions": predictions,
                    "thresholds": thresholds, "groups": groups, "bootstrap": boot}


def _ece(probability: np.ndarray, target: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    result = 0.0
    for index in range(bins):
        mask = (probability >= edges[index]) & ((probability < edges[index + 1]) if index < bins - 1 else (probability <= edges[index + 1]))
        if mask.any():
            result += float(mask.mean() * abs(probability[mask].mean() - target[mask].mean()))
    return result


def run_e2(protocol: dict, e1_context: dict | None = None) -> dict:
    manifest = freeze(B_DATA)
    b_cases = read(B_DATA / "observed.json")
    b_labels = read(B_DATA / "gold_labels.json")
    compatibility = validate_observed_schema(b_cases)
    if compatibility["incompatible_documents"]:
        raise ValueError("Registered B challenge contains incompatible inputs; do not coerce them")
    if len(NAMES) != 32:
        raise ValueError("Frozen V3 feature count changed")
    data, probabilities, _, lock = predict_frozen(b_cases, b_labels, RELEASE / "synthetic")
    thresholds = {name: float(lock["all_thresholds"][name]) for name in MODELS}
    groups = [case["customer_group"] for case in b_cases]
    strata = [case["case_key"].split("-", 1)[0] for case in b_cases]
    all_results = {name: metrics(data, probabilities[name], thresholds[name]) for name in MODELS}
    b_boot = bootstrap(data, {name: probabilities[name] for name in MODELS}, thresholds, groups,
                       int(protocol["bootstrap"]["draws"]), int(protocol["bootstrap"]["seed"]), strata)
    for name in MODELS:
        all_results[name]["ci95"] = b_boot["model_ci95"][name]
        all_results[name]["frozen_threshold"] = thresholds[name]

    scenario_results: dict[str, dict] = {}
    by_scenario_boot = {}
    for scenario_index, scenario in enumerate(SCENARIOS):
        indexes = np.flatnonzero(np.asarray(strata) == scenario)
        subset = _data_slice(data, indexes)
        subgroups = [groups[index] for index in indexes]
        scenario_results[scenario] = {
            name: metrics(subset, probabilities[name][indexes], thresholds[name]) for name in MODELS
        }
        by_scenario_boot[scenario] = bootstrap(
            subset, {name: probabilities[name][indexes] for name in MODELS}, thresholds, subgroups,
            int(protocol["bootstrap"]["draws"]), int(protocol["bootstrap"]["seed"]) + scenario_index + 1
        )
        for name in MODELS:
            scenario_results[scenario][name]["ci95"] = by_scenario_boot[scenario]["model_ci95"][name]

    gaps = {}
    if e1_context:
        a_boot_values = e1_context["bootstrap"]["_values"]
        b_boot_values = b_boot["_values"]
        for name in MODELS:
            a = e1_context["results"][name]
            b = all_results[name]
            row = {"AP_A_minus_AP_B": float(a["average_precision"] - b["average_precision"]),
                   "CriticalRecall_A_minus_B": float(a["critical_recall"] - b["critical_recall"]),
                   "LogLoss_B_minus_A": float(b["log_loss"] - a["log_loss"])}
            ci = {}
            for label, metric_key, direction in (("AP_A_minus_AP_B", "average_precision", 1),
                                                 ("CriticalRecall_A_minus_B", "critical_recall", 1),
                                                 ("LogLoss_B_minus_A", "log_loss", -1)):
                av = np.asarray(a_boot_values[name][metric_key], dtype=float)
                bv = np.asarray(b_boot_values[name][metric_key], dtype=float)
                count = min(len(av), len(bv))
                diff = (av[:count] - bv[:count]) * direction
                ci[label] = _ci(diff.tolist())
            row["independent_customer_bootstrap_ci95"] = ci
            gaps[name] = row

    scenario_rows = []
    for scenario in SCENARIOS:
        for name in MODELS:
            row = scenario_results[scenario][name]
            scenario_rows.append({"scenario": scenario, "model": name, "cases": row["cases"],
                                  "customer_groups": manifest["scenario_counts"][scenario]["customer_groups"],
                                  "documents": row["documents"], "material_errors": row["material_errors"],
                                  "critical_errors": row["critical_errors"], "critical_false_negatives": row["critical_false_negatives"],
                                  "critical_recall": row["critical_recall"], "critical_recall_ci95": row["ci95"]["critical_recall"],
                                  "critical_fnr": row["critical_fnr"],
                                  "critical_fnr_ci95": ([1-row["ci95"]["critical_recall"][1],
                                                          1-row["ci95"]["critical_recall"][0]]
                                                         if row["ci95"]["critical_recall"] else None),
                                  "average_precision": row["average_precision"],
                                  "brier": row["brier"], "log_loss": row["log_loss"],
                                  "review_workload": row["review_workload"],
                                  "false_positive_documents": row["false_positive_documents"],
                                  "flagged_cases_per_100": row["flagged_cases_per_100"],
                                  "frozen_threshold": thresholds[name]})
    _write_csv(OUT / "tables/robustness_by_scenario.csv", scenario_rows)

    # B5 is the prespecified negative-control-like cohort for legitimate discrepancies.
    legitimate_rows = {}
    b5_indexes = np.flatnonzero(np.asarray(strata) == "B5")
    b5 = _data_slice(data, b5_indexes)
    for name in MODELS:
        row = metrics(b5, probabilities[name][b5_indexes], thresholds[name])
        legitimate_rows[name] = {
            "cases": row["cases"], "documents": row["documents"],
            "programmatic_gold_errors": row["material_errors"],
            "flagged_legitimate_documents": row["false_positive_documents"],
            "false_positive_rate_on_legitimate_documents": (
                row["false_positive_documents"] / (row["documents"] - row["material_errors"])
                if row["documents"] > row["material_errors"] else None),
        }

    # Scenario-level and aggregate case/document denominators, label prevalence and ECE.
    base_rates = {"V3_A": {"cases": int(e1_context["data"]["mask"].shape[0]) if e1_context else None,
                           "documents": int(e1_context["data"]["mask"].sum()) if e1_context else None,
                           "material_prevalence": float(e1_context["data"]["y"][e1_context["data"]["mask"]].mean()) if e1_context else None,
                           "critical_prevalence": float(e1_context["data"]["critical"][e1_context["data"]["mask"]].mean()) if e1_context else None},
                  "Generator_B": {"cases": int(data["mask"].shape[0]), "documents": int(data["mask"].sum()),
                           "material_prevalence": float(data["y"][data["mask"]].mean()),
                           "critical_prevalence": float(data["critical"][data["mask"]].mean())}}
    calibration = {}
    for name in MODELS:
        y = data["y"][data["mask"]]
        p = probabilities[name][data["mask"]]
        calibration[name] = {"brier": float(np.mean((p-y) ** 2)),
                             "log_loss": float(log_loss(y, p, labels=[0, 1])), "ece_10_equal_width": _ece(p, y)}

    report = {
        "experiment_id": "cobi-evidence-v4-e2",
        "status": "SYNTHETIC_PROGRAMMATIC_GOLD_ONLY",
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
        "protocol_sha256": manifest["protocol_sha256"],
        "generator_manifest": manifest,
        "compatibility": compatibility,
        "models": all_results,
        "paired_model_difference_ci95": b_boot["paired_difference_ci95"],
        "scenario_results": scenario_results,
        "generalization_gaps": gaps,
        "base_rates": base_rates,
        "calibration": calibration,
        "legitimate_discrepancies_B5": legitimate_rows,
        "failure_taxonomy": {
            "missed_critical_defects": {name: all_results[name]["critical_false_negatives"] for name in MODELS},
            "false_positives_on_legitimate_B5": {name: legitimate_rows[name]["flagged_legitimate_documents"] for name in MODELS},
            "parsing_or_schema_incompatibilities": compatibility["incompatible_documents"],
            "calibration_deterioration_vs_A": {
                name: {"delta_brier_B_minus_A": float(calibration[name]["brier"] - e1_context["results"][name]["brier"]),
                       "delta_log_loss_B_minus_A": float(calibration[name]["log_loss"] - e1_context["results"][name]["log_loss"]),
                       "delta_ece_B_minus_A": float(calibration[name]["ece_10_equal_width"] - _ece(
                           e1_context["predictions"][name][e1_context["data"]["mask"]],
                           e1_context["data"]["y"][e1_context["data"]["mask"]]))} for name in MODELS
            } if e1_context else {},
            "unseen_source_combinations": {name: scenario_results["B6"][name]["review_workload"] for name in MODELS},
        },
        "bootstrap": {"draws": b_boot["draws"], "seed": b_boot["seed"], "unit": b_boot["unit"],
                      "stratified_aggregate": True, "conditions_on": ["frozen models", "frozen V3 calibrators", "frozen V3 thresholds"]},
        "limitations": ["programmatic synthetic gold, not human-reviewed bank truth",
                        "the V3 feature contract is limited to three known source categories",
                        "AP is prevalence-sensitive; compare alongside base rates",
                        "bootstrap intervals condition on frozen models and thresholds"],
    }
    write_json(OUT / "E2_RESULTS.json", report)
    prediction_rows = []
    for case_index, case in enumerate(b_cases):
        for doc_index, doc in enumerate(case["documents"]):
            if not data["mask"][case_index, doc_index]:
                continue
            row = {"dataset": "Generator_B", "scenario": strata[case_index],
                   "customer_group": case["customer_group"], "case_key": case["case_key"],
                   "document_key": doc["document_key"],
                   "material_defect": int(data["y"][case_index, doc_index]),
                   "critical_defect": int(data["critical"][case_index, doc_index])}
            for name in MODELS:
                row[f"{name}_probability"] = float(probabilities[name][case_index, doc_index])
                row[f"{name}_flagged"] = int(probabilities[name][case_index, doc_index] >= thresholds[name])
            prediction_rows.append(row)
    _write_csv(OUT / "tables/e2_prediction_level.csv", prediction_rows)
    _write_e2_figures(report)
    _write_e2_markdown(report)
    return report, {"data": data, "predictions": probabilities, "thresholds": thresholds,
                    "groups": groups, "strata": strata, "bootstrap": b_boot}


def _write_e2_figures(report: dict):
    fig_dir = OUT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                         "axes.spines.right": False, "svg.fonttype": "none"})
    # A/B primary metrics.
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 4.4), layout="constrained")
    a_report = read(RELEASE / "synthetic/report.json")
    for ax, metric, title in ((axes[0], "critical_recall", "Critical recall"),
                              (axes[1], "average_precision", "Material-defect AP"),
                              (axes[2], "review_workload", "Case review workload")):
        for index, name in enumerate(MODELS):
            a = a_report["models"][name]["test"][metric]
            b = report["models"][name][metric]
            ax.plot([0, 1], [a, b], marker="o", color=COLORS[name], label=LABELS[name])
            a_interval = a_report["models"][name]["ci95"][metric]
            b_interval = report["models"][name]["ci95"][metric]
            for point, value, interval in ((0, a, a_interval), (1, b, b_interval)):
                if interval:
                    ax.errorbar(point, value, yerr=[[value-interval[0]], [interval[1]-value]],
                                color=COLORS[name], capsize=2, linestyle="none", linewidth=.9)
        ax.set(xticks=[0, 1], xticklabels=["V3 A test", "Generator B"], ylim=(0, 1), title=title)
        ax.grid(axis="y", alpha=.18)
    axes[0].legend(frameon=False, loc="best")
    fig.suptitle("Frozen evidence models under an independent synthetic generator")
    fig.text(.01, -.02, "V3 A is previously inspected; B is programmatic synthetic gold. Thresholds and preprocessing are frozen. Recall/workload are operating-point metrics; AP is prevalence-sensitive.", fontsize=8)
    for ext in ("svg", "png"):
        fig.savefig(fig_dir / f"generator_shift_performance.{ext}", dpi=220, facecolor="white")
    plt.close(fig)

    # Scenario failure matrix displays critical FNR; color scale has explicit units.
    matrix = np.asarray([[report["scenario_results"][scenario][name]["critical_fnr"] for name in MODELS]
                         for scenario in SCENARIOS], dtype=float)
    fig, ax = plt.subplots(figsize=(8.4, 5.4), layout="constrained")
    image = ax.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=max(.4, float(np.nanmax(matrix))))
    ax.set(xticks=range(len(MODELS)), xticklabels=[LABELS[name] for name in MODELS],
           yticks=range(len(SCENARIOS)), yticklabels=SCENARIOS,
           title="Generator B failure matrix — critical false-negative rate")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, "NA" if np.isnan(matrix[i, j]) else f"{matrix[i, j]:.3f}",
                    ha="center", va="center", color="black", fontsize=9)
    bar = fig.colorbar(image, ax=ax)
    bar.set_label("Critical false-negative rate (fraction of critical documents)")
    fig.text(.01, -.02, "Each cell uses unchanged V3 thresholds. Scenario-specific 95% customer-cluster intervals are in tables/robustness_by_scenario.csv.", fontsize=8)
    for ext in ("svg", "png"):
        fig.savefig(fig_dir / f"scenario_failure_matrix.{ext}", dpi=220, facecolor="white")
    plt.close(fig)

    # Generalization gaps use protocol-sign convention.
    gap_names = list(report["generalization_gaps"])
    if gap_names:
        fig, ax = plt.subplots(figsize=(8.5, 5.3), layout="constrained")
        width = .22
        labels = ["AP(A−B)", "Recall(A−B)", "LogLoss(B−A)"]
        keys = ["AP_A_minus_AP_B", "CriticalRecall_A_minus_B", "LogLoss_B_minus_A"]
        x = np.arange(len(gap_names))
        for index, (key, label) in enumerate(zip(keys, labels, strict=True)):
            values = [report["generalization_gaps"][name][key] for name in gap_names]
            offsets = x + (index - 1) * width
            ax.bar(offsets, values, width, label=label,
                   color=("#4777a2", "#247465", "#a45428")[index])
            for pos, name, value in zip(offsets, gap_names, values, strict=True):
                interval = report["generalization_gaps"][name]["independent_customer_bootstrap_ci95"][key]
                if interval:
                    ax.errorbar(pos, value, yerr=[[value-interval[0]], [interval[1]-value]],
                                color="#263a34", capsize=2, linestyle="none", linewidth=.9)
        ax.axhline(0, color="#555555", linewidth=.8)
        ax.set(xticks=x, xticklabels=[LABELS[name] for name in gap_names],
               ylabel="Difference in metric units", title="Generalization gaps at frozen operating points")
        ax.legend(frameon=False)
        ax.grid(axis="y", alpha=.18)
        fig.text(.01, -.02, "A is the previously inspected V3 test; B is the registered independent Generator B. Positive values follow the sign convention shown in each label.", fontsize=8)
        for ext in ("svg", "png"):
            fig.savefig(fig_dir / f"generalization_gap.{ext}", dpi=220, facecolor="white")
        plt.close(fig)


def _write_e2_markdown(report: dict):
    md = ["# E2 Independent Generator Challenge", "",
          "**Status:** frozen V3 models evaluated on registered, independently generated synthetic cases. Labels are programmatic synthetic gold, not human-reviewed bank truth.", "",
          f"Generator B contains {report['generator_manifest']['counts']['cases']} cases, {report['generator_manifest']['counts']['customer_groups']} customer groups, and {report['generator_manifest']['counts']['documents']} documents. Schema compatibility: {report['compatibility']['compatible_documents']} documents compatible; {report['compatibility']['incompatible_documents']} incompatible.", "",
          "## Aggregate results", "", "| Model | Critical recall | Critical FN / support | AP | Brier | Log loss | Case workload |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name in MODELS:
        row = report["models"][name]
        md.append(f"| {LABELS[name]} | {row['critical_recall']:.3f} | {row['critical_false_negatives']} / {row['critical_errors']} | {row['average_precision']:.4f} | {row['brier']:.4f} | {row['log_loss']:.4f} | {row['review_workload']:.4f} |")
    md += ["", "## Scenario results", "", "| Scenario | Model | Cases | Critical recall | Critical FN | AP | Workload |", "|---|---|---:|---:|---:|---:|---:|"]
    for scenario in SCENARIOS:
        for name in MODELS:
            row = report["scenario_results"][scenario][name]
            md.append(f"| {scenario} | {LABELS[name]} | {row['cases']} | {row['critical_recall']:.3f} | {row['critical_false_negatives']} | {row['average_precision']:.4f} | {row['review_workload']:.4f} |")
    md += ["", "## Interpretation controls", "",
           "Generator A metrics are retrospective because the V3 test has already been opened and discussed. Generator B metrics are a new synthetic challenge with a different event-ledger design. Thresholds, model weights, preprocessing and calibration remain frozen. AP is reported with both A/B label prevalences because it is prevalence-sensitive.", "",
           "**Failure categories:** missed critical defects, false positives on legitimate discrepancies in B5, parsing/schema incompatibility, calibration changes, and performance on the B6 source-combination scenario are itemized in `E2_RESULTS.json`.", "",
           "**Limitations:** this is not real-bank validation. The scenarios, labels and parameter ranges are synthetic. Intervals condition on fixed model artifacts and thresholds. A low workload can coincide with unacceptable missed-defect performance.", "",
           "**Outputs:** `E2_RESULTS.json`, `tables/robustness_by_scenario.csv`, and `figures/generator_shift_performance`, `scenario_failure_matrix`, and `generalization_gap` in SVG/PNG formats."]
    (OUT / "E2_ROBUSTNESS_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def run():
    protocol = read(OUT / "experiment_protocol.json")
    e1_report, e1_context = run_e1(protocol)
    e1_context["results"] = e1_report["models"]
    e2_report, e2_context = run_e2(protocol, e1_context)
    return e1_report, e2_report, e1_context, e2_context


if __name__ == "__main__":
    e1, e2, _, _ = run()
    print(json.dumps({"e1_status": e1["status"], "e2_status": e2["status"],
                      "e2_cases": e2["generator_manifest"]["counts"]["cases"]}, indent=2))
