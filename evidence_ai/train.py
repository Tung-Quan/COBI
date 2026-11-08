"""Train and evaluate the frozen controlled-corruption experiment, never UCI or bank data."""
import argparse
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from shutil import copyfile

import numpy as np
import torch
import xgboost as xgb
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, log_loss
from threadpoolctl import threadpool_limits
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from evidence_ai.evaluation import bootstrap, calibrate, calibrator, lock_threshold, reliability, scores
from evidence_ai.features import GROUPS, NAMES, apply_scaler, build_arrays, fit_scaler
from evidence_ai.model import DeepSets
from evidence_ai.synthetic import CAP, FIELDS, PROTOCOL, freeze
from ml.contracts import ROOT, sha, write_json

RELEASE = ROOT / "reports/evidence-v3"


def now():
    return datetime.now(timezone.utc).isoformat()


def tensors(data, indexes):
    return (torch.from_numpy(data["x"][:, :, indexes]), torch.from_numpy(data["mask"]),
            torch.from_numpy(data["y"].astype(np.float32)), torch.from_numpy(data["fields"]))


def losses(pred, material, fields, mask, aux_weight):
    document_logit, field_logit = pred
    bce = nn.functional.binary_cross_entropy_with_logits
    document_loss = bce(document_logit[mask], material[mask])
    labeled = mask[..., None] & (fields >= 0)
    field_loss = bce(field_logit[labeled], fields[labeled]) if labeled.any() else document_loss.new_zeros(())
    return document_loss, field_loss, document_loss + aux_weight * field_loss


def train_network(train, valid, indexes, seed, params, config, target):
    torch.manual_seed(seed)
    net = DeepSets(len(indexes), params["hidden"], len(FIELDS))
    opt = torch.optim.AdamW(net.parameters(), lr=params["lr"], weight_decay=params["weight_decay"])
    loader = DataLoader(TensorDataset(*tensors(train, indexes)), batch_size=params["batch"], shuffle=True,
                        generator=torch.Generator().manual_seed(seed))
    xv, mv, yv, fv = tensors(valid, indexes)
    best, best_epoch, history = float("inf"), 0, []
    for epoch in range(1, config["neural_max_epochs"] + 1):
        net.train()
        norms, totals, updates = [], np.zeros(3), 0
        for x, mask, y, fields in loader:
            opt.zero_grad(set_to_none=True)
            parts = losses(net(x, mask), y, fields, mask, config["auxiliary_loss_weight"])
            parts[-1].backward()
            norms.append(float(nn.utils.clip_grad_norm_(net.parameters(), 5.0, error_if_nonfinite=True)))
            opt.step()
            updates += len(x)
            totals += np.array([float(part.detach()) for part in parts]) * len(x)
        net.eval()
        with torch.inference_mode():
            validation = [float(part) for part in losses(net(xv, mv), yv, fv, mv, config["auxiliary_loss_weight"])]
        improved = validation[0] < best
        if improved:
            best, best_epoch = validation[0], epoch
            torch.save(net.state_dict(), target)
        stopped = epoch - best_epoch >= config["neural_patience"]
        history.append({"epoch": epoch, "train_document_bce": totals[0] / updates, "train_field_bce": totals[1] / updates,
                        "train_combined_loss": totals[2] / updates, "validation_document_bce": validation[0],
                        "validation_field_bce": validation[1], "validation_combined_loss": validation[2],
                        "gradient_l2_preclip_mean": float(np.mean(norms)), "gradient_l2_preclip_max": max(norms),
                        "optimizer_steps": len(norms), "lr": opt.param_groups[0]["lr"], "batch_size": params["batch"],
                        "checkpoint_sha256": sha(target), "best_epoch": best_epoch,
                        "decision": "STOP_PATIENCE" if stopped else "BEST" if improved else "CONTINUE"})
        if stopped:
            break
    net.load_state_dict(torch.load(target, map_location="cpu", weights_only=True))
    return {"seed": seed, "validation_log_loss": best, "best_epoch": best_epoch, "history": history,
            "file": target.name, "sha256": sha(target)}, net


def network_predict(networks, data, indexes):
    x, mask, _, _ = tensors(data, indexes)
    with torch.inference_mode():
        predictions = [net(x, mask) for net in networks]
        document = np.mean([torch.sigmoid(pred[0]).numpy() for pred in predictions], axis=0)
        fields = np.mean([torch.sigmoid(pred[1]).numpy() for pred in predictions], axis=0)
    return document.astype("float64"), fields.astype("float64")


def padded(mask, values):
    out = np.zeros(mask.shape, dtype=float)
    out[mask] = values
    return out


def run(out):
    config = json.loads(PROTOCOL.read_text())
    observations, labels, split, hashes = freeze(config)
    by_id = {row["case_key"]: row for row in observations}
    cases = {name: [by_id[key] for key in keys] for name, keys in split.items()}
    data = {name: build_arrays(rows, labels) for name, rows in cases.items() if name != "test"}
    write_json(out / "split_manifest.json", {
        "experiment_id": config["experiment_id"], "created_at": now(), "data_sha256": hashes,
        "protocol_sha256": sha(PROTOCOL), "grouping": "customer_group; chronological, no overlap",
        "cohorts": {name: {"cases": len(rows), "groups": len({row["customer_group"] for row in rows}),
                           "start": rows[0]["observed_at"], "end": rows[-1]["observed_at"],
                           "case_keys_sha256": sha256("\n".join(split[name]).encode()).hexdigest()}
                    for name, rows in cases.items()},
    })
    scaler = fit_scaler(data["train"])
    train, validation, calibration = (apply_scaler(data[name], scaler) for name in ("train", "validation", "calibration"))
    mt, mv = train["mask"], validation["mask"]
    xt, yt = train["x"][mt], train["y"][mt]
    xv, yv = validation["x"][mv], validation["y"][mv]
    lr = LogisticRegression(C=config["logistic_C"], solver="lbfgs", max_iter=1000).fit(xt, yt)
    lr_state = {"coefficients": lr.coef_[0].tolist(), "intercept": float(lr.intercept_[0]), "iterations": int(lr.n_iter_[0])}
    write_json(out / "logistic.json", lr_state)
    histories, tree_candidates = [], []
    for depth in config["xgb_depth"]:
        boosters, traces = [], []
        for seed in config["training_seeds"]:
            params = {"objective": "binary:logistic", "eval_metric": "logloss", "max_depth": depth,
                      "eta": config["xgb_learning_rate"], "tree_method": "hist", "seed": seed, "nthread": 1}
            dtrain, dval = xgb.DMatrix(xt, label=yt), xgb.DMatrix(xv, label=yv)
            log = {}
            booster = xgb.train(params, dtrain, config["xgb_rounds"], evals=[(dtrain, "train"), (dval, "validation")],
                                early_stopping_rounds=config["xgb_patience"], evals_result=log, verbose_eval=False)
            best = booster[:booster.best_iteration + 1]
            path = out / f"xgb-d{depth}-s{seed}.json"
            best.save_model(path)
            boosters.append(best)
            traces.append({"seed": seed, "parameters": params, "best_round": booster.best_iteration + 1,
                           "validation_log_loss": log_loss(yv, best.predict(dval)), "history": log,
                           "checkpoint": path.name, "sha256": sha(path)})
        tree_candidates.append((float(np.mean([item["validation_log_loss"] for item in traces])), depth, boosters))
        histories.append({"candidate": f"xgb-d{depth}", "runs": traces})
    _, best_depth, trees = min(tree_candidates, key=lambda row: row[0])

    def train_variant(name, params, indexes):
        runs, networks = [], []
        for seed in config["training_seeds"]:
            target = out / f"{name}-s{seed}.pt"
            record, network = train_network(train, validation, indexes, seed, params, config, target)
            runs.append(record)
            networks.append(network)
        loss = float(np.mean([run["validation_log_loss"] for run in runs]))
        histories.append({"candidate": name, "parameters": params, "runs": runs, "validation_log_loss": loss})
        print(f"{name}: mean validation document log loss={loss:.6f}", flush=True)
        return loss, name, params, indexes, networks, runs

    all_features = list(range(len(NAMES)))
    deep_candidates = [train_variant(f"ds-{i + 1}", params, all_features) for i, params in enumerate(config["deep_sets"])]
    _, selected_name, selected_params, _, nets, runs = min(deep_candidates, key=lambda row: row[0])
    deep_variants = {"M3_DEEP_SETS": (all_features, nets)}
    for group in config["ablate_one_at_a_time"]:
        keep = [i for i, name in enumerate(NAMES) if name not in GROUPS[group]]
        _, _, _, _, networks, _ = train_variant(f"drop-{group}", selected_params, keep)
        deep_variants[f"ABLATE_{group}"] = (keep, networks)
    write_json(out / "training_history.json", histories)

    def predictions(cohort):
        mask = cohort["mask"]
        matrix = xgb.DMatrix(cohort["x"][mask])
        base = {
            "M0_CS_V2": np.broadcast_to(cohort["cs_risk"][:, None], mask.shape),
            "M1_LOGISTIC": padded(mask, expit(cohort["x"][mask] @ lr_state["coefficients"] + lr_state["intercept"])),
            "M2_XGBOOST": padded(mask, np.mean([model.predict(matrix) for model in trees], axis=0)),
        }
        return base | {name: network_predict(models, cohort, indexes)[0] for name, (indexes, models) in deep_variants.items()}

    raw_cal = predictions(calibration)
    models, thresholds, cal_models = {}, {}, {}
    for name, raw in raw_cal.items():
        mask = calibration["mask"]
        params = calibrator(raw[mask], calibration["y"][mask])
        calibrated = calibrate(raw, params)
        threshold = lock_threshold(calibrated[mask], calibration["critical"][mask],
                                   config["calibration_critical_recall_target"])
        thresholds[name] = threshold["threshold"]
        cal_models[name] = params
        models[name] = {"calibrator": params, "threshold_lock": threshold}
    field_cal_p = network_predict(nets, calibration, all_features)[1]
    field_maps = []
    for index in range(len(FIELDS)):
        labels_at = calibration["fields"][:, :, index]
        mask = calibration["mask"] & (labels_at >= 0)
        field_maps.append(calibrator(field_cal_p[:, :, index][mask], labels_at[mask]))
    seed_locks = []
    cmask = calibration["mask"]
    for seed, net in zip(config["training_seeds"], nets, strict=True):
        raw, _ = network_predict([net], calibration, all_features)
        mapping = calibrator(raw[cmask], calibration["y"][cmask])
        threshold = lock_threshold(calibrate(raw[cmask], mapping), calibration["critical"][cmask],
                                   config["calibration_critical_recall_target"])
        seed_locks.append({"seed": seed, "calibrator": mapping, "threshold": threshold["threshold"]})
    model_dir = out / "model"
    model_dir.mkdir()
    for record in runs:
        copyfile(out / record["file"], model_dir / record["file"])
    write_json(model_dir / "preprocessing.json", scaler)
    manifest = {
        "status": "SYNTHETIC_TECHNICAL_ONLY", "purpose": "Research example; no checkout compatibility",
        "experiment_id": config["experiment_id"], "feature_names": NAMES, "source_feature_groups": GROUPS,
        "field_names": FIELDS, "capacity": CAP, "hidden": selected_params["hidden"], "selected_variant": selected_name,
        "seeds": config["training_seeds"], "material_calibrator": cal_models["M3_DEEP_SETS"], "field_calibrators": field_maps,
        "checksums": {p.name: sha(p) for p in sorted(model_dir.iterdir())}, "protocol_sha256": sha(PROTOCOL),
        "frozen_at": now(), "policy_authorized": False, "bank_validated": False,
    }
    write_json(model_dir / "manifest.json", manifest)
    write_json(out / "selection_lock.json", {
        "selected_deep_sets": selected_name, "parameters": selected_params, "xgb_depth": best_depth,
        "all_model_calibrators": cal_models, "all_thresholds": thresholds, "field_calibrators": field_maps,
        "deep_sets_seed_locks": seed_locks,
        "selected_artifacts": manifest["checksums"], "frozen_at": now(),
    })
    print("Selection, calibrators and thresholds frozen. Opening synthetic test once.", flush=True)
    with (out / "test_opened.txt").open("x", encoding="utf-8") as file:
        file.write(now() + "\n")
    test = apply_scaler(build_arrays(cases["test"], labels), scaler)
    raw_test = predictions(test)
    calibrated = {name: calibrate(p, cal_models[name]) for name, p in raw_test.items()}
    groups = [row["customer_group"] for row in cases["test"]]
    intervals, paired = bootstrap(test, calibrated, thresholds, groups, config)
    for name, result in models.items():
        p = calibrated[name]
        result.update(
            test=scores(p, test, thresholds[name]), ci95=intervals[name],
            test_raw={"brier": float(np.mean((raw_test[name][test["mask"]] - test["y"][test["mask"]]) ** 2)),
                      "log_loss": float(log_loss(test["y"][test["mask"]], raw_test[name][test["mask"]]))} if name != "M0_CS_V2" else None,
            reliability=reliability(p[test["mask"]], test["y"][test["mask"]]),
        )
    _, field_test = network_predict(nets, test, all_features)
    field_metrics = {}
    for k, field in enumerate(FIELDS):
        field_label = test["fields"][:, :, k]
        mask = test["mask"] & (field_label >= 0)
        p = calibrate(field_test[:, :, k], field_maps[k])[mask]
        y = field_label[mask]
        field_metrics[field] = {"n": len(y), "errors": int(y.sum()), "average_precision": float(average_precision_score(y, p)),
                                "brier": float(np.mean((p-y) ** 2)), "log_loss": float(log_loss(y, p))}
    group_cut = len(cases["test"]) // 2
    late_only = np.array([row["documents"][0]["template"] == "late-only" for row in cases["test"]])
    subsets = {"late_only_template": late_only, "seen_template": ~late_only,
               "early_test_dates": np.arange(len(late_only)) < group_cut,
               "late_test_dates": np.arange(len(late_only)) >= group_cut}
    subgroup = {key: {name: scores(p, test, thresholds[name], selected[:, None]) for name, p in calibrated.items()
                     if name.startswith("M")} for key, selected in subsets.items()}
    seed_metrics = []
    for locked, net in zip(seed_locks, nets, strict=True):
        p_test, _ = network_predict([net], test, all_features)
        seed_metrics.append({"seed": locked["seed"],
                             "test": scores(calibrate(p_test, locked["calibrator"]), test, locked["threshold"])})

    # Use a validation case for UI explanation; it is synthetic and separate from the locked test.
    row = cases["validation"][0]
    example_data = {key: value[:1] for key, value in validation.items()}
    ep, ef = network_predict(nets, example_data, all_features)
    example = []
    for i, doc in enumerate(row["documents"]):
        reduced = {key: value.copy() for key, value in example_data.items()}
        reduced["mask"][0, i] = False
        reduced_p, _ = network_predict(nets, reduced, all_features)
        neighbors = reduced["mask"][0]
        example.append({
            "source": doc["source"], "material_probability": float(calibrate(ep, cal_models["M3_DEEP_SETS"])[0, i]),
            "field_probabilities": {field: float(calibrate(ef[:, :, k], field_maps[k])[0, i]) for k, field in enumerate(FIELDS)},
            "other_documents_mean_probability_change_without_this_source": float(
                (calibrate(reduced_p, cal_models["M3_DEEP_SETS"])[0, neighbors]
                 - calibrate(ep, cal_models["M3_DEEP_SETS"])[0, neighbors]).mean()),
        })
    report = {
        "experiment_id": config["experiment_id"], "status": "SYNTHETIC_TECHNICAL_ONLY",
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED", "created_at": now(),
        "models": models, "test_field_extraction_heads": field_metrics, "subgroups": subgroup,
        "test_by_deep_sets_seed": seed_metrics, "paired_ci95_deep_sets_minus_baselines": paired,
        "cohorts": json.loads((out / "split_manifest.json").read_text())["cohorts"],
        "selected_deep_sets": selected_name, "selected_parameters": selected_params,
        "bootstrap": {"draws": config["bootstrap_draws"], "unit": "customer_group", "confidence": .95},
        "example": {"case": row["case_key"], "partition": "synthetic validation", "documents": example,
                    "explanation": "Drop one encoded document from the mask with other features fixed. Descriptive model sensitivity."},
        "limitations": ["Generated defects and labels", "No independent bank labels or templates",
                        "Technical estimates are conditional on the generator", "Field extraction is distinct from authenticity"],
    }
    write_json(out / "report.json", report)
    write_json(out / "release.json", {"status": "SYNTHETIC_TECHNICAL_ONLY", "report_sha256": sha(out / "report.json"),
                                      "model_manifest_sha256": sha(model_dir / "manifest.json")})
    print(json.dumps({key: row["test"] for key, row in models.items() if key.startswith("M")}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RELEASE / "synthetic")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    with threadpool_limits(limits=1):
        run(args.out)


if __name__ == "__main__":
    main()
