"""Reconcile and publish read-only V4.1 research and pitch artifacts.

This module consumes only already frozen prediction/label summaries. It does
not train, calibrate, select, or alter models and thresholds.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import struct
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/evidence-v4.1"
PITCH = OUT / "pitch"
FIGURES = PITCH / "figures"
DATA = OUT / "data/generator-c-v1"
METRICS_PATH = OUT / "GENERATOR_C_METRICS.json"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def pct(value, places=2):
    return "—" if value is None else f"{100 * value:.{places}f}%"


def fnum(value, places=4):
    return "—" if value is None else f"{value:.{places}f}"


def ci_label(interval):
    if not interval or interval.get("lower_95") is None:
        return "—"
    return f"[{fnum(interval['lower_95'])}, {fnum(interval['upper_95'])}]"


def load_metrics():
    result = read(METRICS_PATH)
    if result.get("all_previous_aggregate_metrics_match") is not True:
        raise ValueError("Prior aggregate reconciliation does not match")
    if result.get("prediction_freeze_verified") is not True:
        raise ValueError("Frozen predictions do not verify")
    if result.get("models_or_thresholds_changed") is not False:
        raise ValueError("A model or threshold changed during reconciliation")
    return result


def make_csv(path: Path, rows: list[dict], headers: list[str] | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = headers or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_reports(r):
    agg = r["aggregate_metrics"]
    h = agg["SEMANTIC_HYBRID"]
    delayed_path = DATA / "C_DELAYED_BASELINE_XGBOOST_RESULTS.json"
    delayed_xgb = read(delayed_path) if delayed_path.is_file() else None
    xgb_metrics = delayed_xgb["metrics"] if delayed_xgb else None
    if delayed_xgb is None:
        raise ValueError("The delayed frozen XGBoost evaluation must be present before final report generation")
    ci = r["bootstrap"]["intervals_by_model"]["SEMANTIC_HYBRID"]
    scenarios = [x for x in r["scenario_metrics"] if x["model"] == "SEMANTIC_HYBRID"]
    sources = [x for x in r["source_metrics"] if x["model"] == "SEMANTIC_HYBRID"]
    d1 = read(OUT / "POST_EVALUATION_AUDIT_ADDENDUM.json")
    c_manifest = read(DATA / "dataset_manifest.json")
    frozen = read(OUT / "models/frozen-v1/frozen_model_manifest.json")
    rel = read(OUT / "models/frozen-v1/frozen_release.json")
    protected = verify_protected()
    v4_mismatch_lines = []
    for item in protected["mismatches"]:
        if item["manifest"].startswith("V4"):
            v4_mismatch_lines.append(
                f"- `{item['path']}`: expected `{item['expected_sha256']}`, current `{item['actual_sha256'] or 'MISSING'}`."
            )
    v4_detail = "\n".join(v4_mismatch_lines) if v4_mismatch_lines else "- No V4 artifact mismatches."

    scenario_rows = []
    for x in scenarios:
        scenario_rows.append(
            f"| {x['scenario']} | {x['documents']} | {x['critical_tp']}/{x['critical_support']} | "
            f"{pct(x['critical_recall'])} | {x['legitimate_fp']}/{x['legitimate_support']} | "
            f"{pct(x['overall_legitimate_fpr'])} | {x['flagged_case_count']}/{x['case_count']} | {pct(x['case_review_workload'])} |"
        )
    source_table_rows = []
    for x in sources:
        source_table_rows.append(
            f"| {x['source_type']} | {x['documents']} | {x['critical_tp']}/{x['critical_support']} ({pct(x['critical_recall'])}) | "
            f"{x['legitimate_fp']}/{x['legitimate_support']} ({pct(x['overall_legitimate_fpr'])}) | "
            f"{x['flagged_case_count']}/{x['case_count']} ({pct(x['case_review_workload'])}) |"
        )
    xgb_scenario_rows = []
    for x in delayed_xgb["scenario_metrics"]:
        xgb_scenario_rows.append(
            f"| {x['scenario']} | {x['critical_true_positives']}/{x['critical_errors']} ({pct(x['critical_recall'])}) | "
            f"{x['legitimate_false_positives']}/{x['aggregate_legitimate_support']} ({pct(x['aggregate_legitimate_fpr'])}) | "
            f"{x['flagged_cases']}/{x['case_count']} ({pct(x['review_workload'])}) | {fnum(x['material_average_precision'])} |"
        )
    xgb_source_rows = []
    for x in delayed_xgb["source_metrics"]:
        xgb_source_rows.append(
            f"| {x['source_type']} | {x['critical_true_positives']}/{x['critical_errors']} ({pct(x['critical_recall'])}) | "
            f"{x['legitimate_false_positives']}/{x['aggregate_legitimate_support']} ({pct(x['aggregate_legitimate_fpr'])}) | "
            f"{x['flagged_cases']}/{x['case_count']} ({pct(x['review_workload'])}) |"
        )
    # CSV source columns are part of the source metric schema; retain every source row.
    make_csv(OUT / "GENERATOR_C_SOURCE_METRICS.csv", sources)
    make_csv(DATA / "C_DELAYED_BASELINE_XGBOOST_SCENARIO_METRICS.csv", delayed_xgb["scenario_metrics"])
    make_csv(DATA / "C_DELAYED_BASELINE_XGBOOST_SOURCE_METRICS.csv", delayed_xgb["source_metrics"])

    baseline_names = ["M0_CS_V2", "M1_LOGISTIC", "M3_DEEP_SETS", "SEMANTIC_RULE",
                      "SEMANTIC_LOGISTIC", "SEMANTIC_DEEP_SETS", "SEMANTIC_HYBRID"]
    baseline_rows = []
    for model in baseline_names:
        m = agg[model]
        baseline_rows.append(
            f"| {model} | {pct(m['critical_recall'])} ({m['critical_tp']}/{m['critical_support']}) | "
            f"{pct(m['overall_legitimate_fpr'])} ({m['legitimate_fp']}/{m['legitimate_support']}) | "
            f"{pct(m['case_review_workload'])} ({m['flagged_case_count']}/{m['case_count']}) | "
            f"{fnum(m['material_average_precision'])} |"
        )
    if xgb_metrics:
        baseline_rows.append(
            f"| Frozen V3 XGBoost (delayed) | {pct(xgb_metrics['critical_recall'])} "
            f"({xgb_metrics['critical_true_positives']}/{xgb_metrics['critical_errors']}) | "
            f"{pct(xgb_metrics['aggregate_legitimate_fpr'])} "
            f"({xgb_metrics['legitimate_false_positives']}/{xgb_metrics['aggregate_legitimate_support']}) | "
            f"{pct(xgb_metrics['review_workload'])} "
            f"({xgb_metrics['flagged_cases']}/{xgb_metrics['case_count']}) | "
            f"{fnum(xgb_metrics['material_average_precision'])} |"
        )
    baseline_recall_best = max(
        [agg[name]["critical_recall"] for name in ("M0_CS_V2", "M1_LOGISTIC", "M3_DEEP_SETS")]
        + [xgb_metrics["critical_recall"]]
    )
    summary_path = OUT / "GENERATOR_C_SUMMARY.json"
    summary = read(summary_path)
    xgb_ci = delayed_xgb["grouped_confidence_intervals"]
    xgb_summary_row = {
        "model": "M2_XGBOOST", "label": "Frozen V3 XGBoost (delayed post-unblinding)",
        "availability": "AVAILABLE_DELAYED_POST_UNBLINDING",
        "critical_recall": xgb_metrics["critical_recall"],
        "critical_tp": xgb_metrics["critical_true_positives"],
        "critical_support": xgb_metrics["critical_errors"],
        "overall_legitimate_fpr": xgb_metrics["aggregate_legitimate_fpr"],
        "legitimate_fp": xgb_metrics["legitimate_false_positives"],
        "legitimate_support": xgb_metrics["aggregate_legitimate_support"],
        "legitimate_discrepancy_fpr_c1_c3_c5": xgb_metrics["legitimate_discrepancy_fpr"],
        "legitimate_discrepancy_fp_c1_c3_c5": xgb_metrics["C1_C3_C5_false_positives"],
        "legitimate_discrepancy_support_c1_c3_c5": xgb_metrics["C1_C3_C5_legitimate_support"],
        "c4_stale_as_current_recall": xgb_metrics["stale_as_current_recall"],
        "c4_stale_tp": xgb_metrics["C4_stale_true_positives"],
        "c4_stale_critical_support": xgb_metrics["C4_stale_critical_support"],
        "case_review_workload": xgb_metrics["review_workload"],
        "flagged_case_count": xgb_metrics["flagged_cases"], "case_count": xgb_metrics["case_count"],
        "material_average_precision": xgb_metrics["material_average_precision"],
        "brier_score": xgb_metrics["brier"], "log_loss": xgb_metrics["log_loss"],
        "frozen_threshold": xgb_metrics["frozen_threshold"],
        "ci95": {
            "critical_recall": xgb_ci["critical_recall"],
            "overall_legitimate_fpr": xgb_ci["aggregate_legitimate_fpr"],
            "legitimate_discrepancy_fpr_c1_c3_c5": xgb_ci["legitimate_discrepancy_fpr"],
            "c4_stale_as_current_recall": xgb_ci["stale_as_current_recall"],
            "case_review_workload": xgb_ci["review_workload"],
            "material_average_precision": xgb_ci["material_average_precision"],
            "brier_score": xgb_ci["brier"], "log_loss": xgb_ci["log_loss"],
        },
        "evaluation_status": delayed_xgb["status"],
        "prediction_sha256": delayed_xgb["prediction_sha256"],
    }
    summary_models = summary.get("model_comparison", [])
    summary_models = [row for row in summary_models if row.get("model") != "M2_XGBOOST"]
    summary_models.append(xgb_summary_row)
    summary["model_comparison"] = summary_models
    summary.setdefault("model_availability", {})["M2_XGBOOST"] = "AVAILABLE_DELAYED_POST_UNBLINDING"
    summary["baseline_comparison_status"] = "FROZEN_V3_BASELINES_COMPLETE_DELAYED_POST_UNBLINDING"
    summary["semantic_xgboost_status"] = "NOT_EVALUATED"
    summary.setdefault("acceptance", {})[
        "aggregate_recall_degradation_vs_best_complete_frozen_baseline_max_0_02"
    ] = bool(h["critical_recall"] >= baseline_recall_best - .02)
    summary["acceptance"]["best_available_baseline_critical_recall_partial"] = float(baseline_recall_best)
    summary["acceptance"]["full_registered_acceptance_status"] = (
        "FROZEN_V3_BASELINES_COMPLETE_DELAYED_POST_UNBLINDING; SEMANTIC_XGBOOST_NOT_EVALUATED"
    )
    write(summary_path, json.dumps(summary, indent=2))

    # Preserve the original pre-label prediction metrics and attach a separately
    # hashed delayed baseline supplement without changing their frozen rows.
    metrics_record = read(METRICS_PATH)
    metrics_record["delayed_frozen_baseline_evaluation"] = {
        "status": delayed_xgb["status"], "blinded_confirmatory": False,
        "model": "M2_XGBOOST", "metrics": xgb_metrics,
        "grouped_confidence_intervals": xgb_ci,
        "paired_hybrid_contrasts": delayed_xgb["paired_hybrid_contrasts"],
        "prediction_sha256": delayed_xgb["prediction_sha256"],
        "prediction_manifest_sha256": delayed_xgb["prediction_manifest_sha256"],
    }
    write(METRICS_PATH, json.dumps(metrics_record, indent=2))
    ablation_names = ["SEMANTIC_LOGISTIC", "ABLATION_NO_TEMPORAL", "ABLATION_NO_COMPARABILITY", "ABLATION_NO_SOURCE_PROVENANCE"]
    abl_rows = []
    for model in ablation_names:
        m = agg[model]
        abl_rows.append(
            f"| {model} | {m['critical_tp']}/{m['critical_support']} ({pct(m['critical_recall'])}) | "
            f"{m['c4_stale_tp']}/{m['c4_stale_critical_support']} ({pct(m['c4_stale_as_current_recall'])}) | "
            f"{m['legitimate_fp']}/{m['legitimate_support']} ({pct(m['overall_legitimate_fpr'])}) | "
            f"{m['legitimate_discrepancy_fp_c1_c3_c5']}/{m['legitimate_discrepancy_support_c1_c3_c5']} ({pct(m['legitimate_discrepancy_fpr_c1_c3_c5'])}) | "
            f"{m['flagged_case_count']}/{m['case_count']} ({pct(m['case_review_workload'])}) | {fnum(m['material_average_precision'])} |"
        )

    results_md = f"""# Generator C Results — V4.1

**Status:** POST-UNBLINDING RECONCILIATION; EXPLORATORY. **Validation:** `EVIDENCE_AI_VALIDATION_BLOCKED`.

## Dataset and frozen-output record

Generator `semantic-ledger-c-v1.0`, seed `{c_manifest['seed']}`, protocol `{r['protocol_id']}`. The challenge has **{r['dataset']['customer_groups']:,} customer groups**, **{r['dataset']['cases']:,} cases**, and **{r['dataset']['documents']:,} documents**. Predictions were frozen before labels opened: prediction SHA-256 `{r['prediction_sha256']}`. This report reconciles those frozen outputs; no model, rule condition, calibration, threshold, or selection was changed using C labels.

Generator C labels have already been opened. These are observed measurements on a registered synthetic challenge, but they are not a fresh blinded confirmatory evaluation.

## Semantic Hybrid point estimates

| Metric | Numerator / denominator | Estimate | 95% customer-group bootstrap interval |
|---|---:|---:|---:|
| Critical recall | {h['critical_tp']} / {h['critical_support']} | {pct(h['critical_recall'])} | {ci_label(ci['critical_recall'])} |
| Critical FNR | {h['critical_fn']} / {h['critical_support']} | {pct(h['critical_fnr'])} | [0, 0] |
| Overall legitimate-document FPR | {h['legitimate_fp']} / {h['legitimate_support']} | {pct(h['overall_legitimate_fpr'])} | {ci_label(ci['overall_legitimate_fpr'])} |
| C1/C3/C5 legitimate-discrepancy FPR | {h['legitimate_discrepancy_fp_c1_c3_c5']} / {h['legitimate_discrepancy_support_c1_c3_c5']} | {pct(h['legitimate_discrepancy_fpr_c1_c3_c5'])} | {ci_label(ci['legitimate_discrepancy_fpr_c1_c3_c5'])} |
| C4 stale-as-current recall | {h['c4_stale_tp']} / {h['c4_stale_critical_support']} | {pct(h['c4_stale_as_current_recall'])} | {ci_label(ci['c4_stale_as_current_recall'])} |
| Case review workload | {h['flagged_case_count']} / {h['case_count']} | {pct(h['case_review_workload'])} | {ci_label(ci['case_review_workload'])} |
| Material-defect average precision | {h['material_tp']} material positives / {h['documents']} documents | {fnum(h['material_average_precision'])} | {ci_label(ci['material_average_precision'])} |
| Brier score | mean squared probability error over {h['documents']} documents | {fnum(h['brier_score'])} | {ci_label(ci['brier_score'])} |
| Log loss | mean binary cross-entropy over {h['documents']} documents | {fnum(h['log_loss'])} | {ci_label(ci['log_loss'])} |

Metric denominators are document-level except workload, which is case-level. FPR is FP/(FP+TN) among gold legitimate documents. Critical recall is TP/(TP+FN). AP uses the continuous material-defect probability and all {h['documents']} documents. Brier and log loss use the calibrated frozen probability outputs. The case workload counts a case if one or more of its documents crossed the frozen decision threshold `{h['frozen_threshold']:.8f}`.

The C1/C3/C5 zero is **0 observed errors**, not zero population risk. The bootstrap percentile interval is degenerate at this boundary. Cluster-aware bounds are reported separately in `STATISTICAL_AUDIT.md`.

## Outcomes by scenario

| Scenario | Documents | Critical TP / support | Critical recall | Legitimate FP / support | Legitimate FPR | Cases flagged / total | Workload |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(scenario_rows)}

Undefined recall/AP values for scenarios without positive examples remain null. Source-stratified detail is in `GENERATOR_C_SOURCE_METRICS.csv`; the paired model contrasts and raw grouped CIs are preserved in companion CSV files.

## Outcomes by source type

| Source | Documents | Critical TP / support | Legitimate FP / support | Case workload |
|---|---:|---:|---:|---:|
{chr(10).join(source_table_rows)}

## Delayed frozen XGBoost outcomes by scenario

All values below use the unchanged V3 frozen threshold. FPR denominators include legitimate records within the corresponding scenario; the comparison is post-unblinding.

| Scenario | Critical TP / support | Critical recall | Legitimate FP / support | Legitimate FPR | Cases flagged / total | Workload | AP |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(xgb_scenario_rows)}

## Delayed frozen XGBoost outcomes by source

| Source | Critical TP / support | Critical recall | Legitimate FP / support | Legitimate FPR | Cases flagged / total | Workload |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(xgb_source_rows)}

## Frozen baseline comparison after unblinding

| Arm | Critical recall | Legitimate FPR | Case workload | AP |
|---|---:|---:|---:|---:|
{chr(10).join(baseline_rows)}
| Semantic XGBoost | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |

The complete frozen V3 baseline family (CS_V2, Logistic, XGBoost, Deep Sets) was replayed at unchanged artifacts, preprocessing, calibrator and thresholds. The XGBoost replay was delayed until after Generator C labels had already been opened; it is explicitly exploratory and not a fresh blind comparison. The exact `xgboost==3.0.5` environment and protected V3 checkpoint were available, and its replay reproduced all 14 published Generator B aggregate metrics exactly. The separate new Semantic XGBoost arm remains `NOT_EVALUATED`; no model was substituted or retrained. Among the frozen V3 baselines, the best critical recall is 100%; Hybrid is also 100%, so the registered two-point recall-gap criterion meets its point target on this delayed comparison. The full candidate-family comparison remains incomplete because Semantic XGBoost is unavailable.

The delayed frozen V3 XGBoost result is **520/520 critical recall**, but also **6,271/6,271 legitimate false positives**, **1,680/1,680 cases flagged**, AP **0.1396**, Brier **0.9214** and Log Loss **6.9027**. This indicates a severe C operating-point/calibration transfer failure despite perfect observed critical recall. It does not support XGBoost superiority.

## Interpretation

On this synthetic C label set, the frozen Hybrid recorded 520/520 critical detections and 0/2,927 false alerts on the registered C1/C3/C5 endpoint. It also generated 400 false-positive document alerts overall; 160 were in C2, 120 in C6 and 120 in C7. Pairwise deterministic conflict logic flags both records in a conflicting pair because the records alone do not identify which one is wrong. This is a review alert, not a diagnosis that the paired legitimate record is erroneous.

The values are exploratory and construct-dependent. A separate audit found 100 development records whose observable temporal rule indicated critical stale-as-current evidence but whose D1.1 synthetic gold omitted a critical label; those affected training, validation, calibration, and locked test. Also, C's generator thresholds and stale semantics align with rule conditions. This prevents clean causal attribution to learned semantic features and weakens confirmatory external-validity claims.
"""
    write(OUT / "GENERATOR_C_RESULTS.md", results_md)

    grouped = r["boundary_uncertainty"]
    c2 = grouped["by_scenario"]["C2_SAME_PERIOD_CORRUPTION"]
    c4 = grouped["by_scenario"]["C4_TIME_VALIDITY"]
    c6 = grouped["by_scenario"]["C6_TRUE_COMPARABLE_CONFLICT"]
    c7 = grouped["by_scenario"]["C7_HELD_OUT_SOURCE_PAIR"]
    stat_md = f"""# Statistical Audit — Generator C

**Disposition:** observed, post-unblinding, synthetic-only; `EVIDENCE_AI_VALIDATION_BLOCKED`.

## Metric definitions and units

| Metric | Unit and denominator |
|---|---|
| Material defect AP | Document-level precision-recall ranking, 520 positives among 6,791 documents; prevalence-dependent. |
| Critical recall / FNR | Documents labeled critical: TP/(TP+FN), FN/(TP+FN); 520 critical documents. |
| Legitimate-document FPR | Gold legitimate documents: FP/(FP+TN); 6,271 documents. |
| C1/C3/C5 FPR | Gold legitimate records in the registered subgroups: 0 FP / 2,927 records. |
| C4 stale recall | Gold critical stale-as-current records: 120 records. |
| Review workload | Cases with ≥1 flagged record / all 1,680 cases. It is not a document flag rate. |
| Brier | Mean (p-y)^2 over all 6,791 document probabilities. |
| Log loss | Mean binary cross-entropy over the same 6,791 probabilities; clips are inherited from the evaluated probability output. |

Threshold and calibration are frozen from development calibration. AP and proper scoring metrics use continuous predictions; threshold metrics use the released threshold. Results do not include any test-driven threshold change.

## Customer-group bootstrap

The stored 500-draw bootstrap resamples customer groups within the seven registered scenarios (seed `{r['bootstrap']['seed']}`), carrying both cases and all documents from each sampled group. It preserves within-group dependence and produces paired model contrasts. Intervals condition on these fixed generators, labels, fitted models and calibration. They do not include model-training, label-generation, generator-specification, or future institutional uncertainty.

| Hybrid metric | Point | Percentile 95% interval |
|---|---:|---:|
| AP | {fnum(h['material_average_precision'])} | {ci_label(ci['material_average_precision'])} |
| Critical recall | {pct(h['critical_recall'])} | {ci_label(ci['critical_recall'])} |
| Overall legitimate FPR | {pct(h['overall_legitimate_fpr'])} | {ci_label(ci['overall_legitimate_fpr'])} |
| C1/C3/C5 FPR | {pct(h['legitimate_discrepancy_fpr_c1_c3_c5'])} | {ci_label(ci['legitimate_discrepancy_fpr_c1_c3_c5'])} |
| C4 stale recall | {pct(h['c4_stale_as_current_recall'])} | {ci_label(ci['c4_stale_as_current_recall'])} |
| Case workload | {pct(h['case_review_workload'])} | {ci_label(ci['case_review_workload'])} |
| Brier | {fnum(h['brier_score'])} | {ci_label(ci['brier_score'])} |
| Log loss | {fnum(h['log_loss'])} | {ci_label(ci['log_loss'])} |

## Delayed XGBoost baseline uncertainty

The exact frozen V3 XGBoost ensemble was replayed after labels were already open. Its 500-draw scenario-stratified customer-group percentile intervals are descriptive, post-unblinding estimates; they do not restore blinding. Operating-point intervals are degenerate at 100% because every record was flagged in every bootstrap draw.

| Frozen V3 XGBoost metric | Point | 95% group-bootstrap interval |
|---|---:|---:|
| Critical recall | {pct(xgb_metrics['critical_recall'])} | {ci_label(delayed_xgb['grouped_confidence_intervals']['critical_recall'])} |
| Legitimate-document FPR | {pct(xgb_metrics['aggregate_legitimate_fpr'])} | {ci_label(delayed_xgb['grouped_confidence_intervals']['aggregate_legitimate_fpr'])} |
| C1/C3/C5 legitimate FPR | {pct(xgb_metrics['legitimate_discrepancy_fpr'])} | {ci_label(delayed_xgb['grouped_confidence_intervals']['legitimate_discrepancy_fpr'])} |
| C4 stale recall | {pct(xgb_metrics['stale_as_current_recall'])} | {ci_label(delayed_xgb['grouped_confidence_intervals']['stale_as_current_recall'])} |
| Case workload | {pct(xgb_metrics['review_workload'])} | {ci_label(delayed_xgb['grouped_confidence_intervals']['review_workload'])} |
| Material AP | {fnum(xgb_metrics['material_average_precision'])} | {ci_label(delayed_xgb['grouped_confidence_intervals']['material_average_precision'])} |
| Brier | {fnum(xgb_metrics['brier'])} | {ci_label(delayed_xgb['grouped_confidence_intervals']['brier'])} |
| Log loss | {fnum(xgb_metrics['log_loss'])} | {ci_label(delayed_xgb['grouped_confidence_intervals']['log_loss'])} |

## Boundary estimates: zero observed errors are not zero risk

At 100% recall, the bootstrap percentile interval is 100%-100% because every sampled group draw also contains only detected critical records. For a group-level success estimand, exact two-sided Clopper-Pearson intervals are more informative: C2 `{c2['groups_with_all_critical_docs_detected']}/{c2['critical_positive_groups']}` groups had every critical record detected (lower bound {pct(c2['group_success_cp_95']['lower_95'])}); C4 `{c4['groups_with_all_critical_docs_detected']}/{c4['critical_positive_groups']}` (lower {pct(c4['group_success_cp_95']['lower_95'])}); C6 `{c6['groups_with_all_critical_docs_detected']}/{c6['critical_positive_groups']}` (lower {pct(c6['group_success_cp_95']['lower_95'])}); and C7 `{c7['groups_with_all_critical_docs_detected']}/{c7['critical_positive_groups']}` (lower {pct(c7['group_success_cp_95']['lower_95'])}). Each group event is that all critical records in that group were detected. Scenario-specific intervals avoid pretending that C scenarios are exchangeable.

For the C1/C3/C5 subgroup, 0 of {h['legitimate_discrepancy_support_c1_c3_c5']} legitimate documents were false positives, and 0 of {grouped['c1_c3_c5_groups_with_legitimate_records']} independent customer groups had any false-positive record. The pooled one-sided exact 95% upper bound on the **group event incidence** is {pct(grouped['c1_c3_c5_one_sided_95_upper_bound_group_any_fp'])}; it is not a document FPR bound. A conservative one-sided Hoeffding bound for equal-group-weighted document FPR is {pct(grouped['c1_c3_c5_hoeffding_one_sided_95_ucb_equal_group_weighted_fpr'])}. The latter targets an equal-group-weighted rate, not the observed document-weighted ratio. Per-scenario two-sided exact group-event upper bounds are {pct(grouped['by_scenario']['C1_GROSS_NET_PERIODS']['group_any_fp_cp_95_two_sided']['upper_95'])} at 0/120 groups for C1, C3 and C5.

An iid document-level binomial interval would understate uncertainty because documents from one customer group share case context and generator structure. Therefore no independent-document assumption is used for the primary uncertainty interpretation.

## Paired comparisons

Paired group bootstrap contrasts are in `GENERATOR_C_PAIRED_BASELINE_COMPARISONS.csv`; the late XGBoost comparison is also in `data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_PAIRED.csv`. These are post-unblinding descriptive contrasts, not a new model-selection test. Hybrid minus frozen XGBoost legitimate-document FPR is {fnum((delayed_xgb or {}).get('paired_hybrid_contrasts', {}).get('aggregate_legitimate_fpr', {}).get('hybrid_minus_xgboost'))} with interval {ci_label((delayed_xgb or {}).get('paired_hybrid_contrasts', {}).get('aggregate_legitimate_fpr'))}; Hybrid minus XGBoost workload is {fnum((delayed_xgb or {}).get('paired_hybrid_contrasts', {}).get('review_workload', {}).get('hybrid_minus_xgboost'))} with interval {ci_label((delayed_xgb or {}).get('paired_hybrid_contrasts', {}).get('review_workload'))}. The comparison uses the same resampled customer groups and is still conditional on one synthetic challenge.

## Limitations of inference

Finite synthetic scenario frequencies are chosen by construction. Cluster resampling quantifies sampling variation among generated customer groups conditional on those scenario mechanisms; it cannot measure mismatch between synthetic and real financial workflows. Intervals do not account for D1.1 label inconsistency, shared rule/label semantics, or hidden institutional workflows.
"""
    write(OUT / "STATISTICAL_AUDIT.md", stat_md)

    abl_md = f"""# Semantic-Aware Ablation Audit

All C values below come from already frozen predictions and thresholds. This is a post-unblinding descriptive audit. The three registered ablations are Logistic Regression variants; the complete Semantic Hybrid combines deterministic semantic rules with the full Logistic Regression arm. It is not a like-for-like ablation comparator.

| Frozen configuration | Registration | Critical recall | C4 stale recall | Legitimate FPR | C1/C3/C5 FPR | Case workload | AP |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(abl_rows)}
| Semantic Hybrid (rules + full LR) | Registered hybrid | {h['critical_tp']}/{h['critical_support']} ({pct(h['critical_recall'])}) | {h['c4_stale_tp']}/{h['c4_stale_critical_support']} ({pct(h['c4_stale_as_current_recall'])}) | {h['legitimate_fp']}/{h['legitimate_support']} ({pct(h['overall_legitimate_fpr'])}) | {h['legitimate_discrepancy_fp_c1_c3_c5']}/{h['legitimate_discrepancy_support_c1_c3_c5']} ({pct(h['legitimate_discrepancy_fpr_c1_c3_c5'])}) | {h['flagged_case_count']}/{h['case_count']} ({pct(h['case_review_workload'])}) | {fnum(h['material_average_precision'])} |

## Interpretation by feature family

- **Temporal validity:** The complete semantic Logistic arm and `ABLATION_NO_TEMPORAL` both detected 0/120 C4 stale critical records. The Hybrid detected 120/120 because it includes deterministic temporal rules. Thus the statement “removing temporal features reduced stale recall to 0%” is false for the controlled Logistic-vs-Logistic comparison: recall was already 0% in the full LR arm. The Hybrid result cannot isolate temporal feature value from its deterministic rule path.
- **Comparability:** Removing comparability increased LR critical recall from 25/520 (4.81%) to 179/520 (34.42%) at the frozen arm thresholds, while legitimate FPR rose from 56/6,271 (0.89%) to 1,349/6,271 (21.51%) and workload from 81/1,680 (4.82%) to 1,058/1,680 (62.98%). This is a threshold/ranking trade-off, not evidence of improvement from removing semantics.
- **Source/provenance:** Removing source/provenance yields 78/520 critical recall (15.0%), 619/6,271 legitimate FPs (9.87%), and 581/1,680 flagged cases (34.58%). The observed degradation is descriptive and also inherits development-label and calibration limitations.
- **All learned ablations:** D1.1 temporal labels are inconsistent in all model-development partitions: 100 critical stale labels are missing (60 train, 15 validation, 15 calibration, 10 locked test). The selected model and threshold are unchanged; their attribution claims are weakened.

## Feature leakage and rule-target overlap

The observable encoder reads only each record and request context. Code inspection found no reads of canonical truth, gold-label files, scenario labels, customer group IDs as features, event/corruption IDs, or generator-only corruption markers in feature construction. The challenge predictor consumes the frozen observed records and writes predictions before labels open.

However, observable semantic flags include `has_comparable_conflict` and `stale_as_current`, and the deterministic rule thresholds/logic align with the label constructor: both use income/debt/purchase tolerances of VND 500k/250k/500k; the generator creates controlled conflicts around these thresholds; both define critical stale age at 180 days. This is not direct access to hidden gold, but it is construct and rule overlap. C is independent in implementation path, seed, templates, and held-out source pair; it is not independent of the semantic criteria encoded in the rule and labels. That is a generator-dependent shortcut risk and limits external validity.

The C4 rule also evaluates temporal validity on all records, including side-field documents. The semantic rule alone has elevated C4 false positives/workload as shown in the scenario table; the frozen Hybrid's calibrated learned layer changes its operating point. This scoping behavior deserves a new, independently registered test rather than a C-informed code change.
"""
    write(OUT / "ABLATION_REPORT.md", abl_md)

    failure_md = """# Failure Analysis — COBI Evidence V4.1

## Evaluation state

The C predictions and threshold were frozen before labels opened. C labels are now open; all analyses here are post-unblinding exploratory. No tuning or model revision was made with C.

## Generator B mechanisms preserved from the V4 audit

- **B4 stale-as-current:** all 80 critical records were missed by V4 Logistic, XGBoost and Deep Sets at frozen thresholds; CS_V2 missed 34/80. Feature inspection found no explicit effective-period match or asserted-current feature in the frozen V3 contract. This is a feature representation and threshold-transfer failure, not merely an API schema rejection.
- **B5 legitimate discrepancies:** models flagged 1,145–1,198 of 1,199 legitimate records. Large numerical disagreement without semantic comparability was treated as error. Score saturation/overlap means a simple lower cutoff cannot solve this ranking problem.
- **B6 unseen source pair:** CS_V2 and XGBoost missed 106/167 and 95/167 critical records; Logistic and Deep Sets each missed 4/167. For XGBoost, high critical ranking AP with only 72/167 above the frozen threshold indicates a strong operating-point transfer component. These B observations are exploratory diagnostics, not new validation.

## Generator C observed errors and cases

- **Stale evidence:** Hybrid flags 120/120 C4 stale-as-current critical records. The development label audit finding means learned temporal attribution is invalidated; the result is consistent with the deterministic time rule matching the generated label criterion.
- **Legitimate differences:** no false alerts occurred in C1 gross/net and period differences, C3 correction lineage, or C5 different subject/account records (0/2,927). This is a finite synthetic result under rule-aligned semantics.
- **Same-period and genuine conflicts:** the Hybrid raises alerts on both records in a comparable conflicting pair. C2 contributes 160 false-positive companion records; C6 contributes 120. A record-level alert does not establish which source is incorrect. Without an adjudication signal, this is a review signal rather than a per-document defect diagnosis.
- **Held-out payroll+merchant pair:** C7 critical recall is reported by its 120/120 denominator, but C7 also contributes 120 legitimate-document false positives in mixed conflict cases. A held-out pair of known source types is a narrow source-combination challenge, not real-source validation.
- **Rules and thresholds:** `SEMANTIC_RULE` obtains full critical recall but its overall legitimate FPR is 10.38%, higher than the Hybrid's 6.38%; the rule's temporal scoping also flags valid side-field records in C4. The model+rule Hybrid combines rule alerts with calibrated probabilities.
- **Delayed frozen XGBoost baseline:** after C labels were already open, the exact V3 depth-4 ensemble at the unchanged V3 calibration and threshold flagged all 6,791 records. It detected 520/520 critical records but also flagged 6,271/6,271 legitimate records, sending all 1,680 cases to review. AP was 0.1396, Brier 0.9214 and Log Loss 6.9027. This is a severe operating-point/calibration transfer failure on C, not a threshold to retune against C.

## False alerts versus fixed thresholds

Threshold changes cannot be used post hoc to rescue C. V4 B diagnostics already showed that ranking and fixed-threshold effects vary by scenario: B4 learned models failed ranking as well as threshold transfer, B5 score overlap pointed to semantic interpretation/ranking, and B6 XGBoost retained ranking but failed at its operating point. For C, the Hybrid's 400 legitimate false-positive documents are concentrated in the positive conflict scenarios where both conflicting peers are alerted. The registered C1/C3/C5 endpoint has zero observed false alerts. C ablations have different frozen thresholds, so their point differences combine ranking and operating-point changes.

## Construct and shortcut audit

Features contain observed record semantics only; hidden canonical truth and label/corruption fields are absent from the encoder. Nonetheless, the generator and deterministic validator share field tolerances and stale-age semantics. This is target-construct overlap, not direct hidden-label leakage. A truly independent challenge should use independently adjudicated evidence rules, institutions and document workflows, and should freeze criteria before any inspection.

## Failure taxonomy and examples

Examples below are schematic, not copied from hidden Generator C truth:

1. **Valid non-comparable values:** gross monthly salary and net pay, or values covering non-overlapping periods. Values differ; a contradiction is not warranted.
2. **Correction lineage:** an original transaction is marked superseded by a corrected posting. Keeping both for audit is legitimate; the current state should use the correction.
3. **Historical evidence:** an old statement can be valid when matching a historical request; the same statement asserted as current for a later period can be stale.
4. **Comparable conflict:** same subject, account, financial meaning, direction and overlapping period with values beyond the registered tolerance. Both records merit review; additional evidence is needed to identify the erroneous one.
5. **Threshold and review granularity:** pairwise rules can correctly detect a conflict yet still flag a legitimate peer. Document-level false-positive rate and case-level workload answer different questions.

Full prediction-level failure rows and explanation records remain in the preserved C evaluation artifacts. They are not reclassified or tuned here.
"""
    write(OUT / "FAILURE_ANALYSIS.md", failure_md)

    claims = """# Claims and Limitations

## Supported by the current artifacts

- V4's frozen Generator B results document severe synthetic failures in stale evidence (B4), legitimate differences (B5), and source-pair transfer (B6).
- On the already unblinded, registered synthetic Generator C labels, the frozen Semantic Hybrid recorded 520/520 critical detections, 0/2,927 false alerts in C1/C3/C5, 400/6,271 overall legitimate false alerts, 520/1,680 cases flagged, AP 0.5652, Brier 0.03387, and Log Loss 0.09390.
- Group bootstrap intervals and cluster-aware boundary uncertainty are conditional descriptive uncertainty summaries.
- The C1/C3/C5 and C4 result patterns are consistent with semantic and temporal checks being useful in this generator. They do not isolate causal effects.
- Paired, delayed, frozen-output comparisons are available for all four frozen V3 baselines, semantic rule, semantic Logistic, semantic Deep Sets and Hybrid. The semantic XGBoost candidate remains unevaluated.

## Not supported

- “Guaranteed 100% recall,” zero population risk, statistical assurance of no false positives, or safe automated evidence decisions.
- Superiority to all registered candidate models. The frozen V3 XGBoost baseline was replayed after unblinding; the separate Semantic XGBoost research arm remains `NOT_EVALUATED`.
- A causal statement that learned temporal or comparability features produced the Hybrid's results. The D1.1 label mismatch and non-like-for-like hybrid/ablation design prevent it.
- Real financial document accuracy, bank authenticity validation, approval eligibility, regulatory readiness, or generalization to institutions not represented by the generator.
- Measured workload reduction or operational cost savings. Review workload is a synthetic case flag rate, not a time-and-motion study.

## Why the result remains exploratory

Generator C was frozen and scored before label unblinding, and no C-informed tuning was done. However, an after-training audit found that 100 D1.1 stale-as-current critical labels were missing across train, validation, calibration and locked test. Additionally, C's synthetic gold and semantic deterministic checks share financial tolerance and temporal constructs. These issues do not change the frozen C metrics, but weaken attribution and construct independence. The labels and outputs must not be represented as a blind confirmation of the final learned system.

## Required validation before any external claim

Correct and independently audit development labels; pre-register a new challenge with independently specified label adjudication and criteria; evaluate all frozen model families under exact environments; collect privacy-governed, independently reviewed real-document evidence; measure extraction quality, subgroup error, calibration and operational review time; complete legal, security, model-risk and regulatory review. Until then maintain **`EVIDENCE_AI_VALIDATION_BLOCKED`** and keep all research outputs read-only and out of checkout decisions.
"""
    write(OUT / "CLAIMS_AND_LIMITATIONS.md", claims)

    v2v3 = read(ROOT / "reports/evidence-v4/ARTIFACT_MANIFEST.json")
    v4 = read(ROOT / "reports/evidence-v4/final_manifest.json")
    baseline_lines = []
    for sc in scenarios:
        baseline_lines.append(f"| {sc['scenario']} | {sc['documents']} | {sc['critical_tp']}/{sc['critical_support']} | {sc['legitimate_fp']}/{sc['legitimate_support']} | {sc['flagged_case_count']}/{sc['case_count']} |")
    write(OUT / "RECOVERY_AUDIT.md", f"""# Recovery Audit — COBI V4.1

**Project root:** `{ROOT}`. Root exists and is accessible. Existing uncommitted work was preserved; no reset, clean, checkout, or destructive command was used.

## Workspace state

The Git worktree was already dirty before this continuation, including changes across backend, frontend, docs, data and reports. These changes were retained. V4.1 research source and generated artifacts remain under `evidence_ai/` and `reports/evidence-v4.1/`.

## Protected artifacts

- The immutable V2/V3 baseline manifest contains {v2v3['artifact_count']} artifacts; final check: **{protected['v2_v3_verified']}/{protected['v2_v3_expected']}**. Manifest digest: `{protected['v2_v3_manifest_sha256']}`.
- V4 final release manifest lists {protected['v4_expected']} artifacts; final check: **{protected['v4_verified']}/{protected['v4_expected']}**. Manifest digest: `{protected['v4_manifest_sha256']}`. A discrepancy was present at the start of this continuation; it was preserved and not restored or overwritten:
{v4_detail}
- V4 B4/B5/B6 counts were recomputed against 7,744 prediction rows and agree with the pre-change audit; no protected V2-V4 artifact was rewritten.

## Generator C release record

- Generator C groups/cases/documents: {c_manifest['group_count']}/{c_manifest['case_count']}/{c_manifest['document_count']}.
- Prediction file SHA-256: `{sha(DATA / 'C_PREDICTIONS_FROZEN.csv')}`; prediction manifest records the same digest before label access.
- Frozen model manifest SHA-256: `{sha(OUT / 'models/frozen-v1/frozen_model_manifest.json')}`.
- Semantic Hybrid threshold: `{h['frozen_threshold']:.12f}`; no post-C changes.
- Label-access manifest states labels were opened after frozen predictions. This evaluation is therefore post-unblinding, not a fresh blind test.
- Semantic Hybrid aggregate recomputation matches the prior report: `{r['all_previous_aggregate_metrics_match']}`.

## Baseline availability

The exact frozen V3 XGBoost ensemble was recovered from protected V3 artifacts and replayed with the existing `backend/.venv` `xgboost==3.0.5` runtime. Its B replay matched all 14 published aggregate metrics before the delayed C predictions were scored; the C results are explicitly post-unblinding. The frozen V3 baseline family comparison is now complete. The new Semantic XGBoost arm has no frozen artifact and remains `NOT_EVALUATED`; it was not trained or substituted.

## Post-evaluation data-quality finding

The D1.1 audit identified {d1['critical_labels_missing_on_stale_records']} stale-as-current records missing a critical gold label across development partitions (train 60; validation 15; calibration 15; locked test 10). Generator C labels, predictions, thresholds and source artifacts have not been changed. This finding makes temporal feature attribution exploratory and weakens confirmatory claims.

## Artifact disposition

No V2, V3, or V4 baseline artifact was replaced. A stale unverified XGBoost joblib was isolated under `archive/unavailable-artifacts/` and was not used. Current detailed reconciliation is in `GENERATOR_C_RESULTS.md`; final checksums and command results are in `FINAL_MANIFEST.json` and `VERIFICATION_LOG.md`.
""")

    write(OUT / "UPDATED_DATASET_AND_SPLIT_MANIFESTS.md", f"""# Updated Dataset and Split Manifest Index

This index documents existing manifests and their integrity; it does not rewrite their data.

| Artifact | Role | SHA-256 |
|---|---|---|
| `experiment_protocol_c.json` | Registered Generator C mechanism, scenarios, seeds, metrics and acceptance rules | `{sha(OUT / 'experiment_protocol_c.json')}` |
| `data/development-d1.1/dataset_manifest.json` | Permitted D1.1 training/validation/calibration/locked-test source | `{sha(OUT / 'data/development-d1.1/dataset_manifest.json')}` |
| `data/generator-c-v1/dataset_manifest.json` | C group/case/document and scenario manifest | `{sha(DATA / 'dataset_manifest.json')}` |
| `data/generator-c-v1/C_PREDICTION_MANIFEST.json` | Prediction hashes frozen before label access | `{sha(DATA / 'C_PREDICTION_MANIFEST.json')}` |
| `data/generator-c-v1/C_EVALUATION_MANIFEST.json` | Label-opening and evaluation artifact hashes | `{sha(DATA / 'C_EVALUATION_MANIFEST.json')}` |
| `models/frozen-v1/frozen_model_manifest.json` | Frozen model identities, features, thresholds and artifact references | `{sha(OUT / 'models/frozen-v1/frozen_model_manifest.json')}` |

Generator C partitions 840 groups equally across seven registered scenarios (120 groups each), with two cases per group. The two cases and all documents remain clustered by customer group for uncertainty resampling. The payroll+merchant source pair is excluded from D1.1 and used in C7. C labels are open; the existing split remains valid as a frozen split, but C is not a newly blind test.

**Split-quality qualification:** D1.1's four disjoint partitions are documented in the source split manifests. Post-evaluation semantic audit found 100 critical-label omissions in stale records across every partition. Split disjointness does not cure label inconsistency. No relabeling, retraining, recalibration, or retuning is done here.
""")

    write(OUT / "REPRODUCTION.md", """# Reproduction and Artifact Replay

## Scope

This package reconciles an existing frozen Generator C run. It does not retrain, recalibrate, alter rule conditions, or choose thresholds. Generator C labels are already open, so reproductions are post-unblinding and exploratory.

## Reconcile metrics

From project root using the existing COBI Python environment:

```powershell
python -m evidence_ai.v4_1_reconcile_c
```

The reconciliation verifies frozen prediction hashes, recalculates all observed model predictions, grouped intervals and paired descriptive contrasts, and checks prior aggregate metrics. Do not run the one-time evaluator `python -m evidence_ai.v4_1_evaluate_c` again; its guard records the existing label access. Do not run training, calibration or model selection to update this release.

## Verify frozen model replay

```powershell
python -m evidence_ai.v4_1_replay
```

The replay checks exact released artifact hashes and compares predictions on the locked development partition. It does not consume C labels.

## Delayed frozen V3 XGBoost replay

The XGBoost prediction stage scores C observed records only. C labels were already open before this delayed evaluation, so its outputs are exploratory rather than blind confirmation. The script checks the exact protected depth-4 checkpoint, V3 preprocessing, calibrator, threshold and `xgboost==3.0.5`; it also compares all 14 aggregate B replay metrics against the preserved V4 report.

```powershell
backend/.venv/Scripts/python.exe -m evidence_ai.v4_1_delayed_xgb predict
backend/.venv/Scripts/python.exe -m evidence_ai.v4_1_delayed_xgb evaluate
```

The first command writes and hashes a separate prediction file without reading C labels. The second reads the already-open labels and writes delayed metrics and paired group-bootstrap comparisons. It does not overwrite `C_PREDICTIONS_FROZEN.csv` or change any model or threshold. Semantic XGBoost remains `NOT_EVALUATED` because no trained frozen artifact exists.

## Rebuild documents and charts

```powershell
python -m evidence_ai.v4_1_finalize
```

This writes the scientific reports, CSV/SVG/PNG pitch charts and a read-only research release manifest from reconciled outputs. It does not fit or select a model. The final integrity manifest is written after verification commands; see `FINAL_MANIFEST.json`.

## Known blockers

- Frozen V3 XGBoost is replayable with the existing backend virtual environment but was evaluated only after C unblinding. The separate Semantic XGBoost arm remains `NOT_EVALUATED`.
- D1.1 contains 100 missing critical labels among records flagged as critical stale by the temporal rule. Do not repair labels after viewing C and call the result confirmatory.
- HTTP TestClient may be blocked by the Windows sandbox asyncio socketpair restriction; report that as `BLOCKED` if it occurs. A direct route call is not an HTTP test.
- Real-document validation is unavailable. Keep `EVIDENCE_AI_VALIDATION_BLOCKED`.

Exact environment versions, test commands, exit codes, hashes and any blockers are recorded in `VERIFICATION_LOG.md`.
""")

    write(OUT / "RESULTS.md", """# COBI V4.1 Results

## Disposition

V4.1 has a completed frozen-output reconciliation on the already opened synthetic Generator C labels. It is a **partial, post-unblinding exploratory evaluation**, not a fresh blind confirmatory test. All research outputs remain read-only and `EVIDENCE_AI_VALIDATION_BLOCKED`.

## Main observed C measurements

Semantic Hybrid: 520/520 critical recall (100%); 0/2,927 C1/C3/C5 legitimate-document false positives (0%); 400/6,271 overall legitimate-document false positives (6.38%); 520/1,680 case review workload (30.95%); material-defect AP 0.5652; Brier 0.03387; Log Loss 0.09390. C4 stale-as-current recall is 120/120 (100%). See [`GENERATOR_C_RESULTS.md`](GENERATOR_C_RESULTS.md) for all denominators, scenario results, CIs and delayed baseline comparisons.

## Interpretation controls

The D1.1 development split has 100 critical temporal-label omissions across train, validation, calibration and locked test. The Hybrid's full recall is materially supported by deterministic rules; C's label constructs share thresholds and stale semantics with those rules. Therefore the observed results do not demonstrate a causal learned-feature improvement. The controlled Logistic ablations show no C4 stale recall in either the full Logistic model or its no-temporal variant.

The four frozen V3 baselines are now present in the delayed C comparison. Each recorded 100% observed critical recall, but frozen V3 XGBoost also flagged every legitimate document and every case. Semantic XGBoost remains `NOT_EVALUATED`, so the candidate-family comparison is incomplete. No all-candidate superiority, real banking accuracy, measured operational savings, or regulatory validation is claimed.

The scientific answer is **suggestive but inconclusive**: the Hybrid and frozen V3 baselines share 100% observed critical recall, while Hybrid has lower legitimate FPR and workload than the delayed XGBoost replay on this inspected synthetic C set. The XGBoost replay was post-unblinding, and label inconsistency, rule-target overlap, and the unevaluated Semantic XGBoost candidate prevent a complete candidate-family or confirmatory generalization claim. Maintain `EVIDENCE_AI_VALIDATION_BLOCKED`.
""")

    write(OUT / "PAPER_DRAFT.md", """# Semantic-Aware Financial Evidence Validation under Synthetic Distribution Shift

## Abstract

Financial evidence systems can confuse numerically different but semantically incomparable records and can fail to distinguish evidence that is historically applicable from evidence improperly asserted as current. We examined a semantic representation containing subject/account, field meaning, effective period, source provenance, units, gross/net basis, transaction direction, correction lineage, verification, missingness and uncertainty. A three-valued comparator emits COMPARABLE, NOT_COMPARABLE or UNKNOWN, while temporal validation relates evidence periods to the request. After V4 frozen models showed severe synthetic Generator B failures in stale evidence, legitimate discrepancies and source-pair transfer, a new development procedure and independently implemented synthetic Generator C were registered. Generator C predictions were frozen before labels opened. Post-unblinding reconciliation of the frozen Semantic Hybrid produced 100% observed critical recall (520/520), 0% false-positive rate on the registered C1/C3/C5 endpoint (0/2,927), 6.38% overall legitimate-document FPR, 30.95% case workload, AP 0.5652, Brier 0.03387 and Log Loss 0.09390. A delayed replay of the exact frozen V3 XGBoost baseline after label unblinding also detected 520/520 critical records but flagged all 6,271 legitimate records and all cases; AP was 0.1396, Brier 0.9214 and Log Loss 6.9027. An audit found 100 missing critical stale labels in development partitions; deterministic rules also share tolerance and stale criteria with the synthetic gold; and the new Semantic XGBoost arm remains unevaluated. These results are exploratory and do not confirm causal improvement or external validity. No banking validation is available.

## 1. Introduction

V3 synthetic test results suggested useful evidence-defect ranking, but an independent Generator B exposed inconsistent transfer. In B4, frozen Logistic, XGBoost and Deep Sets missed all 80 critical stale-as-current documents. In B5, each flagged most legitimate differences. B6 revealed model-specific weakness on source combinations. V4.1 asks whether explicit financial semantics and time-aware evidence validity can better separate material defects from valid discrepancies.

## 2. Representation and decision logic

Each evidence record stores subject and account references; field and financial meaning; original and normalized value/unit; effective period; source and provenance; gross/net basis; direction; correction state; verification; missingness; uncertainty; observed date and asserted-current state. Pairwise comparability is three-valued. Different subject/account, meaning, basis, direction, or correction lineage can make records non-comparable; missing or uncertain information yields UNKNOWN. Contradictions require comparable facts, overlapping periods and a material difference. Temporal validity treats historical records matching the request as relevant and marks records as stale-as-current only when a current assertion conflicts with the requested effective period. Exact formal rules and tolerances are in `SEMANTIC_EVIDENCE_SCHEMA.md`.

## 3. Methods

Development generator D1.1 supplied train/validation/calibration/locked test partitions by customer group. Candidate families included frozen V4 baselines, deterministic semantic rules, semantic Logistic Regression, semantic Deep Sets, Hybrid rules plus Logistic Regression, and three Logistic feature ablations. Hyperparameters were selected on validation, calibration and thresholds used a separate calibration partition, and C was generated with seed 2026110802 under protocol `cobi-evidence-v4.1-c1.0`. The 840-group, 1,680-case, 6,791-document challenge had seven registered scenarios, including gross/net periods, corrections, temporal validity, non-comparable accounts, genuine conflicts and a held-out payroll+merchant source pair. C's prediction digest was frozen before labels opened. All C analyses reported here are post-unblinding and made no model changes.

## 4. Results

On C, the frozen Semantic Hybrid recorded 520/520 critical recalls and 0/2,927 legitimate false positives in C1/C3/C5; overall it made 400/6,271 legitimate-document false alerts. It flagged 520/1,680 cases. AP was 0.5652, Brier 0.03387 and Log Loss 0.09390. A delayed, post-unblinding frozen V3 XGBoost replay also detected 520/520 critical records but flagged all 6,271 legitimate records and all 1,680 cases; its AP was 0.1396, Brier 0.9214 and Log Loss 6.9027. Group-stratified 500-draw percentile intervals and paired contrasts are reported in `STATISTICAL_AUDIT.md`. The 400 false-positive records arose in mixed comparable-conflict cases; the pair rule flags both members and cannot determine the erroneous source without adjudication.

## 5. Ablation and integrity audit

The full Logistic Regression and no-temporal Logistic ablation both had 0/120 C4 recall. The no-comparability arm had higher critical recall than full LR but a 21.51% legitimate FPR and 62.98% case workload. Hybrid is not a matched feature ablation because it adds deterministic rules.

A post-evaluation label audit found 100 records in D4 for which observable temporal rules marked critical stale-as-current while development gold omitted a critical label: 60 train, 15 validation, 15 calibration and 10 locked test. This does not alter frozen C predictions but weakens learned-feature attribution. Feature code does not read hidden canonical truth, labels, group/scenario identifiers or corruption ids. However, rule conditions and C gold use matching tolerances and 180-day stale criterion, creating target-construct overlap and shortcut risk.

## 6. Limitations

All data and labels are generated; record semantics are structured inputs, so this does not measure document parsing or authenticity. Scenarios, sources and mechanisms are finite. C labels were opened and the study is now exploratory. The frozen V3 XGBoost baseline was evaluated late after unblinding and cannot be described as a fresh blind comparison. The separate Semantic XGBoost candidate remains `NOT_EVALUATED`, so candidate-family comparison is incomplete. Cluster intervals condition on the fixed generation processes and do not quantify generator misspecification. No external or banking validation, measured savings, authorization, or regulatory assessment exists.

## 7. Conclusion

The measured pattern is consistent with semantic/time-aware checks reducing selected kinds of synthetic false alerts while detecting generated critical defects. But the development label inconsistency and rule/gold overlap preclude a confirmatory causal claim. The final research question remains open. A corrected independent development pipeline and a newly registered, independently adjudicated challenge are needed before stronger claims.
""")

    write(OUT / "ENGLISH_PITCH_EVIDENCE_SUMMARY.md", """# Experimental Evidence — Semantic-Aware Financial Validation

## From fixed scoring to context-aware evidence checks

Frozen models evaluated on independent synthetic Generator B missed all 80 B4 stale-as-current critical records in the learned branches and flagged 1,145–1,198 of 1,199 legitimate B5 records. This motivated explicit semantic comparability and time-validity checks.

## Generator C — measured frozen-output results

After prediction freeze and subsequent label opening, the Semantic Hybrid recorded **520/520 critical detections (100%)**, **0/2,927 C1/C3/C5 legitimate false alerts**, **400/6,271 overall legitimate false alerts (6.38%)**, **520/1,680 cases flagged (31.0%)**, AP **0.5652**, Brier **0.0339**, and Log Loss **0.0939**. C4 stale-as-current recall was 120/120. A later frozen V3 XGBoost replay, explicitly post-unblinding, recorded 520/520 critical detections but 6,271/6,271 legitimate false alerts and 1,680/1,680 cases flagged; its AP was 0.1396, Brier 0.9214 and Log Loss 6.9027. These are synthetic observed results with grouped uncertainty; they do not imply zero population risk.

## Scientific qualification

The labels are open, so this is post-unblinding exploratory analysis. A development audit found 100 missing critical stale labels across training, validation, calibration and locked-test partitions. The full Logistic model and no-temporal ablation both had 0% C4 recall; the Hybrid combines rules and Logistic Regression. Therefore temporal-feature causality is not established. Comparability ablation results also combine separate frozen thresholds and a different model family from Hybrid.

The four frozen V3 baselines are now compared using unchanged artifacts and thresholds, but this XGBoost evaluation occurred after unblinding. The separate Semantic XGBoost research arm remains **NOT_EVALUATED**, so comparison across all new candidate families is incomplete. All results are synthetic; real financial-document validation, bank performance, regulatory readiness and measured operational savings remain unvalidated.

**Status:** `EVIDENCE_AI_VALIDATION_BLOCKED`.
""")
    write(OUT / "PITCH_EVIDENCE_SUMMARY.md", (OUT / "ENGLISH_PITCH_EVIDENCE_SUMMARY.md").read_text(encoding="utf-8"))

    write(PITCH / "SLIDE_READY_ENGLISH.md", """# Slide-ready evidence

## Semantic-aware financial evidence checks — synthetic study

**Generator C · frozen predictions · labels now open · exploratory**

| Measure | Observed result |
|---|---:|
| Critical recall | 520 / 520 · 100% |
| C1/C3/C5 legitimate-discrepancy false alerts | 0 / 2,927 · 0% |
| Overall legitimate-document FPR | 400 / 6,271 · 6.38% |
| Case review workload | 520 / 1,680 · 31.0% |
| Material-defect AP | 0.565 |
| Brier / Log Loss | 0.0339 / 0.0939 |

**Ablation caveat:** the full Logistic Regression and no-temporal variant both had 0/120 stale recall; the Hybrid's 120/120 result includes deterministic rules. No causal feature effect is established.

**Baseline note:** frozen V3 XGBoost was evaluated after label unblinding and flagged all legitimate C records; the new Semantic XGBoost arm remains `NOT_EVALUATED`. Development stale-label inconsistency found. No real-bank validation or measured operational savings. `EVIDENCE_AI_VALIDATION_BLOCKED`.

*Method note: document metrics use frozen thresholds and customer-group bootstrap; workload is case-level. Generator C differs from V3 and V4 challenge distributions.*
""")
    write(PITCH / "PITCH_EVIDENCE_SUMMARY.md", (OUT / "ENGLISH_PITCH_EVIDENCE_SUMMARY.md").read_text(encoding="utf-8"))
    write(PITCH / "SPEAKER_SCRIPT_EN.md", """# Speaker script — 60 to 75 seconds

“COBI’s V4 test exposed a specific weakness: fixed evidence scores treated valid financial differences as errors and missed stale documents presented as current. V4.1 adds subject, account, financial meaning, reporting period, gross or net basis, correction lineage and temporal-validity information.

“On the already opened synthetic Generator C labels, the frozen Semantic Hybrid flagged all 520 labeled critical records. It produced no false alerts among 2,927 legitimate documents in the registered gross/net, correction and non-comparable account scenarios. Across all scenarios, 400 of 6,271 legitimate documents were still flagged, and 31 percent of cases entered review. Its average precision was 0.565, Brier score 0.0339 and log loss 0.0939.

"These are measured synthetic results, not a fresh blind confirmation. Our audit found 100 missing critical stale labels in development partitions. The Hybrid includes deterministic rules, and the full Logistic model and no-temporal ablation both had zero stale recall, so we cannot claim a causal benefit from learned temporal features. We later replayed the exact frozen V3 XGBoost baseline after unblinding: it detected all critical records but flagged every legitimate record and every case. The new Semantic XGBoost candidate remains unevaluated. Real banking evidence has not been tested. Generalization remains unvalidated, and research output remains blocked from checkout decisions."
""")
    write(PITCH / "JUDGE_QA.md", """# Judge Q&A — Evidence AI V4.1

### What did you measure?

We measured frozen document-level probabilities and case-level flag workload against programmatic labels on 6,791 synthetic documents clustered into 840 customer groups. The labels were opened after prediction freeze, but are open now; the current analysis is post-unblinding.

### What does 100% recall mean?

It means 520 of 520 synthetic labeled critical documents were flagged at the frozen operating threshold in this C sample. It is not a guarantee. A group bootstrap is degenerate at 100% here, so we also report exact group-level bounds by scenario; those have lower limits below 100%.

### Did the temporal ablation prove temporal features matter?

No. Full Logistic Regression and the no-temporal Logistic variant both detected 0 of 120 C4 stale critical documents. The Hybrid's 120/120 result includes deterministic rules. The D1.1 development data also omitted critical labels for 100 stale records across all partitions, weakening temporal attribution.

### Why is the subgroup FPR zero but the overall FPR 6.38%?

The zero endpoint covers C1, C3 and C5 only: 0/2,927 legitimate records. Overall, 400/6,271 legitimate records were flagged, concentrated in mixed same-period or genuine conflict scenarios where the pairwise rule alerts both records but cannot identify the wrong source.

### Is the Generator C data independent?

The implementation, seed, templates and held-out source pair differ from the earlier generators. But the C gold labels and deterministic checks share financial tolerance and stale-age constructs. That creates rule-target overlap, so the result is not fully independent at the semantic-criterion level.

### Did Semantic Hybrid beat all frozen baselines?

Not established across the full candidate family. All four frozen V3 baselines were replayed without changes; XGBoost was a delayed post-unblinding replay and recorded 100% critical recall but 100% legitimate FPR and 100% case workload. The separate Semantic XGBoost arm remains `NOT_EVALUATED`. No superiority to all candidate models is claimed.

### Are the results bank-ready or operational savings?

No. They are synthetic research metrics. There is no real bank evidence validation, regulatory review, measured time savings or authorization for lending decisions. Checkout use remains `EVIDENCE_AI_VALIDATION_BLOCKED`.

### What is the next valid research step?

Repair and independently audit development labels, pre-register a new challenge with separately specified semantic labels, replay every baseline using the exact environment, and obtain privacy-governed independently adjudicated real-document evidence before making external claims.
""")

    # Flat source files for data reviewers; exact grouped CSVs remain canonical.
    make_csv(PITCH / "figure1_generator_c_performance.csv", [
        {"metric": "Critical recall", "numerator": "520", "denominator": "520", "value": h["critical_recall"], "ci95_low": ci["critical_recall"]["lower_95"], "ci95_high": ci["critical_recall"]["upper_95"], "unit": "document fraction"},
        {"metric": "Overall legitimate FPR", "numerator": "400", "denominator": "6271", "value": h["overall_legitimate_fpr"], "ci95_low": ci["overall_legitimate_fpr"]["lower_95"], "ci95_high": ci["overall_legitimate_fpr"]["upper_95"], "unit": "document fraction"},
        {"metric": "C1/C3/C5 legitimate FPR", "numerator": "0", "denominator": "2927", "value": h["legitimate_discrepancy_fpr_c1_c3_c5"], "ci95_low": ci["legitimate_discrepancy_fpr_c1_c3_c5"]["lower_95"], "ci95_high": ci["legitimate_discrepancy_fpr_c1_c3_c5"]["upper_95"], "unit": "document fraction"},
        {"metric": "C4 stale recall", "numerator": "120", "denominator": "120", "value": h["c4_stale_as_current_recall"], "ci95_low": ci["c4_stale_as_current_recall"]["lower_95"], "ci95_high": ci["c4_stale_as_current_recall"]["upper_95"], "unit": "document fraction"},
        {"metric": "Case review workload", "numerator": "520", "denominator": "1680", "value": h["case_review_workload"], "ci95_low": ci["case_review_workload"]["lower_95"], "ci95_high": ci["case_review_workload"]["upper_95"], "unit": "case fraction"},
        {"metric": "Material-defect AP", "numerator": "520 positives", "denominator": "6791 documents", "value": h["material_average_precision"], "ci95_low": ci["material_average_precision"]["lower_95"], "ci95_high": ci["material_average_precision"]["upper_95"], "unit": "unitless"},
        {"metric": "Brier score", "numerator": "mean squared error", "denominator": "6791", "value": h["brier_score"], "ci95_low": ci["brier_score"]["lower_95"], "ci95_high": ci["brier_score"]["upper_95"], "unit": "unitless"},
        {"metric": "Log loss", "numerator": "mean binary cross-entropy", "denominator": "6791", "value": h["log_loss"], "ci95_low": ci["log_loss"]["lower_95"], "ci95_high": ci["log_loss"]["upper_95"], "unit": "nats per document"},
    ])

    # Figure 2 only compares frozen Logistic-family ablations to the full LR;
    # the Hybrid is included as a separate contextual reference.
    figure2_rows = []
    fig2_models = ["SEMANTIC_HYBRID", "SEMANTIC_LOGISTIC", "ABLATION_NO_TEMPORAL", "ABLATION_NO_COMPARABILITY", "ABLATION_NO_SOURCE_PROVENANCE"]
    for model in fig2_models:
        m = agg[model]
        figure2_rows.append({"model": model, "model_family": "hybrid rules + LR" if model == "SEMANTIC_HYBRID" else "semantic Logistic Regression", "critical_recall": m["critical_recall"], "c4_stale_recall": m["c4_stale_as_current_recall"], "overall_legitimate_fpr": m["overall_legitimate_fpr"], "case_review_workload": m["case_review_workload"], "threshold": m["frozen_threshold"], "status": "frozen post-unblinding descriptive comparison"})
    make_csv(PITCH / "figure2_semantic_ablation.csv", figure2_rows)

    progression = [
        {"phase": "V3", "generator": "Original synthetic generator", "result": "Deep Sets: 91.0% critical recall; AP 0.9269; 96 test groups", "status": "Original synthetic evidence; not equivalent to B/C"},
        {"phase": "V4", "generator": "Independent Generator B", "result": "B4: learned models missed 80/80 critical stale docs; B5: 95.5–99.4% legitimate FPR for learned models", "status": "Independent-generator generalization failures"},
        {"phase": "V4.1", "generator": "Registered Generator C", "result": "Hybrid: 520/520 critical; 0/2,927 C1/C3/C5 FP; 400/6,271 overall FP; XGBoost incomplete", "status": "Measured after label opening; exploratory"},
    ]
    make_csv(PITCH / "figure3_research_progression.csv", progression)

    make_charts(r, figure2_rows, progression)
    # Small signed read-only API release descriptor. The API independently checks
    # these hashes and exposes only curated metrics, never gold/truth data.
    release = {
        "release_id": "cobi-evidence-v4.1-research-summary-v1",
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
        "status": "POST_UNBLINDING_EXPLORATORY",
        "read_only": True,
        "routing_authorized": False,
        "approval_authorized": False,
        "metrics_sha256": sha(METRICS_PATH),
        "prediction_sha256": sha(DATA / "C_PREDICTIONS_FROZEN.csv"),
        "model_manifest_sha256": sha(OUT / "models/frozen-v1/frozen_model_manifest.json"),
    }
    write(OUT / "RESEARCH_RELEASE.json", json.dumps(release, indent=2))


def _font(size, bold=False):
    candidates = [r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


BG = "#F6F5EF"
INK = "#193B34"
MUTED = "#547168"
GREEN = "#2C7868"
GOLD = "#D0B77C"
RED = "#C46D57"
PALE = "#E7EFE8"
WHITE = "#FFFFFF"


def _wrap(draw, text, font, width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), test, font=font)[2] <= width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_text(draw, x, y, text, font, fill, width=None, gap=7):
    if width is None:
        draw.text((x, y), text, font=font, fill=fill)
        return y + font.size + gap
    for line in _wrap(draw, text, font, width):
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + gap
    return y


def _save(svg_body, png_draw, name, width=1800, height=1050, foot="SYNTHETIC · POST-UNBLINDING EXPLORATORY · EVIDENCE_AI_VALIDATION_BLOCKED"):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="{BG}"/>{svg_body}
<text x="72" y="{height-32}" fill="{MUTED}" font-family="Arial,sans-serif" font-size="19">{html.escape(foot)}</text></svg>'''
    FIGURES.mkdir(parents=True, exist_ok=True)
    (FIGURES / f"{name}.svg").write_text(svg, encoding="utf-8")
    im = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(im)
    png_draw(draw, width, height)
    draw.text((72, height - 36), foot, font=_font(15), fill=MUTED)
    im.save(FIGURES / f"{name}.png", format="PNG", dpi=(300, 300), optimize=True)


def make_charts(r, abl, progression):
    h = r["aggregate_metrics"]["SEMANTIC_HYBRID"]
    ci = r["bootstrap"]["intervals_by_model"]["SEMANTIC_HYBRID"]
    W, H = 1800, 1050
    title_font, subtitle_font, label_font, small_font, value_font = _font(44, True), _font(22), _font(21, True), _font(17), _font(24, True)
    # Figure 1: document/case fractions plus probability metrics on separate card scales.
    metrics = [
        ("Critical defect recall", h["critical_recall"], ci["critical_recall"], "520 / 520 documents", GREEN),
        ("Overall legitimate-document FPR", h["overall_legitimate_fpr"], ci["overall_legitimate_fpr"], "400 / 6,271 documents", RED),
        ("C1/C3/C5 legitimate FPR", h["legitimate_discrepancy_fpr_c1_c3_c5"], ci["legitimate_discrepancy_fpr_c1_c3_c5"], "0 / 2,927 documents", GREEN),
        ("Case review workload", h["case_review_workload"], ci["case_review_workload"], "520 / 1,680 cases", GOLD),
    ]
    body = [f'<text x="72" y="82" fill="{INK}" font-family="Arial" font-weight="700" font-size="44">Generator C performance — Semantic Hybrid</text>',
            f'<text x="72" y="124" fill="{MUTED}" font-family="Arial" font-size="22">Frozen threshold {h["frozen_threshold"]:.6f} · 840 groups · 1,680 cases · 6,791 documents</text>']
    for i, (label, val, ci_val, support, color) in enumerate(metrics):
        y = 220 + i * 155
        bar_x, bar_w = 520, 780
        body += [f'<text x="72" y="{y+13}" fill="{INK}" font-family="Arial" font-weight="700" font-size="23">{html.escape(label)}</text>',
                 f'<text x="72" y="{y+48}" fill="{MUTED}" font-family="Arial" font-size="18">{support}</text>',
                 f'<rect x="{bar_x}" y="{y-14}" width="{bar_w}" height="30" rx="5" fill="#E3E8DF"/>',
                 f'<rect x="{bar_x}" y="{y-14}" width="{bar_w*val:.1f}" height="30" rx="5" fill="{color}"/>',
                 f'<text x="{bar_x+bar_w+24}" y="{y+11}" fill="{INK}" font-family="Arial" font-weight="700" font-size="25">{pct(val)}</text>',
                 f'<text x="{bar_x}" y="{y+47}" fill="{MUTED}" font-family="Arial" font-size="16">Group-bootstrap 95% interval: {pct(ci_val["lower_95"])} to {pct(ci_val["upper_95"])}</text>']
    body += [f'<rect x="1390" y="180" width="330" height="610" rx="12" fill="{WHITE}" stroke="#D4DDD4"/>',
             f'<text x="1425" y="235" fill="{INK}" font-family="Arial" font-weight="700" font-size="24">Probability quality</text>',
             f'<text x="1425" y="310" fill="{MUTED}" font-family="Arial" font-size="18">Material-defect AP</text>',
             f'<text x="1425" y="350" fill="{INK}" font-family="Arial" font-weight="700" font-size="32">{h["material_average_precision"]:.3f}</text>',
             f'<text x="1425" y="380" fill="{MUTED}" font-family="Arial" font-size="16">95% CI {ci["material_average_precision"]["lower_95"]:.3f}–{ci["material_average_precision"]["upper_95"]:.3f}</text>',
             f'<text x="1425" y="465" fill="{MUTED}" font-family="Arial" font-size="18">Brier score</text>',
             f'<text x="1425" y="505" fill="{INK}" font-family="Arial" font-weight="700" font-size="32">{h["brier_score"]:.4f}</text>',
             f'<text x="1425" y="535" fill="{MUTED}" font-family="Arial" font-size="16">95% CI {ci["brier_score"]["lower_95"]:.4f}–{ci["brier_score"]["upper_95"]:.4f}</text>',
             f'<text x="1425" y="620" fill="{MUTED}" font-family="Arial" font-size="18">Log loss</text>',
             f'<text x="1425" y="660" fill="{INK}" font-family="Arial" font-weight="700" font-size="32">{h["log_loss"]:.4f}</text>',
             f'<text x="1425" y="690" fill="{MUTED}" font-family="Arial" font-size="16">95% CI {ci["log_loss"]["lower_95"]:.4f}–{ci["log_loss"]["upper_95"]:.4f}</text>',
             f'<text x="72" y="890" fill="{MUTED}" font-family="Arial" font-size="17">Bars use 0–100% scales. Workload is case-level; other bars are document-level. Boundary bootstrap intervals can be degenerate and do not imply zero population risk.</text>']
    def draw1(d, w, hgt):
        d.text((72, 45), "Generator C performance — Semantic Hybrid", font=title_font, fill=INK)
        d.text((72, 98), f"Frozen threshold {h['frozen_threshold']:.6f} · 840 groups · 1,680 cases · 6,791 documents", font=subtitle_font, fill=MUTED)
        for i,(label,val,ci_val,support,color) in enumerate(metrics):
            y=220+i*155
            d.text((72,y-22), label, font=label_font, fill=INK); d.text((72,y+15),support,font=small_font,fill=MUTED)
            d.rounded_rectangle((520,y-35,1300,y-5),radius=5,fill="#E3E8DF")
            d.rounded_rectangle((520,y-35,520+780*val,y-5),radius=5,fill=color)
            d.text((1325,y-29),pct(val),font=value_font,fill=INK)
            d.text((520,y+20),f"Group-bootstrap 95% interval: {pct(ci_val['lower_95'])} to {pct(ci_val['upper_95'])}",font=small_font,fill=MUTED)
        d.rounded_rectangle((1390,180,1720,790),radius=12,fill=WHITE,outline="#D4DDD4",width=2)
        d.text((1425,205),"Probability quality",font=label_font,fill=INK)
        for y,label,val,ci_key in [(290,"Material-defect AP",h['material_average_precision'],'material_average_precision'),(445,"Brier score",h['brier_score'],'brier_score'),(600,"Log loss",h['log_loss'],'log_loss')]:
            d.text((1425,y),label,font=small_font,fill=MUTED); d.text((1425,y+32),f"{val:.4f}",font=_font(30,True),fill=INK)
            iv=ci[ci_key]; d.text((1425,y+69),f"95% CI {iv['lower_95']:.4f}–{iv['upper_95']:.4f}",font=_font(14),fill=MUTED)
        d.text((72,890),"Bars use 0–100% scales. Workload is case-level; other bars are document-level.",font=small_font,fill=MUTED)
        d.text((72,920),"Boundary bootstrap intervals can be degenerate; they do not imply zero population risk.",font=small_font,fill=MUTED)
    _save("".join(body), draw1, "figure1_generator_c_performance")

    # Figure 2: exact tasks across frozen Logistic variants; Hybrid is contextual only.
    model_short = {"SEMANTIC_HYBRID":"Hybrid (rules + LR)","SEMANTIC_LOGISTIC":"Full semantic LR","ABLATION_NO_TEMPORAL":"Without temporal","ABLATION_NO_COMPARABILITY":"Without comparability","ABLATION_NO_SOURCE_PROVENANCE":"Without source/provenance"}
    fig2_models = ["SEMANTIC_HYBRID", "SEMANTIC_LOGISTIC", "ABLATION_NO_TEMPORAL", "ABLATION_NO_COMPARABILITY", "ABLATION_NO_SOURCE_PROVENANCE"]
    series = [
        ("Critical document recall", "critical_recall", GREEN),
        ("C4 stale-as-current document recall", "c4_stale_recall", RED),
        ("Legitimate-document FPR", "overall_legitimate_fpr", GOLD),
        ("Case review workload", "case_review_workload", "#6C86A0"),
    ]
    vals = {row["model"]: row for row in abl}
    body = [f'<text x="72" y="82" fill="{INK}" font-family="Arial" font-weight="700" font-size="44">Semantic feature ablation — frozen Generator C outputs</text>',
            f'<text x="72" y="124" fill="{MUTED}" font-family="Arial" font-size="22">Ablations are Logistic Regression variants; Hybrid is a contextual, non-like-for-like reference.</text>']
    for j,(label,key,color) in enumerate(series):
        px=72+(j%2)*850; py=195+(j//2)*370
        body += [f'<rect x="{px}" y="{py}" width="800" height="330" rx="10" fill="{WHITE}" stroke="#D4DDD4"/>',
                 f'<text x="{px+24}" y="{py+40}" fill="{INK}" font-family="Arial" font-weight="700" font-size="22">{html.escape(label)}</text>']
        for i,m in enumerate(fig2_models):
            row=vals[m]
            value = row["c4_stale_recall"] if key=="c4_stale_recall" else row[key]
            y=py+89+i*42
            body += [f'<text x="{px+22}" y="{y+6}" fill="{MUTED}" font-family="Arial" font-size="16">{html.escape(model_short[m])}</text>',
                     f'<rect x="{px+260}" y="{y-13}" width="380" height="18" rx="4" fill="#E3E8DF"/>',
                     f'<rect x="{px+260}" y="{y-13}" width="{380*value:.1f}" height="18" rx="4" fill="{color}"/>',
                     f'<text x="{px+658}" y="{y+5}" fill="{INK}" font-family="Arial" font-weight="700" font-size="17">{pct(value)}</text>']
    body += [f'<text x="72" y="965" fill="{MUTED}" font-family="Arial" font-size="17">Recall denominator: 520 critical docs; C4 denominator: 120 stale critical docs; legitimate FPR denominator: 6,271; workload denominator: 1,680 cases.</text>',
             f'<text x="72" y="995" fill="{MUTED}" font-family="Arial" font-size="16">No-temporal and full LR both have 0% C4 recall. Separate thresholds and development-label inconsistency prevent causal attribution.</text>']
    def draw2(d,w,hgt):
        d.text((72,45),"Semantic feature ablation — frozen Generator C outputs",font=title_font,fill=INK)
        d.text((72,98),"Ablations are Logistic Regression variants; Hybrid is a contextual, non-like-for-like reference.",font=subtitle_font,fill=MUTED)
        for j,(label,key,color) in enumerate(series):
            px=72+(j%2)*850; py=195+(j//2)*370
            d.rounded_rectangle((px,py,px+800,py+330),radius=10,fill=WHITE,outline="#D4DDD4",width=2)
            d.text((px+24,py+18),label,font=_font(20,True),fill=INK)
            for i,m in enumerate(fig2_models):
                row=vals[m]; value=row["c4_stale_recall"] if key=="c4_stale_recall" else row[key]; y=py+78+i*42
                d.text((px+22,y-9),model_short[m],font=_font(15),fill=MUTED)
                d.rounded_rectangle((px+260,y-10,px+640,y+8),radius=4,fill="#E3E8DF")
                d.rounded_rectangle((px+260,y-10,px+260+380*value,y+8),radius=4,fill=color)
                d.text((px+658,y-10),pct(value),font=_font(16,True),fill=INK)
        d.text((72,965),"Recall denominator: 520 critical docs; C4 denominator: 120 stale critical docs; FPR: 6,271 legitimate docs; workload: 1,680 cases.",font=_font(16),fill=MUTED)
        d.text((72,993),"Full LR and no-temporal both have 0% C4 recall. Threshold and label issues prevent causal attribution.",font=_font(15),fill=MUTED)
    _save("".join(body), draw2, "figure2_semantic_ablation")

    # Figure 3: narrative progression in separate cards (not a common performance axis).
    body = [f'<text x="72" y="82" fill="{INK}" font-family="Arial" font-weight="700" font-size="44">Research progression — evidence and remaining gaps</text>',
            f'<text x="72" y="124" fill="{MUTED}" font-family="Arial" font-size="22">Different generators, protocols and cohorts; these results are not equivalent test distributions.</text>']
    card_x=[72,650,1228]
    for i,row in enumerate(progression):
        x=card_x[i]; color=["#507D6F",RED,GREEN][i]
        body += [f'<rect x="{x}" y="220" width="500" height="560" rx="12" fill="{WHITE}" stroke="#D4DDD4"/>',
                 f'<rect x="{x}" y="220" width="500" height="11" rx="5" fill="{color}"/>',
                 f'<text x="{x+30}" y="286" fill="{color}" font-family="Arial" font-weight="700" font-size="30">{row["phase"]}</text>',
                 f'<text x="{x+30}" y="332" fill="{INK}" font-family="Arial" font-weight="700" font-size="22">{html.escape(row["generator"])}</text>']
        lines = row["result"].split("; ")
        for k,line in enumerate(lines):
            yy=410+k*70
            body += [f'<circle cx="{x+42}" cy="{yy-8}" r="5" fill="{GOLD}"/>',
                     f'<text x="{x+60}" y="{yy}" fill="{INK}" font-family="Arial" font-size="20">{html.escape(line)}</text>']
        body += [f'<text x="{x+30}" y="710" fill="{MUTED}" font-family="Arial" font-size="18">{html.escape(row["status"])}</text>']
    body += [f'<text x="72" y="870" fill="{INK}" font-family="Arial" font-weight="700" font-size="21">Current conclusion: promising synthetic pattern, but not a confirmatory generalization claim.</text>',
             f'<text x="72" y="910" fill="{MUTED}" font-family="Arial" font-size="18">C labels are open · 100 development temporal labels inconsistent · XGBoost not evaluated · no real-bank validation</text>']
    def draw3(d,w,hgt):
        d.text((72,45),"Research progression — evidence and remaining gaps",font=title_font,fill=INK)
        d.text((72,98),"Different generators, protocols and cohorts; not equivalent test distributions.",font=subtitle_font,fill=MUTED)
        for i,row in enumerate(progression):
            x=card_x[i]; color=["#507D6F",RED,GREEN][i]
            d.rounded_rectangle((x,220,x+500,780),radius=12,fill=WHITE,outline="#D4DDD4",width=2); d.rectangle((x,220,x+500,232),fill=color)
            d.text((x+30,266),row["phase"],font=_font(30,True),fill=color)
            d.text((x+30,312),row["generator"],font=_font(18,True),fill=INK)
            y=385
            for line in row["result"].split("; "):
                y=_draw_text(d,x+34,y,line,_font(17),INK,width=430,gap=5)+16
            _draw_text(d,x+30,690,row["status"],_font(16),MUTED,width=440)
        d.text((72,870),"Current conclusion: promising synthetic pattern, but not a confirmatory generalization claim.",font=_font(21,True),fill=INK)
        d.text((72,910),"C labels open · 100 development temporal labels inconsistent · XGBoost not evaluated · no real-bank validation",font=_font(17),fill=MUTED)
    _save("".join(body),draw3,"figure3_research_progression")

    footnotes = {
        "figure1_generator_c_performance": "Title: Generator C performance — Semantic Hybrid. Method: frozen post-unblinding predictions; customer-group stratified bootstrap (500 draws). Recall/FPR/AP/calibration are document-level; workload is case-level. Boundary zero-error intervals require cluster-aware interpretation.",
        "figure2_semantic_ablation": "Title: Semantic feature ablation — frozen Generator C outputs. Denominators: 520 critical documents; 120 C4 stale critical documents; 6,271 legitimate documents; 1,680 cases. Hybrid combines deterministic rules+LR and is contextual, not a matched LR ablation. Observed comparisons are not causal.",
        "figure3_research_progression": "Title: Research progression — evidence and remaining gaps. V3, V4 and V4.1 use different generators, protocols, samples and model contexts; cards are qualitative and do not imply directly comparable test performance.",
    }
    for stem, foot in footnotes.items():
        write(PITCH / f"{stem}_method.md", f"# {foot.split('.')[0]}\n\n{foot}")
    update_release_manifest()


def update_release_manifest():
    """Extend the existing fail-closed release allowlist with generated deliverables."""
    release_path = OUT / "RELEASE_MANIFEST.json"
    if not release_path.is_file():
        raise ValueError("Existing V4.1 RELEASE_MANIFEST.json is required")
    release = read(release_path)
    additions = [
        "RECOVERY_AUDIT.md", "GENERATOR_C_RESULTS.md", "GENERATOR_C_METRICS.json",
        "STATISTICAL_AUDIT.md", "RESULTS.md", "PAPER_DRAFT.md", "FAILURE_ANALYSIS.md",
        "ABLATION_REPORT.md", "CLAIMS_AND_LIMITATIONS.md", "REPRODUCTION.md",
        "UPDATED_DATASET_AND_SPLIT_MANIFESTS.md", "VERIFICATION_LOG.md",
        "ENGLISH_PITCH_EVIDENCE_SUMMARY.md", "PITCH_EVIDENCE_SUMMARY.md",
        "data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_PREDICTIONS.csv",
        "data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_MANIFEST.json",
        "data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_RESULTS.json",
        "data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_PAIRED.csv",
        "data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_SCENARIO_METRICS.csv",
        "data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_SOURCE_METRICS.csv",
    ]
    additions += [str(p.relative_to(OUT)).replace("\\", "/") for p in PITCH.rglob("*") if p.is_file()]
    public = list(dict.fromkeys(release.get("public_artifacts", []) + additions))
    figures = list(dict.fromkeys(release.get("public_figures", []) + [
        "figure1_generator_c_performance.svg", "figure2_semantic_ablation.svg", "figure3_research_progression.svg",
    ]))
    release["public_artifacts"] = public
    release["public_figures"] = figures
    release["artifact_checksums"] = {rel: sha(OUT / rel) for rel in public if (OUT / rel).is_file()}
    source_checksums = release.get("source_checksums", {})
    missing_sources = [rel for rel in source_checksums if not (OUT / rel).is_file()]
    if missing_sources:
        raise ValueError(f"V4.1 release source artifacts are missing: {missing_sources}")
    release["source_checksums"] = {rel: sha(OUT / rel) for rel in source_checksums}
    write(release_path, json.dumps(release, indent=2))


def verify_protected():
    v2v3_manifest = read(ROOT / "reports/evidence-v4/ARTIFACT_MANIFEST.json")
    v4_manifest = read(ROOT / "reports/evidence-v4/final_manifest.json")
    errors = []
    v2v3_bad = set()
    for art in v2v3_manifest["artifacts"]:
        path = ROOT / art["path"]
        if not path.is_file() or path.stat().st_size != art["bytes"] or sha(path) != art["sha256"]:
            errors.append({"manifest": "V2/V3", "path": art["path"], "expected_sha256": art["sha256"],
                           "actual_sha256": sha(path) if path.is_file() else None})
            v2v3_bad.add(art["path"])
    v4_count = 0
    for art in v4_manifest["artifacts"]:
        path = ROOT / art["path"]
        if not path.is_file() or path.stat().st_size != art["bytes"] or sha(path) != art["sha256"]:
            errors.append({"manifest": "V4", "path": art["path"], "expected_sha256": art["sha256"],
                           "actual_sha256": sha(path) if path.is_file() else None})
        else:
            v4_count += 1
    return {"v2_v3_manifest_sha256": sha(ROOT / "reports/evidence-v4/ARTIFACT_MANIFEST.json"),
            "v2_v3_expected": len(v2v3_manifest["artifacts"]), "v2_v3_verified": len(v2v3_manifest["artifacts"]) - len(v2v3_bad),
            "v4_manifest_sha256": sha(ROOT / "reports/evidence-v4/final_manifest.json"),
            "v4_expected": len(v4_manifest["artifacts"]), "v4_verified": v4_count, "mismatches": errors}


def make_final_manifest():
    r = load_metrics()
    protected = verify_protected()
    paths = [
        "evidence_ai/v4_1_audit.py", "evidence_ai/semantic_evidence.py", "evidence_ai/v4_1_training.py",
        "evidence_ai/v4_1_generator_dev.py", "evidence_ai/v4_1_generator_c.py", "evidence_ai/v4_1_predict_c.py",
        "evidence_ai/v4_1_evaluate_c.py", "evidence_ai/v4_1_reconcile_c.py", "evidence_ai/v4_1_replay.py",
        "evidence_ai/v4_1_hard_negatives.py", "evidence_ai/v4_1_data_quality_audit.py", "evidence_ai/v4_1_finalize.py",
        "evidence_ai/v4_1_delayed_xgb.py",
        "backend/app/evidence_research_v41.py", "backend/tests/test_evidence_research_v41.py",
        "frontend/src/EvidenceResearchV41.tsx", "frontend/src/evidence-research-v41.css", "frontend/src/App.tsx", "backend/app/main.py",
    ]
    paths += [
        "reports/evidence-v4.1/RECOVERY_AUDIT.md", "reports/evidence-v4.1/GENERATOR_C_RESULTS.md",
        "reports/evidence-v4.1/GENERATOR_C_METRICS.json", "reports/evidence-v4.1/STATISTICAL_AUDIT.md",
        "reports/evidence-v4.1/RESULTS.md", "reports/evidence-v4.1/PAPER_DRAFT.md",
        "reports/evidence-v4.1/FAILURE_ANALYSIS.md", "reports/evidence-v4.1/ABLATION_REPORT.md",
        "reports/evidence-v4.1/CLAIMS_AND_LIMITATIONS.md", "reports/evidence-v4.1/REPRODUCTION.md",
        "reports/evidence-v4.1/UPDATED_DATASET_AND_SPLIT_MANIFESTS.md", "reports/evidence-v4.1/VERIFICATION_LOG.md",
        "reports/evidence-v4.1/RELEASE_MANIFEST.json",
        "reports/evidence-v4.1/data/generator-c-v1/dataset_manifest.json",
        "reports/evidence-v4.1/data/generator-c-v1/C_PREDICTION_MANIFEST.json",
        "reports/evidence-v4.1/data/generator-c-v1/C_EVALUATION_MANIFEST.json",
        "reports/evidence-v4.1/data/development-d1.1/HARD_NEGATIVE_MANIFEST.json",
        "reports/evidence-v4.1/data/development-d1.1/D1.1_LABEL_SEMANTIC_AUDIT.json",
        "reports/evidence-v4.1/models/frozen-v1/frozen_model_manifest.json",
        "reports/evidence-v4.1/models/frozen-v1/frozen_release.json",
        "reports/evidence-v4.1/models/frozen-v1/training_configuration.json",
        "reports/evidence-v4.1/models/frozen-v1/training_log.json",
        "reports/evidence-v4.1/data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_PREDICTIONS.csv",
        "reports/evidence-v4.1/data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_MANIFEST.json",
        "reports/evidence-v4.1/data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_RESULTS.json",
        "reports/evidence-v4.1/data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_PAIRED.csv",
        "reports/evidence-v4.1/data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_SCENARIO_METRICS.csv",
        "reports/evidence-v4.1/data/generator-c-v1/C_DELAYED_BASELINE_XGBOOST_SOURCE_METRICS.csv",
        "reports/evidence-v4.1/data/generator-c-v1/GENERATOR_C_RESULTS.json",
        "reports/evidence-v4.1/GENERATOR_C_SUMMARY.json",
        "reports/evidence-v4.1/GENERATOR_C_REPORT.md",
        "reports/evidence-v4.1/ENGLISH_PITCH_EVIDENCE_SUMMARY.md",
        "reports/evidence-v4.1/PITCH_EVIDENCE_SUMMARY.md",
        "reports/evidence-v4.1/SEMANTIC_EVIDENCE_SCHEMA.md",
        "reports/evidence-v4.1/models/frozen-v1/semantic_xgboost.joblib",
    ]
    pitch_files = [p for p in PITCH.rglob("*") if p.is_file()]
    paths.extend(str(p.relative_to(ROOT)).replace("\\", "/") for p in pitch_files)
    # Record frozen model artifact digests named in the manifest, never stale archive files.
    for name in ("semantic_logistic.joblib", "semantic_deepsets.pt", "ablation_no_temporal.joblib", "ablation_no_comparability.joblib", "ablation_no_source_provenance.joblib"):
        paths.append(f"reports/evidence-v4.1/models/frozen-v1/{name}")
    paths.extend(f"reports/evidence-v3/synthetic/xgb-d4-s{seed}.json" for seed in (13, 29, 43))
    artifacts = []
    for rel in dict.fromkeys(paths):
        p = ROOT / rel
        if p.is_file():
            artifacts.append({"path": rel.replace("\\", "/"), "bytes": p.stat().st_size, "sha256": sha(p)})
    # Record prediction, label, observation and canonical payload digests without copying content.
    data_digests = {name: sha(DATA / name) for name in ("C_PREDICTIONS_FROZEN.csv", "gold_labels.json", "observed.json", "canonical_truth.json")}
    manifest = {
        "manifest_version": "cobi-evidence-v4.1-final-1",
        "created_by": "evidence_ai.v4_1_finalize",
        "evaluation_status": "POST_UNBLINDING_EXPLORATORY",
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
        "routing_authorized": False,
        "approval_authorized": False,
        "model_or_threshold_changed_from_c": False,
        "all_previous_aggregate_metrics_match": r["all_previous_aggregate_metrics_match"],
        "protected_baseline_verification": protected,
        "protected_integrity_status": "ALL_V2_V3_INTACT_WITH_PREEXISTING_V4_MISMATCH" if protected["mismatches"] else "ALL_PROTECTED_HASHES_MATCH",
        "data_sha256": data_digests,
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "self_hash_excluded": True,
    }
    write(OUT / "FINAL_MANIFEST.json", json.dumps(manifest, indent=2))
    return manifest


def run(final_manifest=False):
    r = load_metrics()
    make_reports(r)
    if final_manifest:
        manifest = make_final_manifest()
    else:
        manifest = None
    return {"status": "PASS_RECONCILED_NO_MODEL_CHANGES", "all_previous_aggregate_metrics_match": r["all_previous_aggregate_metrics_match"],
            "reports_and_pitch_written": True, "final_manifest_written": final_manifest,
            "artifact_count": manifest["artifact_count"] if manifest else None}


if __name__ == "__main__":
    import sys
    print(json.dumps(run(final_manifest="--final-manifest" in sys.argv), indent=2))
