"""Read-only, fail-closed view of the synthetic COBI Evidence AI V4.1 study."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .research import ROOT, digest

router = APIRouter(prefix="/api/evidence-ai/v4.1", tags=["evidence research"])
BLOCKED = "EVIDENCE_AI_VALIDATION_BLOCKED"
OUT = ROOT / "reports/evidence-v4.1"
METRICS = OUT / "GENERATOR_C_METRICS.json"
RELEASE = OUT / "RELEASE_MANIFEST.json"
PUBLIC_FIGURES = {
    "generator_c_model_tradeoffs.svg", "generator_c_ablation_tradeoffs.svg",
}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _verified_metrics():
    try:
        release = _json(RELEASE)
        metrics = _json(METRICS)
        prediction_manifest = _json(OUT / "data/generator-c-v1/C_PREDICTION_MANIFEST.json")
        evaluation_manifest = _json(OUT / "data/generator-c-v1/C_EVALUATION_MANIFEST.json")
        dataset_manifest = _json(OUT / "data/generator-c-v1/dataset_manifest.json")
        presentation_summary = _json(OUT / "GENERATOR_C_SUMMARY.json")
        model_manifest = OUT / "models/frozen-v1/frozen_model_manifest.json"
        frozen_release = _json(OUT / "models/frozen-v1/frozen_release.json")
        predictions = OUT / "data/generator-c-v1/C_PREDICTIONS_FROZEN.csv"
        for relative, expected in release["source_checksums"].items():
            path = OUT / relative
            if not path.is_file() or digest(path) != expected:
                raise ValueError("V4.1 research source checksum mismatch")
        for relative, expected in release["artifact_checksums"].items():
            path = OUT / relative
            if not path.is_file() or digest(path) != expected:
                raise ValueError("V4.1 research artifact checksum mismatch")
        if (release.get("validation_status") != BLOCKED
                or release.get("status") != "READ_ONLY_SYNTHETIC_RESEARCH_RELEASE"
                or release.get("prediction_sha256") != digest(predictions)
                or release.get("model_manifest_sha256") != digest(model_manifest)
                or frozen_release.get("manifest_sha256") != digest(model_manifest)
                or prediction_manifest.get("prediction_sha256") != digest(predictions)
                or metrics.get("prediction_sha256") != digest(predictions)
                or metrics.get("prediction_freeze_verified") is not True
                or metrics.get("models_or_thresholds_changed") is not False
                or evaluation_manifest.get("prediction_sha256") != digest(predictions)
                or evaluation_manifest.get("gold_labels_sha256")
                    != release["source_checksums"].get("data/generator-c-v1/gold_labels.json")
                or evaluation_manifest.get("results_sha256", {}).get("GENERATOR_C_RESULTS.json")
                    != release["source_checksums"].get("data/generator-c-v1/GENERATOR_C_RESULTS.json")
                or dataset_manifest.get("file_sha256", {}).get("observed.json")
                    != release["source_checksums"].get("data/generator-c-v1/observed.json")
                or dataset_manifest.get("file_sha256", {}).get("gold_labels.json")
                    != release["source_checksums"].get("data/generator-c-v1/gold_labels.json")
                or presentation_summary.get("release_id") != release.get("release_id")
                or release.get("routing_authorized") is not False
                or release.get("approval_authorized") is not False
                or release.get("checkout_consumes_research_outputs") is not False):
            raise ValueError("V4.1 research release integrity check failed")
        for filename, expected in frozen_release.get("artifact_sha256", {}).items():
            artifact = model_manifest.parent / filename
            if not artifact.is_file() or digest(artifact) != expected:
                raise ValueError("V4.1 frozen model artifact checksum mismatch")
        return metrics, release, presentation_summary
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(503, "Verified V4.1 research summary unavailable.") from exc


@router.get("/summary")
def summary():
    metrics, release, presentation_summary = _verified_metrics()
    hybrid = metrics["aggregate_metrics"]["SEMANTIC_HYBRID"]
    intervals = metrics["bootstrap"]["intervals_by_model"]["SEMANTIC_HYBRID"]
    selected_models = (
        "SEMANTIC_HYBRID", "SEMANTIC_RULE", "SEMANTIC_LOGISTIC", "SEMANTIC_DEEP_SETS",
        "ABLATION_NO_TEMPORAL", "ABLATION_NO_COMPARABILITY", "ABLATION_NO_SOURCE_PROVENANCE",
        "M0_CS_V2", "M1_LOGISTIC", "M2_XGBOOST", "M3_DEEP_SETS",
    )
    models = {}
    for model in selected_models:
        item = metrics["aggregate_metrics"].get(model)
        models[model] = {
            "availability": metrics["model_availability"].get(model, "NOT_EVALUATED"),
            "metrics": item,
        }
    scenarios = []
    for row in metrics["scenario_metrics"]:
        if row.get("model") == "SEMANTIC_HYBRID":
            scenarios.append({key: row.get(key) for key in (
                "scenario", "documents", "material_defect_support", "material_tp", "material_fn",
                "legitimate_support", "legitimate_fp", "legitimate_tn", "critical_support",
                "critical_tp", "critical_fn", "critical_recall", "critical_fnr",
                "legitimate_discrepancy_support_c1_c3_c5", "legitimate_discrepancy_fp_c1_c3_c5",
                "legitimate_discrepancy_fpr_c1_c3_c5", "c4_stale_critical_support",
                "c4_stale_tp", "c4_stale_fn", "c4_stale_as_current_recall",
                "case_count", "flagged_case_count", "case_review_workload",
                "material_average_precision", "brier_score", "log_loss",
            )})
    sources = []
    for row in metrics["source_metrics"]:
        if row.get("model") == "SEMANTIC_HYBRID":
            sources.append({key: row.get(key) for key in (
                "source_type", "documents", "critical_tp", "critical_support", "critical_recall",
                "legitimate_fp", "legitimate_support", "overall_legitimate_fpr",
                "case_count", "flagged_case_count", "case_review_workload",
            )})
    frozen_model = _json(OUT / "models/frozen-v1/frozen_model_manifest.json")
    frozen_artifacts = _json(OUT / "models/frozen-v1/frozen_release.json")["artifact_sha256"]
    model_artifacts = []
    for model, specification in frozen_model.get("models", {}).items():
        model_path = (specification.get("artifact") or {}).get("weights")
        if model_path:
            filename = Path(model_path).name
            model_artifacts.append({"model": model, "path": model_path,
                                    "sha256": frozen_artifacts[filename]})
    return {
        "status": "POST_UNBLINDING_EXPLORATORY",
        "validation_status": BLOCKED,
        "routing_authorized": False,
        "approval_authorized": False,
        "read_only": True,
        "synthetic_only": True,
        "release": release,
        "protocol_id": metrics.get("protocol_id"),
        "dataset": metrics.get("dataset"),
        "prediction_sha256": metrics.get("prediction_sha256"),
        "model_manifest_sha256": digest(OUT / "models/frozen-v1/frozen_model_manifest.json"),
        "model_artifacts": model_artifacts,
        "frozen_threshold": hybrid.get("frozen_threshold"),
        "semantic_hybrid": hybrid,
        "semantic_hybrid_group_bootstrap_95": intervals,
        "boundary_uncertainty": metrics.get("boundary_uncertainty"),
        "models": models,
        "scenarios": scenarios,
        "sources": sources,
        "false_positive_breakdown": presentation_summary.get("false_positive_breakdown", []),
        "acceptance": presentation_summary.get("acceptance", {}),
        "data_quality_audit": presentation_summary.get("data_quality_audit", {}),
        "label_rule_overlap": presentation_summary.get("label_rule_overlap", {}),
        "artifacts": release["public_artifacts"],
        "figures": release["public_figures"],
        "limitations": [
            "Generator C labels were already opened; this is a post-unblinding frozen-output reconciliation.",
            "A development temporal-label inconsistency was found and weakens learned-feature attribution.",
            "Generator C's monetary and stale-evidence gold constructs overlap with deterministic rule criteria; this is construct overlap, not direct hidden-label leakage.",
            "All evidence and labels are synthetic; no real-bank validation or regulatory validation exists.",
            "XGBoost branches are NOT_EVALUATED because the frozen runtime dependency is unavailable offline.",
        ],
    }


@router.get("/figures/{filename}")
def figure(filename: str):
    if filename not in PUBLIC_FIGURES:
        raise HTTPException(404, "Unknown V4.1 research figure.")
    _, release, _ = _verified_metrics()
    if filename not in release.get("public_figures", []):
        raise HTTPException(404, "V4.1 research figure is not in the verified release.")
    path = OUT / "pitch/figures" / filename
    if not path.is_file():
        raise HTTPException(404, "V4.1 research figure unavailable.")
    return FileResponse(path, filename=filename, media_type="image/svg+xml")


@router.get("/artifacts/{filename:path}")
def artifact(filename: str):
    _, release, _ = _verified_metrics()
    if filename not in release.get("public_artifacts", []):
        raise HTTPException(404, "Unknown V4.1 research artifact.")
    path = OUT / filename
    if not path.is_file():
        raise HTTPException(404, "V4.1 research artifact unavailable.")
    return FileResponse(path, filename=Path(filename).name)
