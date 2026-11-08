"""Replay only local controlled research data through frozen V3 artifacts."""
import json
from pathlib import Path

import numpy as np
import torch
import xgboost as xgb
from scipy.special import expit

from evidence_ai.evaluation import calibrate, scores
from evidence_ai.features import NAMES, apply_scaler, build_arrays
from evidence_ai.model import DeepSets
from evidence_ai.synthetic import DATA, FIELDS
from evidence_ai.train import RELEASE, network_predict, padded
from ml.contracts import sha


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_deep_sets(directory):
    manifest = read(directory / "manifest.json")
    if (manifest["status"] != "SYNTHETIC_TECHNICAL_ONLY" or manifest["feature_names"] != NAMES
            or manifest["bank_validated"] or manifest["policy_authorized"]):
        raise ValueError("Model is outside the controlled evidence contract")
    states = [f"{manifest['selected_variant']}-s{seed}.pt" for seed in manifest["seeds"]]
    if set(manifest["checksums"]) != {"preprocessing.json", *states}:
        raise ValueError("Incomplete model artifact")
    if any(Path(name).name != name or sha(directory / name) != checksum
           for name, checksum in manifest["checksums"].items()):
        raise ValueError("Evidence artifact checksum mismatch")
    nets = []
    for name in states:
        network = DeepSets(len(NAMES), manifest["hidden"], len(FIELDS))
        network.load_state_dict(torch.load(directory / name, map_location="cpu", weights_only=True))
        nets.append(network.eval())
    return manifest, read(directory / "preprocessing.json"), nets


def predict_frozen(cases, targets, directory):
    manifest, scaler, nets = load_deep_sets(directory / "model")
    data = apply_scaler(build_arrays(cases, targets), scaler)
    lock = read(directory / "selection_lock.json")
    mask = data["mask"]
    base = read(directory / "logistic.json")
    trees = []
    for seed in manifest["seeds"]:
        tree = xgb.Booster(params={"nthread": 1})
        tree.load_model(directory / f"xgb-d{lock['xgb_depth']}-s{seed}.json")
        trees.append(tree)
    encoded = xgb.DMatrix(data["x"][mask])
    raw_deep, raw_field = network_predict(nets, data, list(range(len(NAMES))))
    raw = {"M0_CS_V2": np.broadcast_to(data["cs_risk"][:, None], mask.shape),
           "M1_LOGISTIC": padded(mask, expit(data["x"][mask] @ base["coefficients"] + base["intercept"])),
           "M2_XGBOOST": padded(mask, np.mean([model.predict(encoded) for model in trees], axis=0)),
           "M3_DEEP_SETS": raw_deep}
    return data, {name: calibrate(p, lock["all_model_calibrators"][name]) for name, p in raw.items()}, raw_field, lock


def main():
    torch.set_num_threads(1)
    directory = RELEASE / "synthetic"
    cases = read(DATA / "observed.json")
    targets = read(DATA / "technical_labels.json")
    test_ids = set(read(DATA / "locked_split.json")["test"])
    data, p, _, lock = predict_frozen([case for case in cases if case["case_key"] in test_ids], targets, directory)
    report = read(directory / "report.json")
    for name, scores_at in p.items():
        result = scores(scores_at, data, lock["all_thresholds"][name])
        for key, value in result.items():
            np.testing.assert_allclose(value, report["models"][name]["test"][key], rtol=1e-7, atol=1e-8)
    print("Verified all four frozen model test metrics from reloaded checkpoints, scaler and calibration.")


if __name__ == "__main__":
    main()
