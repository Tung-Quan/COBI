"""Build reproducible Generator C reports, figures, and the read-only research release.

This script consumes only the already-frozen evaluation and reconciliation outputs.
It never trains, calibrates, selects, or changes a model or threshold.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/evidence-v4.1"
C_DIR = OUT / "data/generator-c-v1"
PITCH = OUT / "pitch"
TABLES = OUT / "tables"
FIGURES = PITCH / "figures"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                             for key, value in row.items()})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pct(value):
    return "N/A" if value is None else f"{100 * value:.1f}%"


def f3(value):
    return "N/A" if value is None else f"{value:.3f}"


def csv_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def svg_text(x, y, value, size=16, fill="#203a35", weight="400", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{html.escape(str(value))}</text>')


def build_tradeoff_svg(rows):
    width, height = 1120, 670
    left, plot_width, top = 295, 730, 165
    colors = {"critical_recall": "#0d7867", "overall_legitimate_fpr": "#d06b52", "case_review_workload": "#c19a3a"}
    labels = {"critical_recall": "Critical recall", "overall_legitimate_fpr": "Legitimate-record FPR", "case_review_workload": "Case review workload"}
    models = ["SEMANTIC_HYBRID", "SEMANTIC_RULE", "M0_CS_V2", "M1_LOGISTIC", "M3_DEEP_SETS"]
    rows_by_id = {row["model"]: row for row in rows}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
             '<title>Generator C frozen model comparison</title>',
             '<desc>Critical recall, legitimate-record false-positive rate, and case review workload for available frozen models.</desc>',
             f'<rect width="{width}" height="{height}" fill="#fffef9"/>',
             svg_text(40, 52, "Generator C: detection and review trade-offs", 27, "#173e35", "700"),
             svg_text(40, 82, "Frozen thresholds · independent synthetic challenge · higher recall is better; lower FPR and workload are better", 14, "#536a63")]
    for i, (key, label) in enumerate(labels.items()):
        x = 45 + i * 330
        parts.append(f'<rect x="{x}" y="112" width="17" height="17" rx="3" fill="{colors[key]}"/>')
        parts.append(svg_text(x + 25, 126, label, 14, "#294d44", "600"))
    for tick in range(0, 101, 20):
        x = left + plot_width * tick / 100
        parts.append(f'<line x1="{x:.1f}" y1="{top-12}" x2="{x:.1f}" y2="{height-62}" stroke="#e5e9e2"/>')
        parts.append(svg_text(x, height - 35, f"{tick}%", 12, "#65766f", anchor="middle"))
    for row_i, model in enumerate(models):
        row = rows_by_id[model]
        y0 = top + row_i * 92
        display = {"SEMANTIC_HYBRID": "Semantic hybrid", "SEMANTIC_RULE": "Semantic rules", "M0_CS_V2": "Frozen CS V2",
                   "M1_LOGISTIC": "Frozen logistic regression", "M3_DEEP_SETS": "Frozen Deep Sets"}[model]
        parts.append(svg_text(35, y0 + 29, display, 15, "#243f38", "700" if model == "SEMANTIC_HYBRID" else "500"))
        parts.append(f'<line x1="30" y1="{y0+51}" x2="1090" y2="{y0+51}" stroke="#edf0ea"/>')
        for metric_i, key in enumerate(labels):
            value = row.get(key)
            if value is None:
                continue
            y = y0 + 10 + metric_i * 22
            bar_width = plot_width * float(value)
            parts.append(f'<rect x="{left}" y="{y}" width="{max(bar_width, 1):.1f}" height="14" rx="3" fill="{colors[key]}" opacity="0.9"/>')
            label_x = min(left + bar_width + 8, left + plot_width - 2)
            parts.append(svg_text(label_x, y + 12, pct(float(value)), 11, "#243f38", "600"))
    parts.extend([svg_text(40, height - 7, "XGBoost baseline arms were unavailable in the frozen runtime and are omitted, not imputed.", 12, "#725b4b"), '</svg>'])
    return "\n".join(parts)


def build_ablation_svg(rows):
    width, height = 1120, 410
    columns = [
        ("critical_recall", "Critical\nrecall", True),
        ("c4_stale_as_current_recall", "C4 stale\nrecall", True),
        ("legitimate_discrepancy_fpr_c1_c3_c5", "C1/C3/C5\nlegitimate FPR", False),
        ("overall_legitimate_fpr", "Overall\nlegitimate FPR", False),
        ("case_review_workload", "Case review\nworkload", False),
    ]
    models = ["SEMANTIC_LOGISTIC", "ABLATION_NO_TEMPORAL", "ABLATION_NO_COMPARABILITY", "ABLATION_NO_SOURCE_PROVENANCE"]
    display = {"SEMANTIC_LOGISTIC": "Full semantic logistic", "ABLATION_NO_TEMPORAL": "Without temporal features",
               "ABLATION_NO_COMPARABILITY": "Without comparability features", "ABLATION_NO_SOURCE_PROVENANCE": "Without source/provenance features"}
    rows_by_id = {row["model"]: row for row in rows}
    cell_x, cell_w, top, row_h = 350, 142, 138, 55
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
             '<title>Generator C semantic logistic feature ablations</title>',
             '<desc>Frozen-threshold point estimates for the full semantic logistic model and three registered feature ablations.</desc>',
             f'<rect width="{width}" height="{height}" fill="#fffef9"/>',
             svg_text(35, 48, "Feature ablations: recall–false-alert trade-offs", 26, "#173e35", "700"),
             svg_text(35, 78, "C metrics at each arm’s frozen threshold; C was not used to tune any arm.", 14, "#536a63")]
    for col_i, (_, label, _) in enumerate(columns):
        x = cell_x + col_i * cell_w + cell_w / 2
        for line_i, line in enumerate(label.split("\n")):
            parts.append(svg_text(x, 112 + line_i * 17, line, 12, "#294d44", "600", "middle"))
    for row_i, model in enumerate(models):
        row = rows_by_id[model]
        y = top + row_i * row_h
        parts.append(svg_text(35, y + 24, display[model], 14, "#243f38", "600" if row_i == 0 else "500"))
        for col_i, (key, _, higher_is_better) in enumerate(columns):
            value = row.get(key)
            x = cell_x + col_i * cell_w
            if value is None:
                fill, label = "#f0f1ed", "N/A"
            else:
                value = float(value)
                good = value if higher_is_better else 1 - value
                fill = "#d9eee0" if good >= .85 else "#f8edc9" if good >= .60 else "#f2d6cf"
                label = pct(value)
            parts.append(f'<rect x="{x+2}" y="{y}" width="{cell_w-5}" height="42" rx="5" fill="{fill}" opacity="0.9"/>')
            parts.append(svg_text(x + cell_w/2, y + 26, label, 14, "#173e35", "700", "middle"))
    parts.extend([svg_text(35, height - 24, "The full semantic logistic model also had 0% C4 stale recall; this ablation does not show that time features improved it.", 12, "#725b4b"), '</svg>'])
    return "\n".join(parts)


def render_report(summary, results, reconciliation, ablations, audit):
    m = summary["semantic_hybrid"]
    ci = m["ci95"]
    d = summary["dataset"]
    metric_table = "\n".join([
        "| Outcome | Observed result | 95% customer-group bootstrap interval |",
        "|---|---:|---:|",
        f"| Critical recall | 520 / 520 ({pct(m['critical_recall'])}) | {pct(ci['critical_recall']['lower_95'])}–{pct(ci['critical_recall']['upper_95'])} |",
        f"| C4 stale-as-current recall | 120 / 120 ({pct(m['c4_stale_as_current_recall'])}) | {pct(ci['c4_stale_as_current_recall']['lower_95'])}–{pct(ci['c4_stale_as_current_recall']['upper_95'])} |",
        f"| C1/C3/C5 legitimate-discrepancy FPR | 0 / 2,927 ({pct(m['legitimate_discrepancy_fpr_c1_c3_c5'])}) | {pct(ci['legitimate_discrepancy_fpr_c1_c3_c5']['lower_95'])}–{pct(ci['legitimate_discrepancy_fpr_c1_c3_c5']['upper_95'])} |",
        f"| Overall legitimate-record FPR | 400 / 6,271 ({pct(m['overall_legitimate_fpr'])}) | See group-level uncertainty note |",
        f"| Case review workload | 520 / 1,680 ({pct(m['case_review_workload'])}) | {pct(ci['case_review_workload']['lower_95'])}–{pct(ci['case_review_workload']['upper_95'])} |",
        f"| Material-defect average precision | {f3(m['material_average_precision'])} | {f3(ci['material_average_precision']['lower_95'])}–{f3(ci['material_average_precision']['upper_95'])} |",
        f"| Brier score | {f3(m['brier_score'])} | {f3(ci['brier_score']['lower_95'])}–{f3(ci['brier_score']['upper_95'])} |",
        f"| Log loss | {f3(m['log_loss'])} | {f3(ci['log_loss']['lower_95'])}–{f3(ci['log_loss']['upper_95'])} |",
    ])
    scenario_table = ["| Scenario | Documents | Critical support | Critical recall | Legitimate FPR | Review workload |", "|---|---:|---:|---:|---:|---:|"]
    for row in summary["scenario_metrics"]:
        scenario_table.append(f"| {row['scenario']} | {row['documents']:,} | {row['critical_support']:,} | {pct(row['critical_recall'])} | {pct(row['overall_legitimate_fpr'])} | {pct(row['case_review_workload'])} |")
    scenario_table = "\n".join(scenario_table)
    comparison = "\n".join([
        "| Frozen model | Critical recall | Legitimate-record FPR | Case review workload | Material AP |",
        "|---|---:|---:|---:|---:|",
        *[f"| {row['label']} | {pct(row['critical_recall'])} ({row['critical_tp']}/{row['critical_support']}) | {pct(row['overall_legitimate_fpr'])} | {pct(row['case_review_workload'])} | {f3(row['material_average_precision'])} |" for row in summary["model_comparison"]],
    ])
    ablation_table = "\n".join([
        "| Logistic arm | Critical recall | C4 stale recall | C1/C3/C5 FPR | Overall legitimate FPR | Case workload |",
        "|---|---:|---:|---:|---:|---:|",
        *[f"| {row['label']} | {pct(row['critical_recall'])} | {pct(row['c4_stale_as_current_recall'])} | {pct(row['legitimate_discrepancy_fpr_c1_c3_c5'])} | {pct(row['overall_legitimate_fpr'])} | {pct(row['case_review_workload'])} |" for row in summary["ablation_comparison"]],
    ])
    false_positive_table = "\n".join(["| Scenario | False-positive records | Legitimate support |", "|---|---:|---:|"] +
        [f"| {row['scenario']} | {row['false_positives']:,} | {row['legitimate_support']:,} |" for row in summary["false_positive_breakdown"]])
    return f"""# COBI Evidence AI V4.1 — Generator C Scientific Report

**Report date:** 2026-11-08  
**Protocol:** `{summary['protocol_id']}`  
**Generator:** `{summary['generator_id']}`  
**Study status:** `{summary['status']}`  
**Validation status:** `{summary['validation_status']}`

## Executive finding

On the preregistered synthetic Generator C challenge, the frozen semantic hybrid flagged all 520 labeled critical records, including all 120 stale-as-current records in C4. It flagged no legitimate records in the registered C1/C3/C5 endpoint (0/2,927), while its overall legitimate-record FPR was 400/6,271 (6.38%) and case review workload was 520/1,680 (30.95%). Its material-defect AP was 0.565, Brier score 0.0339, and log loss 0.0939.

These are measured outcomes on generated structured evidence. They do not establish performance on real financial documents. The development-label audit found that 100 stale records in D1.1 were missing critical labels, making feature-effect interpretations exploratory. The XGBoost replay dependency was unavailable, so the complete registered baseline acceptance criterion remains unassessable. The status remains **`EVIDENCE_AI_VALIDATION_BLOCKED`**.

**Construct-independence caveat:** Generator C is independently implemented, but its gold criteria overlap with the deterministic semantic rules. The generator uses the same VND field tolerances for C2/C6/C7 conflicts, and both C4 gold construction and the time rule use a 180-day critical-staleness criterion. The 100% recall therefore does not constitute a fully independent test of those semantic criteria. This is target-construct overlap, not evidence that hidden gold labels were passed to the predictor.

## Study question

Can a semantic representation of financial evidence improve defect detection under independent synthetic distribution shift while avoiding alerts on valid differences between records that are not comparable?

Generator C challenges a frozen release on seven registered scenarios: gross/net and period mismatch; same-period corruption; correction lineage; time validity; non-comparable subjects/accounts; true comparable conflict; and a held-out payroll+merchant source pair. Its generator implementation and seed are separate from development data and Generator B.

## Protocol and data

- Protocol ID `{summary['protocol_id']}`, registered before Generator C creation and label evaluation.
- {d['customer_groups']:,} customer groups, {d['cases']:,} cases, and {d['documents']:,} structured evidence records. There are {d['critical_documents']:,} labeled critical records.
- Predictions were frozen before label access. The prediction checksum and frozen model manifest were checked by the post-unblinding reconciliation.
- The reconciliation recomputed all aggregate metrics from the frozen predictions and labels; every aggregate matched the original evaluation (`all_previous_aggregate_metrics_match = {str(reconciliation['all_previous_aggregate_metrics_match']).lower()}`). It changed no model or threshold.
- Uncertainty uses 500 scenario-stratified customer-group bootstrap draws. Intervals condition on the chosen synthetic generator, label rules, frozen models, and thresholds.
- The hybrid operating threshold was frozen at `{m['frozen_threshold']:.12f}`.

The data-quality endpoint records generated financial facts and semantics. It does not measure OCR, document parsing, evidence acquisition, or real-world adjudication.

### Construct independence and rule-target overlap

Generator C has a separate implementation path, seed, and templates, but the generator and deterministic semantic comparator share parts of the target definition. Both use VND tolerances of income 500,000, debt 250,000, and purchase 500,000. In the C2, C6, and C7 corruption cases, generated amount differences are 2.1-4.2 times the applicable tolerance, while the comparator marks a comparable pair critical at a difference of at least two times that tolerance. For C4, the gold marks an old record asserted as current and the rule marks a period-mismatched record critical at age 180 days or more; generated stale records are 432 days old. This is semantic-criterion overlap, not direct hidden-label leakage: corruption identifiers and canonical gold are not predictor inputs. It means strong recall demonstrates agreement with these generated constructs and rules, not independent generalization to externally adjudicated criteria.

## Primary results

{metric_table}

The 400 false-positive records are valid peers of corrupted records in comparable-pair contradiction scenarios. The pair-level rule requests review of both members because it has no independent signal identifying which peer is wrong:

{false_positive_table}

The C1/C3/C5 zero observed false-positive rate has zero errors in the registered sample. A group-level exact binomial analysis found no group with any endpoint false positive among 360 groups; the one-sided 95% upper bound for that *group event rate* is 0.83%. A separate conservative Hoeffding upper bound for equal-group-weighted FPR is 6.45%. These are group-level quantities and are not document-weighted FPR intervals.

### Scenario breakdown

{scenario_table}

C7 contains 60 positive customer groups; all had every critical record detected. The exact 95% group-level interval for this all-critical-records-detected event is 94.0%–100%. In C7, 120/832 legitimate records were also flagged (14.4%), so recall should be read together with the review burden.

## Frozen model comparison

{comparison}

Frozen CS V2, Logistic Regression, and Deep Sets each achieved 100% critical recall in this challenge while flagging approximately all legitimate records and sending nearly every case to review. The semantic hybrid retained the same observed critical recall with substantially fewer alerts on this synthetic challenge. The pairwise bootstrap contrasts are descriptive and post-unblinding; they are not confirmatory model-selection evidence.

The semantic rule baseline alone also achieved 100% critical recall, with 10.38% overall legitimate FPR and 37.08% case workload. The hybrid's corresponding point estimates were 6.38% and 30.95%. Learned-model contributions remain uncertain because of the D1.1 label inconsistency described below.

## Registered feature ablations

{ablation_table}

The full semantic Logistic Regression and its no-temporal ablation both had 0% C4 stale-as-current recall. This challenge therefore does not show that the learned temporal features improved stale recall. Removing comparability features raised logistic critical recall from 4.8% to 34.4%, but also raised overall legitimate FPR from 0.9% to 21.5% and case workload from 4.8% to 63.0%. These frozen-threshold outcomes show a trade-off in this experiment; they do not establish a causal or general feature contribution.

## Registered acceptance criteria

| Criterion | Result | Status |
|---|---:|---|
| Aggregate critical recall at least 90% | 520/520 = 100% | Point estimate meets |
| C4 stale-as-current recall at least 90% | 120/120 = 100% | Point estimate meets |
| C1/C3/C5 legitimate-discrepancy FPR at most 20% | 0/2,927 = 0% | Point estimate meets |
| C7 critical recall at least 85% | 120/120 = 100% | Point estimate meets |
| Recall no more than 2 percentage points below the best complete frozen baseline | Best available frozen baseline = 100%; XGBoost replay unavailable | **Unassessable as registered** |

Four criteria meet their point-estimate thresholds. The complete registered criterion set is not met as an evaluable package because the frozen XGBoost baseline could not run. No XGBoost result was fabricated or substituted.

## Data-quality audit and interpretation

The post-evaluation D1.1 audit found 200 records that the temporal rule treats as stale-as-current; 100 were labeled noncritical. The missing critical labels span the training, validation, calibration, and locked development-test partitions (60, 15, 15, and 10 records). Generator C labels and scores were not changed or reopened for tuning. This issue does not rewrite the frozen C measurements, but it weakens training and threshold evidence about temporal behavior and means that the semantic learned feature effects must be treated as exploratory.

The hybrid's 100% recall includes deterministic semantic rules. It cannot be attributed to learned semantic features alone. The strong point estimates on C are therefore evidence that this frozen, rule-plus-model system succeeded on the registered generated scenarios, not that the model learned a generally valid financial-evidence rule.

## Limitations and deployment status

1. All examples, labels, and financial facts are programmatically generated; the distributions may not represent banks, merchants, or borrower documents.
2. Structured metadata is provided to the evaluator. OCR and upstream extraction quality are outside the experiment.
3. The finite scenario taxonomy and held-out source pair do not cover all financial products, document types, languages, or source systems.
4. Bootstrap intervals are conditional on the frozen synthetic data-generating process and do not account for generator misspecification or label-policy error.
5. The D1.1 temporal-label inconsistency prevents confirmatory attribution of learned feature effects.
6. XGBoost replay was blocked by the unavailable `xgboost==3.0.5` dependency; full baseline acceptance is incomplete.
7. The pair-level comparator flags a valid peer alongside true contradictions when it cannot identify the corrupt member, contributing 400 false-positive records.
8. Generator C is independent in implementation path, seed, and templates, but its C2/C6/C7 monetary defect magnitudes and C4 stale-age criterion overlap with the deterministic rules. The 100% recall result is therefore not a fully independent validation of those semantic criteria; this is construct overlap, not direct hidden-label leakage.

Research outputs remain read-only. `routing_authorized = false`, `approval_authorized = false`, and checkout does not consume Generator C outputs. No lending or operational use is authorized.

## Reproducibility and artifact map

- Frozen primary output: `data/generator-c-v1/GENERATOR_C_RESULTS.json`
- Independent arithmetic reconciliation: `GENERATOR_C_METRICS.json`
- Full scenario/source/contrast tables: `tables/`
- Protocol: `EXPERIMENT_PROTOCOL_C.md`
- Development-label audit: `POST_EVALUATION_AUDIT_ADDENDUM.json`
- Prediction freeze manifest: `data/generator-c-v1/C_PREDICTION_MANIFEST.json`
- Evaluation manifest: `data/generator-c-v1/C_EVALUATION_MANIFEST.json`
- Release integrity manifest: `RELEASE_MANIFEST.json`

All presentation artifacts are derived from the existing frozen results. This reporting step does not train models, change predictions, or select thresholds.
"""


def main():
    reconciliation = read_json(OUT / "GENERATOR_C_METRICS.json")
    results = read_json(C_DIR / "GENERATOR_C_RESULTS.json")
    ablations = read_json(C_DIR / "ABLACTION_STUDY.json")
    dataset = read_json(C_DIR / "dataset_manifest.json")
    pred_manifest = read_json(C_DIR / "C_PREDICTION_MANIFEST.json")
    eval_manifest = read_json(C_DIR / "C_EVALUATION_MANIFEST.json")
    access = read_json(C_DIR / "LABEL_ACCESS_STATUS.json")
    audit = read_json(OUT / "POST_EVALUATION_AUDIT_ADDENDUM.json")

    if reconciliation.get("status") != "POST_UNBLINDING_RECONCILIATION_NO_TUNING":
        raise ValueError("The independent Generator C reconciliation is missing or has an unexpected status")
    if not reconciliation.get("all_previous_aggregate_metrics_match"):
        raise ValueError("Reconciled aggregate metrics do not match the frozen evaluation")
    if not reconciliation.get("prediction_freeze_verified") or reconciliation.get("models_or_thresholds_changed"):
        raise ValueError("Frozen-prediction conditions are not satisfied")
    if pred_manifest.get("status") != "PREDICTIONS_FROZEN_LABELS_NOT_OPENED":
        raise ValueError("The prediction freeze manifest is invalid")
    if not access.get("predictions_frozen") or not access.get("labels_opened_for_evaluation"):
        raise ValueError("The recorded label-access state is incomplete")
    if eval_manifest.get("status") != "LABELS_OPENED_EVALUATION_COMPLETE":
        raise ValueError("The recorded evaluation manifest is incomplete")

    hybrid = reconciliation["aggregate_metrics"]["SEMANTIC_HYBRID"]
    ci = reconciliation["bootstrap"]["intervals_by_model"]["SEMANTIC_HYBRID"]
    scenario_rows = [row for row in reconciliation["scenario_metrics"] if row["model"] == "SEMANTIC_HYBRID"]
    false_positive_counts = {}
    for row in results["failure_taxonomy"]:
        if row["model"] == "SEMANTIC_HYBRID" and row["failure_category"] == "PAIR_LEVEL_REVIEW_FLAGS_VALID_PEER":
            false_positive_counts[row["scenario"]] = false_positive_counts.get(row["scenario"], 0) + 1

    model_labels = {"SEMANTIC_HYBRID": "Semantic hybrid", "SEMANTIC_RULE": "Semantic rules",
                    "M0_CS_V2": "Frozen CS V2", "M1_LOGISTIC": "Frozen Logistic Regression",
                    "M3_DEEP_SETS": "Frozen Deep Sets"}
    model_comparison = []
    for model in model_labels:
        metric = reconciliation["aggregate_metrics"].get(model)
        if not metric:
            continue
        model_comparison.append({
            "model": model, "label": model_labels[model], "critical_recall": metric["critical_recall"],
            "critical_tp": metric["critical_tp"], "critical_support": metric["critical_support"],
            "overall_legitimate_fpr": metric["overall_legitimate_fpr"],
            "legitimate_fp": metric["legitimate_fp"], "legitimate_support": metric["legitimate_support"],
            "case_review_workload": metric["case_review_workload"], "flagged_case_count": metric["flagged_case_count"],
            "case_count": metric["case_count"], "material_average_precision": metric["material_average_precision"],
            "ci95": reconciliation["bootstrap"]["intervals_by_model"].get(model, {}),
        })

    ablation_labels = {"SEMANTIC_LOGISTIC": "Full semantic Logistic Regression",
                       "ABLATION_NO_TEMPORAL": "Without temporal features",
                       "ABLATION_NO_COMPARABILITY": "Without comparability features",
                       "ABLATION_NO_SOURCE_PROVENANCE": "Without source/provenance features"}
    ablation_comparison = []
    for model, label in ablation_labels.items():
        metric = reconciliation["aggregate_metrics"].get(model)
        if not metric:
            continue
        ablation_comparison.append({
            "model": model, "label": label, "critical_recall": metric["critical_recall"],
            "c4_stale_as_current_recall": metric["c4_stale_as_current_recall"],
            "legitimate_discrepancy_fpr_c1_c3_c5": metric["legitimate_discrepancy_fpr_c1_c3_c5"],
            "overall_legitimate_fpr": metric["overall_legitimate_fpr"],
            "case_review_workload": metric["case_review_workload"],
            "material_average_precision": metric["material_average_precision"],
            "ci95": reconciliation["bootstrap"]["intervals_by_model"].get(model, {}),
        })

    summary = {
        "release_id": "cobi-evidence-v4.1-generator-c-reporting-1.0",
        "status": results["status"], "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
        "protocol_id": results["protocol_id"], "generator_id": results["generator_id"],
        "dataset": {"customer_groups": dataset["group_count"], "cases": dataset["case_count"],
                    "documents": dataset["document_count"], "critical_documents": hybrid["critical_support"],
                    "positive_material_documents": hybrid["material_defect_support"], "seed": dataset["seed"]},
        "semantic_hybrid": {
            "critical_recall": hybrid["critical_recall"], "critical_tp": hybrid["critical_tp"],
            "critical_support": hybrid["critical_support"], "critical_false_negatives": hybrid["critical_fn"],
            "c4_stale_as_current_recall": hybrid["c4_stale_as_current_recall"],
            "c4_stale_tp": hybrid["c4_stale_tp"], "c4_stale_support": hybrid["c4_stale_critical_support"],
            "legitimate_discrepancy_fpr_c1_c3_c5": hybrid["legitimate_discrepancy_fpr_c1_c3_c5"],
            "legitimate_discrepancy_fp": hybrid["legitimate_discrepancy_fp_c1_c3_c5"],
            "legitimate_discrepancy_support": hybrid["legitimate_discrepancy_support_c1_c3_c5"],
            "overall_legitimate_fpr": hybrid["overall_legitimate_fpr"],
            "legitimate_fp": hybrid["legitimate_fp"], "legitimate_support": hybrid["legitimate_support"],
            "case_review_workload": hybrid["case_review_workload"], "flagged_case_count": hybrid["flagged_case_count"],
            "case_count": hybrid["case_count"], "material_average_precision": hybrid["material_average_precision"],
            "brier_score": hybrid["brier_score"], "log_loss": hybrid["log_loss"],
            "frozen_threshold": hybrid["frozen_threshold"], "ci95": ci,
        },
        "model_comparison": model_comparison,
        "ablation_comparison": ablation_comparison,
        "scenario_metrics": [{"scenario": row["scenario"], "documents": row["documents"],
                               "critical_support": row["critical_support"], "critical_recall": row["critical_recall"],
                               "legitimate_fp": row["legitimate_fp"], "legitimate_support": row["legitimate_support"],
                               "overall_legitimate_fpr": row["overall_legitimate_fpr"],
                               "case_review_workload": row["case_review_workload"]} for row in scenario_rows],
        "false_positive_breakdown": [
            {"scenario": scenario, "false_positives": count,
             "legitimate_support": next((row["legitimate_support"] for row in scenario_rows if row["scenario"] == scenario), 0)}
            for scenario, count in sorted(false_positive_counts.items())],
        "acceptance": results["acceptance_assessment"],
        "model_availability": pred_manifest["model_availability"],
        "boundary_uncertainty": reconciliation["boundary_uncertainty"],
        "data_quality_audit": {
            "audit_id": audit["audit_id"], "stale_as_current_records": audit["stale_as_current_records"],
            "critical_labels_missing": audit["critical_labels_missing_on_stale_records"],
            "counts_by_split": audit["counts_by_split"], "consequence": audit["consequence"],
            "generator_c_labels_changed_or_reopened": audit["generator_c_labels_changed_or_reopened"],
            "generator_c_metrics_or_thresholds_changed": audit["generator_c_metrics_or_thresholds_changed"],
        },
        "label_rule_overlap": {
            "classification": "TARGET_CONSTRUCT_OVERLAP_NOT_DIRECT_LABEL_LEAKAGE",
            "shared_field_thresholds_vnd": {"income": 500000, "debt": 250000, "purchase": 500000},
            "comparator_critical_delta_multiple": 2.0,
            "generator_conflict_delta_multiples": {
                "C2": [2.4, 4.2], "C6": [2.1, 3.8], "C7": [2.2, 3.4]
            },
            "shared_stale_critical_age_days": 180,
            "generator_c4_stale_record_age_days": 432,
            "direct_hidden_gold_or_corruption_ids_used_as_predictor_inputs": False,
            "interpretation": "The 100% critical recall is not a fully independent validation of the monetary and stale-evidence criteria because the gold constructs align with deterministic rule criteria. It demonstrates performance on these generated constructs, not generalization to independently adjudicated criteria."
        },
        "reconciliation": {"prediction_freeze_verified": reconciliation["prediction_freeze_verified"],
                           "all_previous_aggregate_metrics_match": reconciliation["all_previous_aggregate_metrics_match"],
                           "models_or_thresholds_changed": reconciliation["models_or_thresholds_changed"],
                           "bootstrap_draws": reconciliation["bootstrap"]["draws"],
                           "bootstrap_unit": reconciliation["bootstrap"]["unit"],
                           "bootstrap_seed": reconciliation["bootstrap"]["seed"]},
        "decision": {"routing_authorized": False, "approval_authorized": False,
                     "checkout_consumes_research_outputs": False},
        "limitations": [
            "All data and labels are programmatically generated; no real bank-document validation was conducted.",
            "Structured metadata is supplied; OCR and evidence extraction accuracy were not measured.",
            "The D1.1 development audit found 100 stale records missing critical labels across training, validation, calibration, and locked development test; learned feature-effect claims are exploratory.",
            "XGBoost replay was blocked by the unavailable xgboost==3.0.5 dependency; the complete registered baseline acceptance comparison is unassessable.",
            "The hybrid includes deterministic semantic rules; its C recall cannot be attributed to learned features alone.",
            "Generator C's C2/C6/C7 monetary defect and C4 stale-age gold constructs overlap with deterministic rule criteria; this is construct overlap, not direct hidden-label leakage.",
            "Bootstrap intervals condition on the synthetic generator, label rules, frozen models, and thresholds.",
        ],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    PITCH.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "GENERATOR_C_SUMMARY.json", summary)

    write_csv(TABLES / "generator_c_model_comparison.csv", model_comparison)
    write_csv(TABLES / "generator_c_ablation_comparison.csv", ablation_comparison)
    write_csv(TABLES / "generator_c_scenario_metrics.csv", reconciliation["scenario_metrics"])
    write_csv(TABLES / "generator_c_paired_baseline_contrasts.csv", reconciliation["paired_group_bootstrap_contrasts"])
    write_csv(TABLES / "generator_c_group_cluster_uncertainty.csv", [
        {"scenario": key, **value} for key, value in reconciliation["boundary_uncertainty"]["by_scenario"].items()])

    (FIGURES / "generator_c_model_tradeoffs.svg").write_text(build_tradeoff_svg(model_comparison), encoding="utf-8")
    (FIGURES / "generator_c_ablation_tradeoffs.svg").write_text(build_ablation_svg(ablation_comparison), encoding="utf-8")
    (OUT / "GENERATOR_C_REPORT.md").write_text(render_report(summary, results, reconciliation, ablations, audit), encoding="utf-8")

    (OUT / "README.md").write_text("""# COBI Evidence AI V4.1 reporting release

This folder contains the read-only Generator C research release. The frozen model, prediction file, labels, and thresholds were not changed by report generation.

## Start here

- `GENERATOR_C_REPORT.md` - complete scientific evaluation, limitations, acceptance status, and interpretation.
- `GENERATOR_C_SUMMARY.json` - curated structured API/UI summary.
- `PAPER_DRAFT.md` - manuscript-style draft.
- `pitch/SLIDE_READY_EVIDENCE.md` - presentation-ready narrative and numbers.
- `pitch/figures/` and `tables/` - vector figures and downloadable evidence tables.
- `EXPERIMENT_PROTOCOL_C.md` - registered Generator C protocol.
- `POST_EVALUATION_AUDIT_ADDENDUM.json` - D1.1 temporal-label audit.
- `GENERATOR_C_METRICS.json` - independent post-unblinding arithmetic reconciliation.

**Status:** `EVIDENCE_AI_VALIDATION_BLOCKED`. Generator C is synthetic technical evidence, not real-bank validation or lending authorization.
""", encoding="utf-8")

    (OUT / "PAPER_DRAFT.md").write_text("""# Semantic-Aware Financial Evidence Validation under Synthetic Distribution Shift

## Abstract

Financial evidence screening must distinguish true contradictions from valid differences caused by reporting periods, subjects, accounts, units, gross/net basis, transaction direction, and correction history. We report an exploratory evaluation of a frozen semantic rule-plus-model hybrid on a preregistered independent synthetic challenge with 840 customer groups, 1,680 cases, 6,791 structured evidence records, and 520 labeled critical records. At its frozen operating threshold, the hybrid detected 520/520 critical records, including 120/120 stale-as-current records, and flagged 0/2,927 legitimate records in the C1/C3/C5 endpoint. Overall it flagged 400/6,271 legitimate records, yielding a 6.38% legitimate-record FPR, and sent 520/1,680 cases to review. Material-defect AP was 0.565; Brier score was 0.0339 and log loss 0.0939. However, a post-evaluation audit identified 100 missing critical labels among stale records in the D1.1 development data, the frozen XGBoost baseline could not be replayed, and 400 valid peer records were flagged in comparable-conflict scenarios. Findings are exploratory synthetic measurements; they do not demonstrate real-document or bank performance.

## 1. Introduction

Evidence validation systems can over-flag when numeric disagreement is treated as a contradiction without checking whether records describe the same person, account, field meaning, period, units, or transaction direction. A second challenge is temporal: evidence can be historically accurate yet invalid when asserted as current for a later request. This study evaluates a semantic-aware representation and hybrid detector under a deliberately constructed distribution shift. The research goal is to test an explicit synthetic challenge, not to validate a lending policy.

## 2. Research question

Can semantic-aware financial-evidence validation maintain critical-defect detection while reducing alerts on valid non-comparable differences and stale evidence under an independent synthetic generator?

The preregistered outcomes are material-defect average precision, critical recall and false-negative count, C1/C3/C5 legitimate-discrepancy FPR, C4 stale-as-current recall, C7 held-out source-pair critical recall, case review workload, calibration losses, and scenario/source strata.

## 3. Method

### 3.1 Synthetic challenge

Generator C (`semantic-ledger-c-v1.0`, seed 2026110802) is implemented independently from the development and Generator B paths. The challenge includes seven scenarios: gross/net and period differences; same-period corruption; correction lineage; time validity; different subjects/accounts; genuine comparable conflict; and a held-out payroll+merchant source pair. The target design is 120 groups per scenario and two cases per group. The observed release has 840 groups, 1,680 cases, and 6,791 evidence records. Canonical truth and event identifiers are excluded from prediction inputs.

### 3.2 Models and information controls

Models and operating thresholds were frozen before Generator C labels were opened. The semantic hybrid combines deterministic semantic checks with a calibrated learned score. Generator C was not used to retrain, calibrate, select a model, or alter a threshold. The post-unblinding reconciliation recomputed metrics and verified that aggregate values match the original frozen evaluation.

Registered XGBoost arms could not be replayed because the offline runtime lacked `xgboost==3.0.5`. They are recorded as unavailable; no substitute is reported under the XGBoost label.

### 3.3 Metrics and uncertainty

Critical recall is detected critical records divided by critical-record support. The registered C1/C3/C5 endpoint is false alerts divided by legitimate records in those three scenarios. Overall legitimate-record FPR uses all labeled legitimate records. Case review workload is the proportion of cases with at least one flagged record. The evaluation reports 500 scenario-stratified customer-group bootstrap percentile intervals. These intervals are conditional on the synthetic generator, labels, frozen models, and thresholds. Exact group-level binomial bounds are reported separately where relevant.

## 4. Results

The semantic hybrid achieved 520/520 critical recall (100%), 120/120 C4 stale-as-current recall (100%), 0/2,927 C1/C3/C5 legitimate false positives, and 120/120 C7 critical recall. Overall, it flagged 400/6,271 legitimate records (6.38%) and 520/1,680 cases (30.95%). Material-defect AP was 0.565 (95% cluster bootstrap interval 0.562–0.569), Brier score was 0.0339 (0.0319–0.0358), and log loss was 0.0939 (0.0884–0.0992). The 95% bootstrap intervals for critical recall and C4 recall were both 100%–100%; the workload interval was 29.5%–32.4%.

The 400 false alerts consisted of 160 legitimate peers in C2, 120 in C6, and 120 in C7. The pair-level comparator raises review for both sides of a true comparable conflict when it cannot identify which item is corrupted. Frozen CS V2, Logistic Regression, and Deep Sets also reached 100% critical recall but flagged approximately all legitimate records and routed nearly every case to review. Semantic rules alone reached the same point recall with a 10.38% overall legitimate FPR and 37.08% workload.

The full semantic Logistic Regression had 4.8% critical recall and 0% C4 recall. Its no-temporal ablation also had 0% C4 recall. Removing comparability features increased logistic critical recall to 34.4% while increasing overall legitimate FPR to 21.5% and case workload to 63.0%. Because the D1.1 temporal-label audit found missing critical labels in development partitions, these ablations are descriptive and cannot support causal feature-effect claims.

Generator C was independently implemented, but its gold criteria are not independent of the deterministic rules at the construct level. C2/C6/C7 generate conflicts at 2.1-4.2 times the same field tolerances used by the comparator, which treats differences of at least two times tolerance as critical. C4 uses a 180-day critical-staleness criterion also used by the semantic time rule (the generated stale record is 432 days old). The canonical gold and corruption identifiers are not model inputs, so this is target-construct overlap rather than direct hidden-label leakage. It limits the 100% recall result as evidence of external or independently adjudicated generalization.

Four of the five registered acceptance point-estimate criteria were met. The complete comparison against the best frozen baseline is unassessable because the XGBoost baseline is unavailable, so the full criterion package remains incomplete.

## 5. Discussion

The measured synthetic result illustrates why detection and review burden should be reported together. The frozen V3 baselines attained full critical recall on this challenge by flagging almost all evidence, while the hybrid retained full observed recall with a smaller alert and case-review fraction. The hybrid's zero observed alerts on C1/C3/C5 is specific to the registered endpoint and sample. The separate group-level analysis found 0/360 groups with any endpoint false positive; the one-sided 95% exact upper bound for that group event is 0.83%. A conservative equal-group-weighted FPR upper bound was 6.45%. Neither bound covers generator misspecification.

The paired rule flags legitimate peers in same-period contradiction scenarios, showing that semantic comparability alone does not identify the faulty member. Independent adjudication or additional source reliability evidence would be needed to resolve that ambiguity. Further, hybrid recall includes deterministic rules and should not be attributed to learned representations.

## 6. Limitations

All records, labels, and metadata are synthetic. The evaluation supplies structured evidence semantics and does not measure OCR or extraction errors. The finite scenario set and one held-out source pair cannot represent the breadth of financial products and document workflows. Generator C is independent in implementation path, seed, and templates, but its monetary and stale-evidence gold constructs share key criteria with deterministic rules; this target-construct overlap means the 100% recall is not fully independent semantic-criterion validation. It is not direct hidden-label leakage because canonical gold and corruption identifiers are absent from prediction inputs. Separately, 100 D1.1 records identified as stale-as-current by the temporal rule lacked critical labels across training, validation, calibration, and locked development test. This weakens learned temporal feature evidence and makes feature attribution exploratory. The XGBoost runtime blocker prevents complete registered baseline comparison. Bootstrap intervals are conditional on the synthetic process and do not provide real-world uncertainty guarantees.

## 7. Conclusion

On the registered synthetic Generator C data, the frozen semantic hybrid detected all labeled critical records while avoiding alerts on the registered C1/C3/C5 endpoint, with 6.38% overall legitimate-record FPR and 30.95% case review workload. These results are exploratory, not bank validation. A corrected and independently audited development labeling process, successful replay of all registered baselines, and a new independent challenge are required before claims of general improvement. No operational routing or lending authorization follows from these results.

## Data and software availability

Frozen predictions, manifests, evaluation results, reconciled metrics, protocol, model availability status, and presentation tables are in this repository under `reports/evidence-v4.1/`. Prediction, labels, and manifest checksums are captured in the release manifests. Checkout does not consume these research outputs.
""", encoding="utf-8")

    (PITCH / "SLIDE_READY_EVIDENCE.md").write_text("""# Generator C — slide-ready evidence

## Slide 1 — Research question

**Can semantic-aware validation catch critical evidence defects without treating valid differences as contradictions?**

- Context is checked before comparing values: subject, account, field meaning, period, units, gross/net basis, direction, correction lineage, source and verification.
- Generator C is a preregistered, independent synthetic challenge. It is not a bank dataset.

## Slide 2 — Evaluation setup

- 840 customer groups · 1,680 cases · 6,791 structured evidence records.
- 7 registered scenarios, including stale-as-current evidence, true comparable conflicts and a held-out payroll+merchant pair.
- Prediction file, model release and threshold were frozen before C labels were opened.
- 500 scenario-stratified customer-group bootstrap draws; no C-based training or threshold change.
- **Construct-overlap caveat:** C2/C6/C7 generated corruption magnitudes use the same field tolerances as deterministic rules, and the C4 stale criterion shares the 180-day cutoff. This is target-construct overlap, not direct hidden-label leakage; 100% recall is not independent validation of those criteria.

## Slide 3 — Frozen semantic hybrid results

| Metric | Result |
|---|---:|
| Critical recall | **520/520 = 100%** (95% bootstrap: 100%–100%) |
| C4 stale-as-current recall | **120/120 = 100%** (95% bootstrap: 100%–100%) |
| C1/C3/C5 legitimate-discrepancy FPR | **0/2,927 = 0%** |
| Overall legitimate-record FPR | **400/6,271 = 6.38%** |
| Cases sent to review | **520/1,680 = 30.95%** (95% bootstrap: 29.5%–32.4%) |
| Material-defect AP | **0.565** (95% bootstrap: 0.562–0.569) |

Use `figures/generator_c_model_tradeoffs.svg` to compare detection and review burden. Use `figures/generator_c_ablation_tradeoffs.svg` to show the feature ablation outcomes.

## Slide 4 — What the false positives show

- All 400 hybrid false positives are valid peers in comparable-conflict scenarios: 160 in C2, 120 in C6 and 120 in C7.
- The pair-level rule flags both records because it cannot infer which side is corrupted without another adjudication signal.
- The semantic rule baseline also achieved 100% critical recall, with 10.38% overall legitimate FPR and 37.08% case workload.

## Slide 5 — Limits and honest conclusion

- D1.1 audit: 100 stale records were missing critical labels across training, validation, calibration and locked development test. Learned feature-effect claims are exploratory.
- Generator C's monetary and stale-evidence gold constructs overlap with deterministic rule criteria. Describe its 100% recall as performance on the generated constructs, not independent semantic-criterion generalization.
- XGBoost replay was blocked by unavailable `xgboost==3.0.5`; the complete registered baseline criterion is unassessable.
- Structured synthetic metadata was supplied; OCR/extraction and real bank documents were not evaluated.
- **Conclusion:** promising performance on this registered synthetic challenge, with unresolved data-label and runtime blockers. `EVIDENCE_AI_VALIDATION_BLOCKED`; no routing or approval use.

## 30-second talk track

"We froze the semantic hybrid before scoring a synthetic challenge with 840 groups and 6,791 evidence records. It detected 520 of 520 labeled critical defects, including 120 of 120 stale-as-current records, with no alerts on 2,927 valid differences in the registered C1/C3/C5 endpoint. Overall it still flagged 400 valid peer records in true-conflict cases and sent 31% of cases to review. One key limit is that some generated gold criteria share monetary tolerances and stale-age logic with deterministic rules, so the result is not an independent test of those criteria. Our development audit also found 100 missing temporal critical labels, and the frozen XGBoost baseline could not run. This is not real-bank validation or authorization for credit decisions."
""", encoding="utf-8")

    (PITCH / "FIGURE_CAPTIONS.md").write_text("""# Figure captions

## Generator C model trade-offs

Frozen-threshold point estimates for the semantic hybrid, semantic-rule comparator and replayable frozen baselines. Each model is shown on critical recall, overall legitimate-record FPR and case review workload. The hybrid's 100% recall is observed on the synthetic challenge and includes deterministic rules. The frozen XGBoost arms were unavailable and are not imputed.

## Generator C logistic feature ablations

Frozen-threshold critical recall, stale-as-current recall, legitimate-discrepancy FPR, overall legitimate-record FPR and case workload for the full semantic Logistic Regression and three registered feature ablations. The full model and no-temporal ablation both had 0% C4 recall; this comparison does not support a temporal-feature benefit claim. D1.1 development labels were later found inconsistent, so the ablation interpretation is exploratory.
""", encoding="utf-8")

    (PITCH / "JUDGE_QA.md").write_text("""# Likely questions and precise answers

### Is this validated on actual bank documents?

No. Generator C is programmatic synthetic evidence with supplied structured metadata. It does not measure real-document parsing or bank performance.

### What does 100% recall mean here?

The frozen hybrid flagged all 520 records labeled critical in this Generator C release. It flagged all 120 critical stale-as-current records in scenario C4. The estimates are conditional on this generator and label policy.

### Why was the overall false-positive rate not zero?

The hybrid flagged 400 valid peer records in same-period conflict scenarios: 160 in C2, 120 in C6 and 120 in C7. The pair-level rule can detect a comparable conflict but cannot identify which peer is wrong, so both sides are sent for review.

### Did the semantic features cause the improvement?

That conclusion is not supported. The hybrid includes deterministic rules, and an audit found 100 missing critical labels among stale development records. The learned feature effects remain exploratory.

### Is Generator C independent of the deterministic rules?

It is independent in implementation path, seed, and templates, but not fully independent at the semantic-criterion level. C2/C6/C7 use the same field tolerances as the rules, and the C4 gold and time rule share a 180-day stale threshold. This is target-construct overlap, not direct leakage of hidden gold or corruption IDs into prediction inputs. The result does not establish generalization to independently adjudicated criteria.

### Did every registered acceptance criterion pass?

Four of five point-estimate criteria were met. The fifth requires comparison with the best complete frozen baseline, but the frozen XGBoost replay was blocked by the missing `xgboost==3.0.5` dependency. The registered criterion is therefore unassessable.

### Can it route or approve applications?

No. Validation status is `EVIDENCE_AI_VALIDATION_BLOCKED`; the checkout application does not consume Generator C outputs, and routing/approval are unauthorized.
""", encoding="utf-8")

    public_artifacts = [
        "GENERATOR_C_SUMMARY.json", "GENERATOR_C_REPORT.md", "PAPER_DRAFT.md", "README.md",
        "GENERATOR_C_METRICS.json", "GENERATOR_C_SCENARIO_METRICS.csv", "GENERATOR_C_SOURCE_METRICS.csv",
        "GENERATOR_C_PAIRED_BASELINE_COMPARISONS.csv", "GENERATOR_C_GROUP_CLUSTER_UNCERTAINTY.csv",
        "tables/generator_c_model_comparison.csv", "tables/generator_c_ablation_comparison.csv",
        "tables/generator_c_scenario_metrics.csv", "tables/generator_c_paired_baseline_contrasts.csv",
        "tables/generator_c_group_cluster_uncertainty.csv",
        "pitch/SLIDE_READY_EVIDENCE.md", "pitch/FIGURE_CAPTIONS.md", "pitch/JUDGE_QA.md",
        "pitch/figures/generator_c_model_tradeoffs.svg", "pitch/figures/generator_c_ablation_tradeoffs.svg",
    ]
    sources = [
        "data/generator-c-v1/C_PREDICTIONS_FROZEN.csv", "data/generator-c-v1/C_PREDICTION_MANIFEST.json",
        "data/generator-c-v1/C_EVALUATION_MANIFEST.json", "data/generator-c-v1/GENERATOR_C_RESULTS.json",
        "data/generator-c-v1/ABLACTION_STUDY.json", "data/generator-c-v1/dataset_manifest.json",
        "data/generator-c-v1/observed.json", "data/generator-c-v1/gold_labels.json",
        "data/generator-c-v1/LABEL_ACCESS_STATUS.json", "GENERATOR_C_METRICS.json",
        "EXPERIMENT_PROTOCOL_C.md", "experiment_protocol_c.json", "POST_EVALUATION_AUDIT_ADDENDUM.json",
        "models/frozen-v1/frozen_model_manifest.json",
    ]
    manifest = {
        "release_id": summary["release_id"], "created_by": "scripts/finalize_v4_1_reporting.py",
        "status": "READ_ONLY_SYNTHETIC_RESEARCH_RELEASE",
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
        "prediction_sha256": pred_manifest["prediction_sha256"],
        "evaluation_manifest_sha256": sha256(C_DIR / "C_EVALUATION_MANIFEST.json"),
        "model_manifest_sha256": sha256(OUT / "models/frozen-v1/frozen_model_manifest.json"),
        "protocol_sha256": sha256(OUT / "experiment_protocol_c.json"),
        "source_checksums": {rel: sha256(OUT / rel) for rel in sources},
        "artifact_checksums": {rel: sha256(OUT / rel) for rel in public_artifacts},
        "public_artifacts": public_artifacts,
        "public_figures": ["generator_c_model_tradeoffs.svg", "generator_c_ablation_tradeoffs.svg"],
        "routing_authorized": False, "approval_authorized": False,
        "checkout_consumes_research_outputs": False,
    }
    write_json(OUT / "RELEASE_MANIFEST.json", manifest)
    print(json.dumps({"release_id": summary["release_id"], "artifacts": len(public_artifacts),
                      "figures": manifest["public_figures"],
                      "all_previous_aggregate_metrics_match": reconciliation["all_previous_aggregate_metrics_match"],
                      "validation_status": summary["validation_status"]}, indent=2))


if __name__ == "__main__":
    main()
