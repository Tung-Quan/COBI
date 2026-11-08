"""Run the preregistered benchmark once, or explicitly reproduce its frozen run."""

import argparse
import json
import platform
import random
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from shutil import copyfile

import numpy as np
import pandas as pd
import torch
from threadpoolctl import threadpool_limits

from ml.candidates import fit_candidates, raw_predict, select
from ml.contracts import ALLOWLIST, CONTRACT, DOMAIN, HORIZON, ROOT, SIGNATURE, TARGET, sha, write_json
from ml.evaluation import calibrate, evaluate, logistic_calibration
from ml.predict import CANONICAL_RUN, EXPERIMENT_ID, MODEL_ID, load, predict
from ml.preprocessing import fit, transform
from ml.split import LOCK, PROTOCOL, audit_membership, dataset


def now():
    return datetime.now(timezone.utc).isoformat()


def export_model(out, winner, state, calibrator, dataset_manifest, split, config):
    model_dir = out / "model"
    model_dir.mkdir()
    checkpoint = model_dir / ("model" + winner.checkpoint.suffix)
    copyfile(winner.checkpoint, checkpoint)
    write_json(model_dir / "preprocessing.json", state)
    write_json(model_dir / "calibrator.json", calibrator)
    manifest = {
        "model_id": MODEL_ID, "version": config["version"], "selected_candidate": winner.name,
        "family": winner.family, "parameters": winner.parameters, "training_dataset": dataset_manifest,
        "source_domain": DOMAIN, "label_horizon": HORIZON, "target": TARGET, "class_mapping": {"0": "no default", "1": "default"},
        "feature_signature": SIGNATURE, "feature_contract": CONTRACT, "feature_allowlist": ALLOWLIST,
        "calibrated": True, "status": "BENCHMARK_ONLY", "evaluation_status": "PENDING_LOCKED_TEST",
        "human_risk_review": "PENDING_INDEPENDENT_REVIEW", "checkout_compatible": False,
        "split": split, "protocol_sha256": sha(PROTOCOL),
        "code_sha256": {p.name: sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
        "libraries": {name: version(name) for name in ("numpy", "pandas", "scipy", "scikit-learn", "xgboost", "torch")},
        "python": platform.python_version(), "platform": platform.platform(),
        "sha256": {p.name: sha(p) for p in (checkpoint, model_dir / "preprocessing.json", model_dir / "calibrator.json")},
    }
    write_json(model_dir / "model_manifest.json", manifest)
    return manifest


def run(out):
    manifest, data = dataset()
    config = json.loads(PROTOCOL.read_text())
    lock = json.loads(LOCK.read_text())
    if (lock["normalized_sha256"] != manifest["normalized_sha256"] or lock["protocol_sha256"] != sha(PROTOCOL)
            or lock["split_code_sha256"] != sha(Path(__file__).with_name("split.py"))):
        raise ValueError("Split lock differs from frozen data, implementation or protocol")
    membership = lock.pop("membership")
    if lock["split_overlap"] or lock["cohorts"] != audit_membership(data[TARGET], membership, config):
        raise ValueError("Invalid split membership")
    lock["lock_sha256"] = sha(LOCK)
    seed = config["seed"]
    random.seed(seed)
    np.random.seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    train_frame = data.loc[membership["train"], ALLOWLIST]
    state = fit(train_frame)

    def arrays(name):
        return transform(data.loc[membership[name], ALLOWLIST], state), data.loc[membership[name], TARGET].to_numpy()

    train, validation = arrays("train"), arrays("validation")
    candidates = fit_candidates(config, train, validation, out)
    winner = select(candidates, config["minimum_validation_improvement_over_simpler"])
    logistic = min((row for row in candidates if row.family == "logistic"), key=lambda row: row.validation_loss)
    write_json(out / "candidates.json", [{
        "candidate": row.name, "family": row.family, "validation_loss": row.validation_loss,
        "parameters": row.parameters, "history": row.history, "checkpoint_sha256": sha(row.checkpoint),
    } for row in candidates])
    xc, yc = arrays("calibration")
    calibrator = logistic_calibration(yc, raw_predict(winner.family, winner.model, xc))
    if calibrator["slope"] <= 0:
        raise ValueError("Calibration must preserve risk ranking")
    model_manifest = export_model(out, winner, state, calibrator, manifest, lock, config)
    model_dir = out / "model"
    # Round-trip on validation rows before unlocking test.
    sample = data.loc[membership["validation"][:16], ALLOWLIST].to_dict("records")
    restored = predict(load(model_dir), sample, source_domain=DOMAIN, label_horizon=HORIZON, feature_signature=SIGNATURE)
    probe = raw_predict(winner.family, winner.model, validation[0][:16])
    np.testing.assert_allclose(restored["raw"], probe, rtol=1e-6, atol=1e-7)
    np.testing.assert_allclose(restored["calibrated"], calibrate(probe, calibrator), rtol=1e-6, atol=1e-7)
    write_json(out / "selection.json", {
        "selected": winner.name, "logistic": logistic.name, "validation_log_loss": winner.validation_loss,
        "calibrator": calibrator, "calibration_cohort": lock["cohorts"]["calibration"],
        "frozen_at": now(), "frozen_components_sha256": model_manifest["sha256"],
    })
    print(f"Selected {winner.name}. Calibration frozen. Opening test once.", flush=True)
    with (out / ".test-opened").open("x", encoding="utf-8") as marker:
        marker.write(now())
    x_test, y_test = arrays("test")
    raw = raw_predict(winner.family, winner.model, x_test)
    predictions = {
        "dummy": raw_predict("dummy", candidates[0].model, x_test),
        "logistic": raw_predict("logistic", logistic.model, x_test),
        "selected_raw": raw, "selected_calibrated": calibrate(raw, calibrator),
    }
    result = evaluate(y_test, predictions, config)
    test_rows = data.loc[membership["test"], ALLOWLIST]
    train_hashes = pd.util.hash_pandas_object(train_frame, index=False)
    test_hashes = pd.util.hash_pandas_object(test_rows, index=False)
    shift = (test_rows.mean() - train_frame.mean()).abs() / train_frame.std(ddof=0).replace(0, np.nan)
    result["data_diagnostics"] = {
        "test_rows_with_identical_train_predictor_vector": int(test_hashes.isin(train_hashes).sum()),
        "standardized_mean_shift_numeric_features": {name: float(shift[name]) for name in state["numeric_names"]},
        "customer_group_check": "UNAVAILABLE_NO_GROUP_KEY",
        "fairness_status": "DEMOGRAPHIC_EXCLUSION_ONLY_INDEPENDENT_FAIRNESS_REVIEW_PENDING",
    }
    pd.DataFrame({"sample_id": membership["test"], "y": y_test, **predictions}).to_csv(out / "test_predictions.csv", index=False)
    result.update(experiment_id=EXPERIMENT_ID, status="PUBLIC_DATA_BENCHMARKED", selected_candidate=winner.name,
                  feature_signature=SIGNATURE, split=lock, target=TARGET, source_domain=DOMAIN,
                  horizon=HORIZON, calibration=calibrator, evaluated_at=now(), test_predictions_sha256=sha(out / "test_predictions.csv"))
    write_json(out / "report.json", result)
    model_manifest.update(evaluation_status=result["status"], report_sha256=sha(out / "report.json"),
                          test_metrics=result["models"]["selected_calibrated"]["metrics"])
    write_json(model_dir / "model_manifest.json", model_manifest)
    print(json.dumps(result["models"]["selected_calibrated"]["metrics"], indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=CANONICAL_RUN)
    parser.add_argument("--reproduce-locked", action="store_true", help="Reproduce the same protocol, without independent test evidence")
    args = parser.parse_args()
    out = args.out.resolve()
    if out != CANONICAL_RUN and not args.reproduce_locked:
        parser.error("Non-canonical output requires --reproduce-locked and the same frozen protocol")
    if args.reproduce_locked and (out == CANONICAL_RUN or not (CANONICAL_RUN / "report.json").exists()):
        parser.error("Reproduce a completed canonical run into a separate new directory")
    # mkdir provides an exclusive claim and prevents accidental retries after seeing test.
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "status.json", {"status": "RUNNING", "started_at": now()})
    try:
        with threadpool_limits(limits=1):
            run(out)
    except Exception as exc:
        status = "INSUFFICIENT_TEST_EVIDENCE" if "INSUFFICIENT_TEST_EVIDENCE" in str(exc) else "FAILED"
        write_json(out / "status.json", {"status": status, "failed_at": now(), "failure_type": type(exc).__name__})
        raise
    write_json(out / "status.json", {"status": "PUBLIC_DATA_BENCHMARKED", "completed_at": now(),
                                     "reproduction": args.reproduce_locked})


if __name__ == "__main__":
    main()
