"""Score Generator C observations with frozen models without reading C labels."""
from __future__ import annotations

from hashlib import sha256
import csv
import json
from pathlib import Path

import joblib
import numpy as np
import torch

from evidence_ai.features import NAMES as LEGACY_FEATURE_NAMES, build_arrays as build_legacy_arrays
from evidence_ai.model import DeepSets as LegacyDeepSets
from evidence_ai.semantic_evidence import case_feature_array, semantic_validation
from evidence_ai.v4_1_replay import _flat_scores
from evidence_ai.v4_1_training import _apply_platt, _json, _sigmoid, _semantic_rule
from ml.contracts import ROOT, canonical, sha, write_json

C_DIR = ROOT / "reports/evidence-v4.1/data/generator-c-v1"
V41_MODEL_DIR = ROOT / "reports/evidence-v4.1/models/frozen-v1"
V3_DIR = ROOT / "reports/evidence-v3/synthetic"
PREDICTION_CSV = C_DIR / "C_PREDICTIONS_FROZEN.csv"


def _legacy_projection(cases):
    projected, dummy_labels = [], []
    for case in cases:
        documents, targets = [], []
        for record in case["records"]:
            values = {field: None for field in ("income", "debt", "purchase")}
            values[record["field_type"]] = record["normalized_value"]
            document = {"document_key": record["record_id"], "source": record["source_type"],
                        "template": "semantic-evidence-v1", "values": values, "age_days": record["age_days"],
                        "verified": record["verification_status"] == "VERIFIED", "ocr_quality": record["ocr_quality"],
                        "text": record["text"].lower(), "observed_at": record["observed_at"]}
            documents.append(document)
            targets.append({"document_key": record["record_id"],
                            "observed_payload_sha256": sha256(canonical(document)).hexdigest(),
                            "material_evidence_error": 0, "critical_evidence_error": 0,
                            "field_extraction_error": {field: 0 for field in ("income", "debt", "purchase")}})
        projected.append({"case_key": case["case_id"], "customer_group": case["customer_group"],
                          "observed_at": case["request"]["requested_at"], "income_history_months": 12,
                          "documents": documents})
        dummy_labels.append({"case_key": case["case_id"], "documents": targets})
    return projected, dummy_labels


def _legacy_raw(cases):
    release_dir = V3_DIR
    model_dir = release_dir / "model"
    manifest = _json(model_dir / "manifest.json")
    lock = _json(release_dir / "selection_lock.json")
    if manifest["feature_names"] != LEGACY_FEATURE_NAMES:
        raise ValueError("V3 feature contract mismatch")
    for filename, digest in manifest["checksums"].items():
        if sha(model_dir / filename) != digest:
            raise ValueError(f"V3 artifact checksum mismatch: {filename}")
    projected, dummy_labels = _legacy_projection(cases)
    data = build_legacy_arrays(projected, dummy_labels)
    scaler = _json(model_dir / "preprocessing.json")
    x = ((data["x"] - np.asarray(scaler["mean"])) / np.asarray(scaler["scale"])).astype(np.float32)
    x[~data["mask"]] = 0
    flat = x[data["mask"]]
    logistic = _json(release_dir / "logistic.json")
    raw = {
        "M0_CS_V2": data["cs_risk"][..., None].repeat(data["mask"].shape[1], axis=1)[data["mask"]],
        "M1_LOGISTIC": _sigmoid(flat @ np.asarray(logistic["coefficients"]) + float(logistic["intercept"])),
    }
    networks = []
    for seed in manifest["seeds"]:
        network = LegacyDeepSets(len(LEGACY_FEATURE_NAMES), manifest["hidden"], len(manifest["field_names"]))
        network.load_state_dict(torch.load(model_dir / f"{manifest['selected_variant']}-s{seed}.pt",
                                           map_location="cpu", weights_only=True))
        networks.append(network.eval())
    with torch.no_grad():
        tensor = torch.from_numpy(x)
        mask_tensor = torch.from_numpy(data["mask"])
        logits = np.mean([network(tensor, mask_tensor)[0].cpu().numpy() for network in networks], axis=0)
    raw["M3_DEEP_SETS"] = _sigmoid(logits[data["mask"]])
    calibrated = {name: _apply_platt(scores, lock["all_model_calibrators"][name]) for name, scores in raw.items()}
    return calibrated, lock


def predict():
    torch.set_num_threads(1)
    manifest = _json(C_DIR / "dataset_manifest.json")
    observed_path = C_DIR / "observed.json"
    if sha(observed_path) != manifest["file_sha256"]["observed.json"]:
        raise ValueError("Generator C observed data hash mismatch")
    release_path = V41_MODEL_DIR / "frozen_release.json"
    release = _json(release_path)
    model_manifest_path = V41_MODEL_DIR / "frozen_model_manifest.json"
    frozen = _json(model_manifest_path)
    if sha(model_manifest_path) != release["manifest_sha256"]:
        raise ValueError("Frozen V4.1 manifest hash mismatch")
    if manifest["model_release_sha256"] != sha(release_path):
        raise ValueError("Generator C was not registered against this frozen model release")
    if frozen["generator_c_loaded"] or not release["frozen_before_generator_c"]:
        raise ValueError("V4.1 model release is not frozen before C")
    cases = _json(observed_path)

    # Build every feature vector from the observed file only.
    x, mask, _ = case_feature_array(cases, capacity=6)
    all_indexes = np.arange(len(cases))
    raw_v41 = {}
    for name, entry in frozen["models"].items():
        if entry.get("kind") in {"logistic", "deepsets"}:
            raw_v41[name] = _flat_scores(entry, x, mask, all_indexes)
    rule_scores, rule_explanations = _semantic_rule(cases)
    rule_flat = np.concatenate([row[:int(mask[i].sum())] for i, row in enumerate(rule_scores)])
    raw_v41["SEMANTIC_RULE"] = rule_flat

    hybrid = frozen["models"]["SEMANTIC_HYBRID"]
    base_name = hybrid["base_model"]
    hybrid_scores = _apply_platt(np.maximum(raw_v41[base_name], rule_flat), hybrid["calibrator"])
    calibrated_v41 = {}
    for name, raw in raw_v41.items():
        if name == "SEMANTIC_RULE":
            calibrated_v41[name] = raw
        else:
            calibrated_v41[name] = _apply_platt(raw, frozen["models"][name]["calibrator"])
    calibrated_v41["SEMANTIC_HYBRID"] = hybrid_scores

    legacy_scores, legacy_lock = _legacy_raw(cases)
    availability = {}
    for name, entry in frozen["models"].items():
        availability[name] = "BLOCKED_DEPENDENCY" if entry.get("status") == "BLOCKED_DEPENDENCY" else "AVAILABLE"
    availability.update({name: "AVAILABLE" for name in legacy_scores})
    availability["M2_XGBOOST"] = "BLOCKED_DEPENDENCY"

    semantic_explanations = []
    explanation_by_record = {}
    for case in cases:
        result = semantic_validation(case)
        explanation_by_record.update({record["record_id"]: {
            "alerts": result["documents"][record["record_id"]]["alerts"],
            "time_validity": result["documents"][record["record_id"]]["time_validity"],
            "comparisons": [pair for pair in result["comparisons"] if record["record_id"] in
                            {pair["left_record_id"], pair["right_record_id"]}],
        } for record in case["records"]})
        semantic_explanations.append({"case_id": case["case_id"], "comparisons": result["comparisons"]})

    model_scores = {**legacy_scores, **calibrated_v41}
    threshold_lookup = {name: entry.get("threshold") for name, entry in frozen["models"].items()
                       if entry.get("threshold") is not None}
    threshold_lookup.update({name: float(value) for name, value in legacy_lock["all_thresholds"].items()
                             if name in legacy_scores})
    rows = []
    for model_name, scores in model_scores.items():
        if model_name == "SEMANTIC_RULE":
            threshold_lookup[model_name] = .5
        threshold = threshold_lookup[model_name]
        cursor = 0
        for case in cases:
            for record in case["records"]:
                score = float(scores[cursor])
                rows.append({"model": model_name, "case_id": case["case_id"],
                             "customer_group": case["customer_group"], "scenario": case["scenario"],
                             "record_id": record["record_id"], "source_type": record["source_type"],
                             "score": score, "score_kind": "DETERMINISTIC_RULE_SIGNAL" if model_name == "SEMANTIC_RULE" else "CALIBRATED_PROBABILITY",
                             "threshold": threshold, "flagged": bool(score >= threshold)})
                cursor += 1
        if cursor != len(scores):
            raise ValueError(f"Prediction/document alignment mismatch: {model_name}")

    fieldnames = list(rows[0])
    with PREDICTION_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    explanations_path = C_DIR / "C_SEMANTIC_EXPLANATIONS.json"
    write_json(explanations_path, {"status": "FROZEN_PRE_LABEL_EVALUATION",
               "records": explanation_by_record, "case_comparisons": semantic_explanations})
    prediction_manifest = {
        "status": "PREDICTIONS_FROZEN_LABELS_NOT_OPENED",
        "generator_c_manifest_sha256": sha(C_DIR / "dataset_manifest.json"),
        "observed_sha256": sha(observed_path), "frozen_model_release_sha256": sha(release_path),
        "model_manifest_sha256": sha(model_manifest_path), "prediction_sha256": sha(PREDICTION_CSV),
        "predictor_source_sha256": sha(Path(__file__)),
        "explanation_sha256": sha(explanations_path), "prediction_rows": len(rows),
        "case_count": len(cases), "document_count": sum(len(case["records"]) for case in cases),
        "model_availability": availability, "routing_authorized": False, "approval_authorized": False,
        "checkout_consumes_research_outputs": False,
    }
    write_json(C_DIR / "C_PREDICTION_MANIFEST.json", prediction_manifest)
    write_json(C_DIR / "LABEL_ACCESS_STATUS.json", {
        "labels_opened_for_evaluation": False, "predictions_frozen": True,
        "prediction_sha256": prediction_manifest["prediction_sha256"],
        "prediction_manifest_sha256": sha(C_DIR / "C_PREDICTION_MANIFEST.json"),
        "status": "READY_FOR_ONE_TIME_LABEL_EVALUATION",
    })
    return prediction_manifest


if __name__ == "__main__":
    print(json.dumps(predict(), indent=2))
