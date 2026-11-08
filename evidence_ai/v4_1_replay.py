"""Verify V4.1 frozen artifacts and deterministic D locked-test replay."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import torch

from evidence_ai.semantic_evidence import FEATURE_NAMES, case_feature_array, semantic_validation
from evidence_ai.v4_1_generator_dev import OUT as DEV
from evidence_ai.v4_1_training import DeepSetsContext, _apply_platt, _json, _sigmoid
from ml.contracts import ROOT, sha

MODEL_DIR = ROOT / "reports/evidence-v4.1/models/frozen-v1"
PREDICTION_PATH = ROOT / "reports/evidence-v4.1/DEVELOPMENT_TEST_PREDICTIONS.json"


def _flat_scores(model_entry, x, mask, indexes):
    indexes = np.asarray(indexes, dtype=int)
    feature_indexes = model_entry["feature_indices"]
    preprocess = model_entry["artifact"]["preprocess"]
    selected = x[indexes][..., feature_indexes].astype(np.float64)
    scaled = ((selected - np.asarray(preprocess["mean"])) / np.asarray(preprocess["scale"])).astype(np.float32)
    local_mask = mask[indexes]
    scaled[~local_mask] = 0.0
    if model_entry["kind"] == "logistic":
        model_path = ROOT / model_entry["artifact"]["weights"]
        model = joblib.load(model_path)
        return model.predict_proba(scaled[local_mask])[:, 1]
    if model_entry["kind"] == "deepsets":
        model = DeepSetsContext(len(feature_indexes), int(preprocess["hidden"]))
        model.load_state_dict(torch.load(ROOT / model_entry["artifact"]["weights"], map_location="cpu", weights_only=True))
        model.eval()
        with torch.no_grad():
            logits = model(torch.from_numpy(scaled), torch.from_numpy(local_mask)).cpu().numpy()
        return _sigmoid(np.concatenate([logits[i, :int(local_mask[i].sum())] for i in range(len(indexes))]))
    raise ValueError(f"Unsupported frozen kind: {model_entry['kind']}")


def replay():
    release = _json(MODEL_DIR / "frozen_release.json")
    manifest_path = MODEL_DIR / "frozen_model_manifest.json"
    manifest = _json(manifest_path)
    if release["manifest_sha256"] != sha(manifest_path):
        raise ValueError("Frozen model manifest checksum mismatch")
    for filename, digest in release["artifact_sha256"].items():
        if sha(MODEL_DIR / filename) != digest:
            raise ValueError(f"Frozen artifact checksum mismatch: {filename}")
    if "frozen_release.json" in release["artifact_sha256"]:
        raise ValueError("Release manifest must not hash itself")
    if manifest["validation_status"] != "EVIDENCE_AI_VALIDATION_BLOCKED" or manifest["routing_authorized"]:
        raise ValueError("V4.1 release safety contract mismatch")
    if manifest["feature_names"] != list(FEATURE_NAMES):
        raise ValueError("Feature contract mismatch")

    cases = _json(DEV / "observed.json")
    split = _json(DEV / "split_locked_test.json")["case_ids"]
    index_by_id = {case["case_id"]: i for i, case in enumerate(cases)}
    indexes = np.asarray([index_by_id[case_id] for case_id in split], dtype=int)
    selected_cases = [cases[i] for i in indexes]
    x_all, mask_all, _ = case_feature_array(cases, capacity=6)
    x, mask = x_all[indexes], mask_all[indexes]

    raw_by_model = {}
    for name, entry in manifest["models"].items():
        if entry.get("kind") in {"logistic", "deepsets"}:
            raw_by_model[name] = _flat_scores(entry, x, mask, np.arange(len(indexes)))
    rule_rows = []
    for case in selected_cases:
        out = semantic_validation(case)
        rule_rows.extend(float(out["documents"][record["record_id"]]["score"]) for record in case["records"])
    raw_by_model["SEMANTIC_RULE"] = np.asarray(rule_rows, dtype=float)

    expected = _json(PREDICTION_PATH)["rows"]
    expected_by_model = {}
    for row in expected:
        expected_by_model.setdefault(row["model"], {})[row["record_id"]] = row
    results = {}
    for name, raw in raw_by_model.items():
        entry = manifest["models"][name]
        if entry["kind"] == "semantic_rule":
            scores = raw
        else:
            scores = _apply_platt(raw, entry["calibrator"])
        cursor = 0
        max_error = 0.0
        for case in selected_cases:
            for record in case["records"]:
                observed = expected_by_model[name][record["record_id"]]["score"]
                max_error = max(max_error, abs(float(scores[cursor]) - observed))
                cursor += 1
        if cursor != len(scores) or max_error > 1e-7:
            raise ValueError(f"Replay mismatch for {name}; max_abs_error={max_error}")
        results[name] = {"documents_replayed": cursor, "max_absolute_score_error": max_error}

    base_name = manifest["models"]["SEMANTIC_HYBRID"]["base_model"]
    hybrid_entry = manifest["models"]["SEMANTIC_HYBRID"]
    rule = raw_by_model["SEMANTIC_RULE"]
    hybrid = _apply_platt(np.maximum(raw_by_model[base_name], rule), hybrid_entry["calibrator"])
    cursor, max_error = 0, 0.0
    for case in selected_cases:
        for record in case["records"]:
            expected_score = expected_by_model["SEMANTIC_HYBRID"][record["record_id"]]["score"]
            max_error = max(max_error, abs(float(hybrid[cursor]) - expected_score))
            cursor += 1
    if max_error > 1e-7:
        raise ValueError(f"Hybrid replay mismatch; max_abs_error={max_error}")
    results["SEMANTIC_HYBRID"] = {"documents_replayed": cursor, "max_absolute_score_error": max_error}
    return {"status": "PASS", "release_id": manifest["release_id"],
            "frozen_artifacts_verified": len(release["artifact_sha256"]),
            "generator_c_loaded": manifest["generator_c_loaded"],
            "model_replay": results}


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2))
