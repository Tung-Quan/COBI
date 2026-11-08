"""Candidate search receives train and validation arrays only."""

import csv
import json
from dataclasses import dataclass
from itertools import product

import numpy as np
import torch
import xgboost as xgb
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from ml.contracts import sha, write_json
from ml.net import network


@dataclass
class Candidate:
    name: str
    family: str
    checkpoint: object
    parameters: dict
    history: list
    validation_loss: float
    model: object


def raw_predict(family, model, x):
    if family == "dummy":
        return np.full(len(x), model["prevalence"])
    if family == "logistic":
        return expit(x.astype("float64") @ model["coefficients"] + model["intercept"])
    if family == "xgb":
        return model.predict(xgb.DMatrix(x)).astype("float64")
    with torch.inference_mode():
        return torch.sigmoid(model(torch.from_numpy(x))).numpy().astype("float64")


def fit_mlp(name, batch_size, config, train, validation, checkpoint, out):
    xt, yt = train
    xv, yv = validation
    seed = config["seed"]
    torch.manual_seed(seed)
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        TensorDataset(torch.from_numpy(xt), torch.tensor(yt, dtype=torch.float32)),
        batch_size=batch_size, shuffle=True, generator=generator,
    )
    model = network(xt.shape[1], config["mlp_hidden"])
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["mlp_learning_rate"],
                                  weight_decay=config["mlp_weight_decay"], foreach=False, fused=False)
    loss_function = nn.BCEWithLogitsLoss()
    parameters = {
        "architecture": {"inputs": xt.shape[1], "hidden": config["mlp_hidden"], "activation": "ReLU", "outputs": 1},
        "optimizer": "AdamW", "optimizer_options": {k: v for k, v in optimizer.defaults.items()},
        "batch_size": batch_size, "effective_batch_size": batch_size, "shuffle": True, "drop_last": False,
        "seed": seed, "gradient_clip_norm": config["mlp_clip_norm"], "loss": "BCEWithLogitsLoss (mean)",
        "max_epochs": config["mlp_epochs"], "patience": config["mlp_patience"],
    }
    best_loss, best_epoch, updates, history = float("inf"), 0, 0, []
    columns = ["epoch", "update", "batch_rows", "train_bce", "gradient_l2_pre_clip", "learning_rate", "seed"]
    with (out / f"batch-{name}.csv").open("w", newline="", encoding="utf-8") as log:
        batches = csv.DictWriter(log, columns)
        batches.writeheader()
        for epoch in range(1, config["mlp_epochs"] + 1):
            model.train()
            total_loss = 0.0
            norms = []
            for x, y in loader:
                optimizer.zero_grad(set_to_none=True)
                loss = loss_function(model(x), y)
                loss.backward()
                norm = float(nn.utils.clip_grad_norm_(model.parameters(), config["mlp_clip_norm"], error_if_nonfinite=True))
                optimizer.step()
                updates += 1
                value = float(loss.detach())
                total_loss += value * len(x)
                norms.append(norm)
                batches.writerow(dict(zip(columns, (epoch, updates, len(x), value, norm, optimizer.param_groups[0]["lr"], seed))))
            model.eval()
            validation_loss = log_loss(yv, raw_predict("mlp", model, xv))
            if validation_loss < best_loss:
                best_loss, best_epoch = validation_loss, epoch
                torch.save(model.state_dict(), checkpoint)
            history.append({
                "step": epoch, "train_loss": total_loss / len(yt), "validation_loss": validation_loss,
                "best_epoch": best_epoch, "gradient_l2_pre_clip_mean": float(np.mean(norms)),
                "gradient_l2_pre_clip_max": max(norms), "learning_rate": optimizer.param_groups[0]["lr"],
                "effective_batch_size": batch_size, "optimizer_updates": updates,
                "epoch_updates": len(norms), "seed": seed, "best_checkpoint_sha256": sha(checkpoint),
            })
            log.flush()
            if epoch - best_epoch >= config["mlp_patience"]:
                break
    model.load_state_dict(torch.load(checkpoint, weights_only=True, map_location="cpu"))
    return Candidate(name, "mlp", checkpoint, parameters | {"best_epoch": best_epoch}, history, best_loss, model.eval())


def fit_candidates(config, train, validation, out):
    xt, yt = train
    xv, yv = validation
    checkpoints = out / "checkpoints"
    checkpoints.mkdir()
    candidates = []

    def register(name, family, model, parameters, history, checkpoint):
        validation_loss = log_loss(yv, raw_predict(family, model, xv))
        candidates.append(Candidate(name, family, checkpoint, parameters, history, validation_loss, model))
        print(f"{name}: validation log loss {validation_loss:.8f}", flush=True)

    dummy = {"prevalence": float(yt.mean())}
    checkpoint = checkpoints / "dummy.json"
    write_json(checkpoint, dummy)
    register("dummy", "dummy", dummy, {"strategy": "train prevalence"}, [], checkpoint)
    for c in config["logistic_C"]:
        name = f"logistic-C{c}"
        estimator = LogisticRegression(C=c, solver="lbfgs", penalty="l2", tol=1e-8, max_iter=5000)
        estimator.fit(xt, yt)
        iterations = int(estimator.n_iter_[0])
        if iterations >= estimator.max_iter:
            raise RuntimeError(f"{name} failed to converge")
        model = {"coefficients": estimator.coef_[0].tolist(), "intercept": float(estimator.intercept_[0])}
        p = raw_predict("logistic", model, xt)
        gradient = np.r_[xt.T @ (p - yt) / len(yt) + estimator.coef_[0] / (c * len(yt)), np.mean(p - yt)]
        checkpoint = checkpoints / f"{name}.json"
        write_json(checkpoint, model)
        history = [{"step": iterations, "train_loss": log_loss(yt, p),
                    "validation_loss": log_loss(yv, raw_predict("logistic", model, xv)),
                    "gradient_l2_final_regularized": float(np.linalg.norm(gradient))}]
        register(name, "logistic", model, estimator.get_params() | {"iterations": iterations}, history, checkpoint)

    dtrain, dval = xgb.DMatrix(xt, label=yt), xgb.DMatrix(xv, label=yv)
    for depth, rate in product(config["xgb_depth"], config["xgb_learning_rate"]):
        name = f"xgb-d{depth}-lr{rate}"
        params = dict(max_depth=depth, eta=rate, objective="binary:logistic", eval_metric="logloss",
                      tree_method="hist", device="cpu", nthread=1, seed=config["seed"], subsample=1,
                      colsample_bytree=1, reg_lambda=1, reg_alpha=0, min_child_weight=1, gamma=0, max_bin=256)
        history = {}
        booster = xgb.train(params, dtrain, num_boost_round=config["xgb_rounds"],
                            evals=[(dtrain, "train"), (dval, "validation")], evals_result=history,
                            early_stopping_rounds=config["xgb_patience"], verbose_eval=False)
        rounds = booster.best_iteration + 1
        resolved = json.loads(booster.save_config())
        model = booster[:rounds]
        checkpoint = checkpoints / f"{name}.json"
        model.save_model(checkpoint)
        steps = [{"step": i, "train_loss": t, "validation_loss": v}
                 for i, (t, v) in enumerate(zip(history["train"]["logloss"], history["validation"]["logloss"]), 1)]
        register(name, "xgb", model, params | {"rounds": rounds, "max_rounds": config["xgb_rounds"],
                                              "patience": config["xgb_patience"], "resolved_config": resolved}, steps, checkpoint)

    for batch_size in config["mlp_batch_size"]:
        name = f"mlp-b{batch_size}"
        candidates.append(fit_mlp(name, batch_size, config, train, validation, checkpoints / f"{name}.pt", out))
        print(f"{name}: validation log loss {candidates[-1].validation_loss:.8f}", flush=True)
    return candidates


def select(candidates, margin):
    best = candidates[0]
    for family in ("logistic", "xgb", "mlp"):
        challenger = min((row for row in candidates if row.family == family), key=lambda row: row.validation_loss)
        if challenger.validation_loss < best.validation_loss - margin:
            best = challenger
    return best
