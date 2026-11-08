"""Read checksummed local artifacts and predict only within the signed UCI contract."""

import argparse
import json
from pathlib import Path

from ml.contracts import DOMAIN, FEATURES, HORIZON, ROOT, SIGNATURE, sha

EXPERIMENT_ID = "uci350-v2.0"
CANONICAL_RUN = ROOT / "reports/final" / EXPERIMENT_ID
MODEL_ID = "uci350-v2.0-selected"
MISMATCH = "PD_UNAVAILABLE_SCHEMA_MISMATCH"


def load_manifest(directory):
    manifest = json.loads((directory / "model_manifest.json").read_text(encoding="utf-8"))
    if (manifest["feature_signature"], manifest["source_domain"], manifest["label_horizon"],
        manifest["status"], manifest["model_id"]) != (SIGNATURE, DOMAIN, HORIZON, "BENCHMARK_ONLY", MODEL_ID):
        raise ValueError(MISMATCH)
    expected_model = "model.pt" if manifest["family"] == "mlp" else "model.json"
    if set(manifest["sha256"]) != {expected_model, "preprocessing.json", "calibrator.json"}:
        raise ValueError("Incomplete model checksums")
    for filename, digest in manifest["sha256"].items():
        if sha(directory / filename) != digest:
            raise ValueError(f"Corrupted model artifact: {filename}")
    return manifest


def load(directory):
    import torch
    import xgboost as xgb

    from ml.net import network

    manifest = load_manifest(directory)
    family = manifest["family"]
    if family == "xgb":
        model = xgb.Booster(params={"nthread": 1})
        model.load_model(directory / "model.json")
    elif family == "mlp":
        architecture = manifest["parameters"]["architecture"]
        model = network(architecture["inputs"], architecture["hidden"])
        model.load_state_dict(torch.load(directory / "model.pt", weights_only=True, map_location="cpu"))
        model.eval()
    elif family in {"logistic", "dummy"}:
        model = json.loads((directory / "model.json").read_text())
    else:
        raise ValueError("Unknown model family")
    preprocessing = json.loads((directory / "preprocessing.json").read_text())
    calibrator = json.loads((directory / "calibrator.json").read_text())
    return manifest, model, preprocessing, calibrator


def predict(artifact, rows, *, source_domain, label_horizon, feature_signature):
    import pandas as pd

    from ml.candidates import raw_predict
    from ml.evaluation import calibrate
    from ml.preprocessing import transform

    manifest, model, state, calibrator = artifact
    if (source_domain, label_horizon, feature_signature) != (DOMAIN, HORIZON, manifest["feature_signature"]):
        raise ValueError(MISMATCH)
    names = [field["name"] for field in FEATURES]
    if not rows:
        raise ValueError(MISMATCH)
    for row in rows:
        if set(row) != set(names):
            raise ValueError(MISMATCH)
        for feature in FEATURES:
            value = row[feature["name"]]
            low, high = feature["bounds"]
            if type(value) is not int or not low <= value <= high:
                raise ValueError(MISMATCH)
    x = transform(pd.DataFrame(rows, columns=names), state)
    raw = raw_predict(manifest["family"], model, x)
    return {"risk_source": "PUBLIC_BENCHMARK_ONLY", "raw": raw.tolist(), "calibrated": calibrate(raw, calibrator).tolist()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path, help="JSON containing rows, source_domain, label_horizon and feature_signature")
    parser.add_argument("--artifact", type=Path, default=CANONICAL_RUN / "model",
                        help="Trusted local artifact directory")
    args = parser.parse_args()
    print(json.dumps(predict(load(args.artifact), **json.loads(args.request.read_text(encoding="utf-8")))))


if __name__ == "__main__":
    main()
