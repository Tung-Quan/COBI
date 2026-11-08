"""Read-only audit of the frozen COBI V2 release. Run as a module from the repository root."""
from __future__ import annotations

import csv
import gc
import io
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import numpy as np
import pandas as pd
import torch
import xgboost as xgb
from fastapi.testclient import TestClient
from scipy.special import expit
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from threadpoolctl import threadpool_limits

from backend.app import db
from backend.app.main import app
from ml.candidates import raw_predict, select
from ml.contracts import ALLOWLIST, DOMAIN, FILENAME, HORIZON, ROOT, SIGNATURE, STATUS, TARGET, sha, write_json
from ml.evaluation import evaluate, log_odds, metrics
from ml.net import network
from ml.predict import CANONICAL_RUN as RUN, MODEL_ID, load, predict
from ml.preprocessing import fit, transform
from ml.split import CSV, DATASET, LOCK, PROTOCOL, assignments, audit_membership, dataset
from scripts.fetch_uci import normalize

OUT = Path(__file__).resolve().parent
SERIES = ["dummy", "logistic", "selected_raw", "selected_calibrated"]
KEYS = ["roc_auc", "average_precision", "brier", "log_loss"]
PAIRS = [("logistic", "dummy"), ("selected_raw", "dummy"), ("selected_calibrated", "dummy"),
         ("selected_raw", "logistic"), ("selected_calibrated", "logistic"),
         ("selected_calibrated", "selected_raw")]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def source_integrity(manifest, data):
    raw = ROOT / "data/raw"
    inputs = {
        "original_sha256": raw / FILENAME,
        "raw_archive_sha256": raw / "uci350.zip",
        "raw_csv_sha256": raw / "uci350-official.csv",
        "license_snapshot_sha256": raw / "uci350-card.html",
        "normalized_sha256": CSV,
    }
    actual = {key: sha(path) for key, path in inputs.items()}
    assert all(actual[key] == manifest[key] for key in actual)
    with ZipFile(inputs["raw_archive_sha256"]) as archive:
        xls = archive.read(FILENAME)
    assert xls == inputs["original_sha256"].read_bytes()
    excel = normalize(pd.read_excel(io.BytesIO(xls), header=1, engine="xlrd"))
    original = normalize(pd.read_csv(inputs["raw_csv_sha256"]))
    pd.testing.assert_frame_equal(excel, original)
    pd.testing.assert_frame_equal(original.set_index("ID")[data.columns], data)
    return actual


def candidate_audit(candidates, xv, yv):
    details = []
    for row in candidates:
        name, family, params, history = (row[key] for key in ("candidate", "family", "parameters", "history"))
        path = RUN / "checkpoints" / (name + (".pt" if family == "mlp" else ".json"))
        assert sha(path) == row["checkpoint_sha256"]
        result = {"candidate": name, "family": family, "parameters": params, "checkpoint": path.relative_to(ROOT).as_posix(),
                  "checkpoint_sha256": sha(path), "steps_logged": len(history)}
        if family == "mlp":
            architecture = params["architecture"]
            model = network(architecture["inputs"], architecture["hidden"])
            model.load_state_dict(torch.load(path, weights_only=True, map_location="cpu"))
            model.eval()
            batches = pd.read_csv(RUN / f"batch-{name}.csv")
            assert batches["update"].tolist() == list(range(1, len(batches) + 1))
            for epoch in history:
                group = batches[batches.epoch == epoch["step"]]
                assert group.batch_rows.sum() == 18000 and len(group) == epoch["epoch_updates"]
                np.testing.assert_allclose(np.average(group.train_bce, weights=group.batch_rows), epoch["train_loss"], atol=1e-9)
                np.testing.assert_allclose(group.gradient_l2_pre_clip.mean(), epoch["gradient_l2_pre_clip_mean"], atol=1e-9)
                np.testing.assert_allclose(group.gradient_l2_pre_clip.max(), epoch["gradient_l2_pre_clip_max"], atol=1e-9)
            assert history[-1]["optimizer_updates"] == len(batches)
            result.update(best_step=params["best_epoch"], optimizer_updates=len(batches),
                          last_batch_rows=int(batches.batch_rows.iloc[-1]), best_epoch_trace=history[params["best_epoch"] - 1])
        elif family == "xgb":
            model = xgb.Booster(params={"nthread": 1})
            model.load_model(path)
            training_trees = int(params["resolved_config"]["learner"]["gradient_booster"]["gbtree_model_param"]["num_trees"])
            assert training_trees == len(history) == min(params["max_rounds"], params["rounds"] + params["patience"])
            assert model.num_boosted_rounds() == params["rounds"]
            result.update(best_step=params["rounds"], training_trees=training_trees,
                          persisted_trees=model.num_boosted_rounds(), best_round_trace=history[params["rounds"] - 1])
        else:
            model = read(path)
            if family == "logistic":
                assert params["iterations"] < params["max_iter"]
                result.update(best_step=params["iterations"], terminal_trace=history[0])
        measured = log_loss(yv, raw_predict(family, model, xv))
        np.testing.assert_allclose(measured, row["validation_loss"], atol=1e-8, rtol=0)
        result.update(validation_log_loss=float(measured))
        details.append(result)
    return details


def primary(y, p):
    return np.array([roc_auc_score(y, p), average_precision_score(y, p), brier_score_loss(y, p), log_loss(y, p)])


def paired_analysis(y, prediction_arrays, repetitions=1000, seed=43):
    """Additional paired metrics. Relative changes use the second series as denominator."""
    point = np.array([primary(y, prediction_arrays[k]) for k in SERIES])
    rng = np.random.default_rng(seed)
    draws = np.empty((repetitions, len(SERIES), len(KEYS)))
    for i in range(repetitions):
        indices = rng.integers(len(y), size=len(y))
        draws[i] = [primary(y[indices], prediction_arrays[k][indices]) for k in SERIES]
    comparisons = []
    for a, b in PAIRS:
        i, j = SERIES.index(a), SERIES.index(b)
        diff = point[i] - point[j]
        draws_diff = draws[:, i, :] - draws[:, j, :]
        rel = 100 * diff / point[j]
        rel_draws = 100 * draws_diff / draws[:, j, :]
        comparisons.append({"first": a, "reference": b, "metrics": {
            key: {"delta": float(diff[k]), "relative_pct": float(rel[k]),
                  "delta_ci95": np.quantile(draws_diff[:, k], [.025, .975]).tolist(),
                  "relative_pct_ci95": np.quantile(rel_draws[:, k], [.025, .975]).tolist()}
            for k, key in enumerate(KEYS)
        }})
    return comparisons


def duplicate_analysis(data, membership, test):
    vectors = {name: pd.MultiIndex.from_frame(data.loc[ids, ALLOWLIST]) for name, ids in membership.items()}
    full = pd.MultiIndex.from_frame(data[ALLOWLIST])
    in_train = vectors["test"].isin(vectors["train"])
    in_dev = vectors["test"].isin(vectors["train"].union(vectors["validation"]).union(vectors["calibration"]))
    result = {
        "all_excess": int(full.duplicated().sum()),
        "test_matching_train": int(in_train.sum()),
        "test_matching_validation": int(vectors["test"].isin(vectors["validation"]).sum()),
        "test_matching_calibration": int(vectors["test"].isin(vectors["calibration"]).sum()),
        "test_matching_any_development": int(in_dev.sum()),
        "test_internal_excess": int(vectors["test"].duplicated().sum()),
        "test_matching_train_pct": float(100 * in_train.mean()),
        "distinct_vectors_all": int(full.nunique()),
        "subsets": {},
    }
    for label, mask in [("full", np.ones(len(test), dtype=bool)), ("unseen_in_train", ~in_train),
                        ("unseen_in_development", ~in_dev), ("seen_in_train", in_train)]:
        rows = test.loc[mask]
        y = rows.y.to_numpy()
        entry = {"n": len(rows), "events": int(y.sum()), "prevalence": float(y.mean())}
        predictions = {name: rows[name].to_numpy() for name in SERIES}
        entry["metrics"] = {name: dict(zip(KEYS, primary(y, p).tolist())) for name, p in predictions.items()}
        # Descriptive bootstrap for the calibrated-minus-raw loss only. No reselection.
        delta = np.logaddexp(0, log_odds(predictions["selected_calibrated"])) - y * log_odds(predictions["selected_calibrated"])
        delta -= np.logaddexp(0, log_odds(predictions["selected_raw"])) - y * log_odds(predictions["selected_raw"])
        samples = np.random.default_rng(43).integers(len(rows), size=(1000, len(rows)))
        entry["calibrated_minus_raw_log_loss"] = {
            "delta": float(delta.mean()), "ci95": np.quantile(delta[samples].mean(axis=1), [.025, .975]).tolist()}
        result["subsets"][label] = entry
    return result


def explain(booster, state, frame, xv):
    validation_matrix = xgb.DMatrix(xv)
    shap = booster.predict(validation_matrix, pred_contribs=True).astype("float64")
    margin = booster.predict(validation_matrix, output_margin=True)
    np.testing.assert_allclose(shap.sum(axis=1), margin, atol=1e-5, rtol=0)
    numeric_names, status_names, categories = (state[key] for key in ("numeric_names", "status_names", "status_categories"))
    encoded_names = numeric_names + [f"{field}={code}" for field in status_names for code in categories]
    contribution = {field: shap[:, i] for i, field in enumerate(numeric_names)}
    for i, field in enumerate(status_names):
        start = len(numeric_names) + i * len(categories)
        contribution[field] = shap[:, start:start + len(categories)].sum(axis=1)
    grouped = pd.DataFrame(contribution)
    np.testing.assert_allclose(grouped.sum(axis=1) + shap[:, -1], margin, atol=1e-5, rtol=0)
    top = grouped.abs().mean().sort_values(ascending=False)
    local = []
    # Select rows by the min/max PAY_0 attribution. Ordinals refer to sorted validation IDs.
    for label, offset in [("lowest_PAY_0_attribution", int(grouped.PAY_0.idxmin())),
                          ("highest_PAY_0_attribution", int(grouped.PAY_0.idxmax()))]:
        row = grouped.iloc[offset]
        local.append({"example": label, "validation_ordinal_1_based": offset + 1, "PAY_0": int(frame.iloc[offset].PAY_0),
                      "raw_probability": float(expit(margin[offset])), "raw_margin": float(margin[offset]),
                      "base_margin": float(shap[offset, -1]), "grouped_attributions": row.to_dict()})
    gain = {encoded_names[int(feature[1:])]: float(value) for feature, value in booster.get_score(importance_type="gain").items()}
    effect = []
    for code in categories:
        supported = int((frame.PAY_0 == code).sum())
        if not supported:
            continue
        altered = frame.copy()
        altered["PAY_0"] = code
        p = booster.predict(xgb.DMatrix(transform(altered, state)))
        effect.append({"code": code, "observed_n": supported, "average_raw_probability": float(p.mean())})
    return {
        "validation_n": len(frame), "max_margin_additivity_error": float(np.max(np.abs(shap.sum(axis=1) - margin))),
        "mean_abs_grouped_shap": top.to_dict(), "native_encoded_mean_split_gain": dict(sorted(gain.items(), key=lambda x: -x[1])),
        "examples": local, "pay_0_partial_dependence": effect,
    }, grouped


def check_workbench_math(trace):
    inputs, assessment = trace["inputs"], trace["assessment"]
    income = np.array(inputs["monthly_income_vnd"], dtype=float)
    mean, sd, p25 = float(income.mean()), float(income.std()), float(np.quantile(income, .25))
    debt, essentials = inputs["existing_monthly_debt_vnd"], inputs["essential_monthly_expenses_vnd"]
    evidence = inputs["evidence"]
    score = (.30 * len(income) / 12 + .30 * evidence["reconciliation_fields_consistent"]
             / evidence["reconciliation_fields_total"] + .20 * np.exp(-evidence["age_days"] / 40)
             + .20 * evidence["verified_sources"] / evidence["available_sources"])
    dti, cv = debt / mean, sd / mean
    dti_cap, residual_cap = .35 * mean - debt, (p25 - essentials - debt) * .75
    capacity = min(dti_cap, residual_cap)
    assert inputs["purchase_amount_vnd"] == inputs["loan_amount_vnd"] + inputs["own_funds_vnd"]
    assert inputs["annual_interest_rate"] == 0
    pmt = inputs["loan_amount_vnd"] / inputs["term_months"]
    demo_score = expit(-3.5 + 3 * dti + 1.5 * cv)
    measured = [assessment["features"][key] for key in ("mean_income_vnd", "income_standard_deviation_vnd",
                                                       "income_p25_vnd", "income_cv", "existing_dti_ratio")]
    measured.extend(assessment["affordability"][key] for key in ("dti_capacity_vnd", "residual_capacity_vnd",
                                                               "stressed_payment_capacity_vnd", "pmt_vnd",
                                                               "repayment_buffer_vnd"))
    measured += [assessment["confidence"]["score"], assessment["risk"]["score"], assessment["expected_loss"]["amount_vnd"]]
    expected = [mean, sd, p25, cv, dti, dti_cap, residual_cap, capacity, pmt, capacity - pmt,
                score, demo_score, demo_score * .45 * inputs["loan_amount_vnd"]]
    np.testing.assert_allclose(measured, expected, rtol=1e-12, atol=1e-12)
    routes = trace["routing"]["route_comparison"]
    least_cost = min((row for row in routes if row["eligible"]), key=lambda row: row["estimated_cost_vnd"])
    assert least_cost["route"] == trace["routing"]["recommended_route"] == "FAST_TRACK_CANDIDATE"


def api_checks(test_rows, saved_test):
    old_path = db.DB_PATH
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        db.DB_PATH = Path(temp) / "evidence.sqlite"
        try:
            with TestClient(app) as client:
                url = f"/api/research/models/{MODEL_ID}/predict"
                payload = {"rows": test_rows.iloc[:100].to_dict("records"), "source_domain": DOMAIN,
                           "label_horizon": HORIZON, "feature_signature": SIGNATURE}
                response = client.post(url, json=payload)
                assert response.status_code == 200, response.text
                assert response.json()["risk_source"] == "PUBLIC_BENCHMARK_ONLY"
                raw_diff = float(np.max(np.abs(response.json()["raw"] - saved_test.selected_raw.iloc[:100].to_numpy())))
                cal_diff = float(np.max(np.abs(response.json()["calibrated"] - saved_test.selected_calibrated.iloc[:100].to_numpy())))
                assert max(raw_diff, cal_diff) < 1e-7
                bad = client.post(url, json={**payload, "rows": [{"existing_monthly_debt_vnd": 1000000}]})
                assert bad.status_code == 422 and bad.json()["detail"] == "PD_UNAVAILABLE_SCHEMA_MISMATCH"
                detail = client.get("/api/assessments/DEMO-001/explanation").json()
                check_workbench_math(detail)
                baseline = client.post("/api/assessments/simulate", json={"application_id": "DEMO-001"}).json()
                mismatch = client.post("/api/assessments/simulate",
                                       json={"application_id": "DEMO-001", "benchmark_model_id": MODEL_ID}).json()
                assert mismatch["assessment"]["pd_status"] == "PD_UNAVAILABLE_SCHEMA_MISMATCH"
                assert mismatch["assessment"]["checkout_pd"] is None
                assert mismatch["assessment"]["risk"] == baseline["assessment"]["risk"]
                assert mismatch["routing"] == baseline["routing"]
                reviewed = client.post("/api/applications/DEMO-001/review",
                                       json={"action": "confirm_route", "reason": "Verified the synthetic demonstration trace."}).json()
                assert reviewed["loan_approval_created"] is False
                revoked = client.post("/api/applications/DEMO-001/revoke-consent",
                                      json={"reason": "Synthetic consent withdrawal for evidence audit."})
                assert revoked.status_code == 200
                blocked = client.post("/api/assessments/simulate", json={"application_id": "DEMO-001", "consent": True}).json()
                assert blocked["assessment"]["scoring_performed"] is False and blocked["assessment"]["risk"] is None
                assert blocked["routing"]["eligible_routes"] == ["HOLD_FOR_HUMAN_HANDLING"]
                detail["verified_review_event"] = reviewed["event"]
                detail["verified_hold_after_revocation"] = blocked["routing"]["recommended_route"]
        finally:
            db.DB_PATH = old_path
            gc.collect()
    return detail, {"n_api_rows": 100, "raw_api_max_error": raw_diff, "calibrated_api_max_error": cal_diff,
                    "incompatible_research_api_http_status": 422, "checkout_mismatch_status": "PD_UNAVAILABLE_SCHEMA_MISMATCH",
                    "mismatch_route_unchanged": True}


def main():
    torch.set_num_threads(1)
    manifest, data = dataset()
    source_hashes = source_integrity(manifest, data)
    lock, config = read(LOCK), read(PROTOCOL)
    members = lock["membership"]
    report, candidates = read(RUN / "report.json"), read(RUN / "candidates.json")
    selected = read(RUN / "selection.json")
    artifact = load(RUN / "model")
    model_manifest, booster, state, calibrator = artifact
    assert model_manifest["report_sha256"] == sha(RUN / "report.json")
    assert selected["frozen_components_sha256"] == model_manifest["sha256"]
    assert lock["protocol_sha256"] == model_manifest["protocol_sha256"] == sha(PROTOCOL)
    assert report["split"]["lock_sha256"] == sha(LOCK)
    assert {name: sha(ROOT / "ml" / name) for name in model_manifest["code_sha256"]} == model_manifest["code_sha256"]
    assert members == assignments(data[TARGET], config)
    assert audit_membership(data[TARGET], members, config) == report["split"]["cohorts"]
    assert selected["selected"] == select([SimpleNamespace(name=r["candidate"], **r) for r in candidates],
                                         config["minimum_validation_improvement_over_simpler"]).name
    assert pd.Timestamp(lock["locked_at"]) < pd.Timestamp(selected["frozen_at"]) <= pd.Timestamp(report["evaluated_at"])
    train_frame = data.loc[members["train"], ALLOWLIST]
    fitted_train_state = fit(train_frame)  # Recompute summary moments only, no model training.
    assert state == fitted_train_state and state["fit_rows"] == len(train_frame)
    assert set(data[TARGET]) == {0, 1} and int(data.isna().sum().sum()) == 0
    validation = data.loc[members["validation"], ALLOWLIST]
    xv = transform(validation, state)
    assert xv.shape == (4500, 85) and xv.dtype == np.float32
    candidate_checks = candidate_audit(candidates, xv, data.loc[members["validation"], TARGET].to_numpy())
    checkpoint = RUN / "checkpoints" / (selected["selected"] + ".json")
    assert sha(checkpoint) == sha(RUN / "model/model.json")
    selected_check = next(row for row in candidate_checks if row["candidate"] == selected["selected"])
    test_path = RUN / "test_predictions.csv"
    assert sha(test_path) == report["test_predictions_sha256"]
    test = pd.read_csv(test_path, float_precision="round_trip")
    assert test.sample_id.tolist() == members["test"]
    y = test.y.to_numpy()
    np.testing.assert_array_equal(y, data.loc[members["test"], TARGET])
    test_frame = data.loc[members["test"], ALLOWLIST]
    reloaded = predict(artifact, test_frame.to_dict("records"), source_domain=DOMAIN, label_horizon=HORIZON,
                       feature_signature=SIGNATURE)
    errors = {k: float(np.max(np.abs(reloaded[k] - test[f"selected_{k}"].to_numpy()))) for k in ("raw", "calibrated")}
    assert max(errors.values()) < 1e-7
    pred = {k: test[k].to_numpy() for k in SERIES}
    train_y = data.loc[members["train"], TARGET].to_numpy()
    np.testing.assert_array_equal(pred["dummy"], np.repeat(train_y.mean(), len(test)))
    lr = read(RUN / "checkpoints" / (selected["logistic"] + ".json"))
    np.testing.assert_allclose(pred["logistic"], raw_predict("logistic", lr, transform(test_frame, state)), atol=1e-10, rtol=0)
    for name, p in pred.items():
        expected = report["models"][name]["metrics"]
        np.testing.assert_allclose(primary(y, p), [expected[key]["estimate"] for key in KEYS], atol=1e-10, rtol=0)
    print("Verified source hashes, locked membership, train-only scaler, 11 validation checkpoints and 4,500 reloaded test predictions.", flush=True)
    reproduced = evaluate(y, pred, config)
    ci_diff = 0.0
    for name in SERIES:
        for key, value in reproduced["models"][name]["metrics"].items():
            saved = report["models"][name]["metrics"][key]
            ci_diff = max(ci_diff, float(np.max(np.abs(np.subtract(value["ci95"], saved["ci95"])))))
            np.testing.assert_allclose(value["estimate"], saved["estimate"], atol=1e-8, rtol=0)
        assert reproduced["models"][name]["reliability"] == report["models"][name]["reliability"]
    assert ci_diff < 1e-7
    for a, b in zip(reproduced["paired_log_loss"], report["paired_log_loss"], strict=True):
        assert a["comparison"] == b["comparison"]
        np.testing.assert_allclose(a["ci95"], b["ci95"], atol=1e-8, rtol=0)
    print("Reproduced all published test point metrics, reliability bins and 1,000-draw paired bootstrap CIs.", flush=True)
    comparisons = paired_analysis(y, pred)
    duplicates = duplicate_analysis(data, members, test)
    assert duplicates["all_excess"] == manifest["duplicate_predictor_rows"]
    assert duplicates["test_matching_train"] == report["data_diagnostics"]["test_rows_with_identical_train_predictor_vector"]
    explanations, grouped = explain(booster, state, validation, xv)
    workbench, checks = api_checks(test_frame, test)
    audit = {
        "experiment_id": report["experiment_id"], "audited_existing_release": True, "training_replayed": False,
        "hashes": source_hashes | {"model": sha(RUN / "model/model.json"), "report": sha(RUN / "report.json"),
                                 "test_predictions": sha(test_path), "split_lock": sha(LOCK)},
        "dataset": {"rows": len(data), "source_features": manifest["source_features"], "model_source_features": len(ALLOWLIST),
                    "encoded_inputs": xv.shape[1], "missing_cells": 0, "cohorts": report["split"]["cohorts"]},
        "candidates": candidate_checks, "selection": selected, "test_metrics": report["models"],
        "published_bootstrap_max_ci_endpoint_error": ci_diff, "additional_paired_comparisons": comparisons,
        "parity": checks | {"n_reloaded_test_rows": len(test), "raw_artifact_max_error": errors["raw"],
                            "calibrated_artifact_max_error": errors["calibrated"], "training_trees": selected_check["training_trees"],
                            "persisted_trees": booster.num_boosted_rounds(), "effective_iteration_range": [0, 210]},
        "duplicates": duplicates, "explainability": explanations, "workbench": workbench,
    }
    write_json(OUT / "audit_summary.json", audit)
    with (OUT / "test_comparisons.csv").open("w", newline="", encoding="utf-8") as file:
        table = csv.writer(file)
        table.writerow(["first", "reference", "metric", "delta", "delta_ci95_low", "delta_ci95_high",
                        "relative_pct", "relative_ci95_low", "relative_ci95_high"])
        for pair in comparisons:
            for key, item in pair["metrics"].items():
                table.writerow([pair["first"], pair["reference"], key, item["delta"], *item["delta_ci95"],
                                item["relative_pct"], *item["relative_pct_ci95"]])
    from .plot_evidence import render
    render(audit, test, candidates, grouped)
    print("Verified duplicate sensitivity, TreeSHAP additivity, API parity, schema rejection and DEMO-001 trace.", flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        main()


