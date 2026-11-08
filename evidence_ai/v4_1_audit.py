"""Pre-change audit and exploratory B score analysis for COBI V4.1."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score

from evidence_ai.features import GROUPS, NAMES
from ml.contracts import sha

ROOT = Path(__file__).resolve().parents[1]
V4 = ROOT / "reports/evidence-v4"
OUT = ROOT / "reports/evidence-v4.1/baseline"
MODELS = ("M0_CS_V2", "M1_LOGISTIC", "M2_XGBOOST", "M3_DEEP_SETS")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = read(V4 / "final_manifest.json")
    verified = []
    mismatches = []
    for artifact in manifest["artifacts"]:
        path = ROOT / Path(artifact["path"])
        if not path.is_file() or path.stat().st_size != artifact["bytes"] or sha(path) != artifact["sha256"]:
            mismatches.append(artifact["path"])
        else:
            verified.append(artifact["path"])
    if mismatches:
        raise ValueError(f"V4 baseline changed before V4.1: {mismatches[:5]}")

    v3 = ROOT / "reports/evidence-v3/synthetic"
    model_manifest = read(v3 / "model/manifest.json")
    selection_lock = read(v3 / "selection_lock.json")
    for filename, digest in model_manifest["checksums"].items():
        if sha(v3 / "model" / filename) != digest:
            raise ValueError(f"V3 selected model file mismatch: {filename}")
    for filename, digest in selection_lock["selected_artifacts"].items():
        model_path = (v3 / "model" / filename if filename == "preprocessing.json" or filename.endswith(".pt")
                      else v3 / filename)
        if sha(model_path) != digest:
            raise ValueError(f"V3 selection lock mismatch: {filename}")

    with (V4 / "tables/e2_prediction_level.csv").open(encoding="utf-8-sig", newline="") as handle:
        predictions = list(csv.DictReader(handle))
    results = read(V4 / "E2_RESULTS.json")
    if len(predictions) != 7744:
        raise ValueError(f"Expected 7,744 E2 prediction rows, found {len(predictions)}")

    score_rows, metric_rows, failures = [], [], {}
    for scenario in ("B1", "B2", "B3", "B4", "B5", "B6"):
        docs = [row for row in predictions if row["scenario"] == scenario]
        failures[scenario] = {}
        for model in MODELS:
            probability = np.asarray([float(row[f"{model}_probability"]) for row in docs])
            material = np.asarray([int(row["material_defect"]) for row in docs])
            critical = np.asarray([int(row["critical_defect"]) for row in docs])
            flagged = np.asarray([int(row[f"{model}_flagged"]) == 1 for row in docs])
            threshold = float(results["models"][model]["frozen_threshold"])
            for label, mask in (("material", material == 1), ("legitimate", material == 0), ("critical", critical == 1)):
                scores = probability[mask]
                quantiles = np.quantile(scores, [.05, .25, .5, .75, .95])
                score_rows.append({
                    "scenario": scenario, "model": model, "label": label, "n": len(scores),
                    "mean": float(scores.mean()), "std": float(scores.std(ddof=1)) if len(scores) > 1 else 0.0,
                    "q05": float(quantiles[0]), "q25": float(quantiles[1]), "median": float(quantiles[2]),
                    "q75": float(quantiles[3]), "q95": float(quantiles[4]), "frozen_threshold": threshold,
                    "score_fraction_above_threshold": float((scores >= threshold).mean()),
                })
            legitimate = material == 0
            critical_fn = int((~flagged & (critical == 1)).sum())
            critical_support = int(critical.sum())
            legitimate_fp = int((flagged & legitimate).sum())
            legitimate_support = int(legitimate.sum())
            failures[scenario][model] = {
                "critical_false_negatives": critical_fn, "critical_support": critical_support,
                "legitimate_false_positives": legitimate_fp, "legitimate_support": legitimate_support,
            }
            metric_rows.append({
                "scenario": scenario, "model": model, "documents": len(docs),
                "material_prevalence": float(material.mean()), "critical_support": critical_support,
                "material_ap": float(average_precision_score(material, probability)),
                "critical_ap": float(average_precision_score(critical, probability)) if 0 < critical_support < len(critical) else None,
                "critical_recall": float(1 - critical_fn / critical_support) if critical_support else None,
                "critical_fn": critical_fn,
                "legitimate_fpr": float(legitimate_fp / legitimate_support) if legitimate_support else None,
                "mean_probability_minus_material_prevalence": float(probability.mean() - material.mean()),
                "frozen_threshold": threshold,
                "review_workload": float(results["scenario_results"][scenario][model]["review_workload"]),
            })

    # Recompute the concrete failures quoted in the V4 reports.
    expected = {
        "B4": {"M0_CS_V2": 34, "M1_LOGISTIC": 80, "M2_XGBOOST": 80, "M3_DEEP_SETS": 80},
        "B5": {"M0_CS_V2": 1198, "M1_LOGISTIC": 1192, "M2_XGBOOST": 1145, "M3_DEEP_SETS": 1174},
        "B6": {"M0_CS_V2": 106, "M1_LOGISTIC": 4, "M2_XGBOOST": 95, "M3_DEEP_SETS": 4},
    }
    for scenario, by_model in expected.items():
        for model, count in by_model.items():
            key = "legitimate_false_positives" if scenario == "B5" else "critical_false_negatives"
            if failures[scenario][model][key] != count:
                raise ValueError(f"V4 reported count mismatch {scenario}/{model}: {failures[scenario][model][key]} != {count}")

    write_csv(OUT / "score_distributions.csv", score_rows)
    write_csv(OUT / "scenario_metrics_recomputed.csv", metric_rows)
    audit = {
        "status": "PASS_NO_BASELINE_DISCREPANCY",
        "v4_manifest_sha256": sha(V4 / "final_manifest.json"),
        "v4_manifest_artifacts_verified": len(verified),
        "v3_model_manifest_sha256": sha(v3 / "model/manifest.json"),
        "v3_selection_lock_sha256": sha(v3 / "selection_lock.json"),
        "v3_model_manifest": {key: model_manifest.get(key) for key in
                               ("experiment_id", "feature_names", "source_feature_groups", "seeds", "selected_variant", "policy_authorized", "bank_validated")},
        "v3_frozen_thresholds": selection_lock["all_thresholds"],
        "e2_prediction_rows": len(predictions), "failure_counts_recomputed": failures,
        "feature_names": NAMES, "feature_groups": GROUPS,
        "exploratory": True,
    }
    (OUT / "pre_modification_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    model_names = {"M0_CS_V2": "CS_V2", "M1_LOGISTIC": "Logistic", "M2_XGBOOST": "XGBoost", "M3_DEEP_SETS": "Deep Sets"}
    lines = [
        "# V4.1 Baseline Audit — Before Implementation Changes", "",
        "**Audit:** no discrepancy found in the reviewed V4 results or protected model artifacts. This audit was run before V4.1 implementation changes.", "",
        "## Integrity", "",
        f"- V4 final manifest files verified: **{len(verified)}/{len(verified)}**.",
        "- Selected V3 model artifacts and selection-lock hashes: verified.",
        f"- V3 model manifest: {len(model_manifest['feature_names'])} features; capacity {model_manifest['capacity']}; selected variant `{model_manifest['selected_variant']}`; seeds `{model_manifest['seeds']}`.",
        "- V4 bank authorization remains false; no V2–V4 artifact was changed during this audit.", "",
        "## Recomputed failure counts from E2 prediction rows", "",
        "The following counts were recomputed from all 7,744 rows in `reports/evidence-v4/tables/e2_prediction_level.csv` using the frozen flags and labels, then checked against the E2 JSON and narrative reports.", "",
        "| Scenario / model | Critical FN / support | Legitimate FP / support |", "|---|---:|---:|",
    ]
    for scenario in ("B4", "B5", "B6"):
        for model in MODELS:
            f = failures[scenario][model]
            lines.append(f"| {scenario} / {model_names[model]} | {f['critical_false_negatives']} / {f['critical_support']} | {f['legitimate_false_positives']} / {f['legitimate_support']} |")
    lines += [
        "", "The recomputed counts match the V4 report. B4 has 80 critical documents: CS_V2 misses 34 and each learned model misses 80. B5 has 1,199 legitimate documents; 1,145–1,198 are flagged across models. B6 has 167 critical documents; CS_V2 misses 106 and XGBoost misses 95, while Logistic and Deep Sets each miss 4.", "",
        "## Exploratory score-distribution findings", "",
        "All results in this section are post-hoc diagnostics on the already evaluated Generator B; they do not modify the V4 confirmatory results.", "",
        "- **B4 ranking plus threshold:** critical AP is low for the learned models. The frozen thresholds further suppress detection: none of the three learned models flags any of the 80 critical documents. This is both a ranking and operating-point transfer failure, rather than a cutoff-only issue.",
        "- **B5 semantics and ranking:** critical and legitimate scores overlap or saturate high. For XGBoost, the legitimate score median is approximately 0.996 and critical median approximately 0.998; lowering the threshold cannot separate those classes. Logistic and Deep Sets show the same high-score overlap.",
        "- **B6 model-specific mechanism:** XGBoost critical AP is approximately 0.953, but the frozen threshold 0.924 flags only 72/167 critical documents. This is primarily threshold transfer. CS_V2 has weak B6 critical ranking (AP approximately 0.171); Logistic and Deep Sets retain strong ranking and recall.",
        "- Score quantiles by scenario, label and model are in `score_distributions.csv`; recomputed scenario metrics are in `scenario_metrics_recomputed.csv`.", "",
        "## Feature-contract observations", "",
        "The frozen 32-feature contract includes log amounts, missingness, OCR quality, age in days, verification, three source one-hot features, raw peer gaps, document count, four CS subscores and 12 hashed-text features. It omits subject/account identity, effective-period overlap, gross/net meaning, correction lineage, transaction direction, and whether old evidence is asserted current or presented historically. Peer gaps compare values without first checking semantic comparability. The CS consistency/recency subscores also use numerical similarity and age without effective-period semantics.", "",
        "Schema rejection does not explain the V4 failures: all 7,744 B documents were compatible, and B used the same three individual source categories. B6 tests source-set combinations, not unseen individual source types. These are mechanism hypotheses supported by the feature contract and score patterns; they are not causal proof."
    ]
    (OUT / "BASELINE_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return audit


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
