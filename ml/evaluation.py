"""One locked-holdout evaluation and prespecified paired comparisons."""

import numpy as np
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score


def log_odds(p):
    return logit(np.clip(p.astype("float64"), 1e-7, 1 - 1e-7))


def logistic_calibration(y, p):
    model = LogisticRegression(penalty=None, solver="lbfgs", tol=1e-9, max_iter=500)
    model.fit(log_odds(p).reshape(-1, 1), y)
    if model.n_iter_[0] >= model.max_iter:
        raise RuntimeError("Calibration fit failed to converge")
    return {"intercept": float(model.intercept_[0]), "slope": float(model.coef_[0, 0])}


def calibrate(p, parameters):
    return expit(parameters["intercept"] + parameters["slope"] * log_odds(p))


def metrics(y, p):
    result = {
        "roc_auc": roc_auc_score(y, p), "average_precision": average_precision_score(y, p),
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(np.mean(np.logaddexp(0, log_odds(p)) - y * log_odds(p))),
        "prevalence": float(np.mean(y)), "expected_events": float(p.sum()), "observed_events": int(y.sum()),
        "observed_minus_expected": float(y.sum() - p.sum()),
        "expected_to_observed": float(p.sum() / y.sum()),
    }
    if np.ptp(p) > 1e-8:
        result.update({f"calibration_{key}": value for key, value in logistic_calibration(y, p).items()})
    return result


def reliability(y, p):
    bins = np.minimum((p * 10).astype(int), 9)
    result = []
    for index in range(10):
        mask = bins == index
        result.append({"lower": index / 10, "upper": (index + 1) / 10, "n": int(mask.sum()),
                       "mean_predicted": float(p[mask].mean()) if mask.any() else None,
                       "observed_rate": float(y[mask].mean()) if mask.any() else None})
    return result


def interval(values):
    return np.quantile(values, [0.025, 0.975]).tolist()


def evaluate(y, predictions, config):
    rng = np.random.default_rng(config["bootstrap_seed"])
    points = {name: metrics(y, p) for name, p in predictions.items()}
    replicates = {name: {key: [] for key in values} for name, values in points.items()}
    # The same row resample is used for every model and every comparison.
    for _ in range(config["bootstrap_replicates"]):
        ids = rng.integers(len(y), size=len(y))
        for name, probabilities in predictions.items():
            for key, value in metrics(y[ids], probabilities[ids]).items():
                replicates[name][key].append(value)
    return {
        "models": {
            name: {"metrics": {k: {"estimate": v, "ci95": interval(replicates[name][k])}
                               for k, v in point.items()}, "reliability": reliability(y, predictions[name])}
            for name, point in points.items()
        },
        "paired_log_loss": [
            {"comparison": [a, b], "estimate": points[a]["log_loss"] - points[b]["log_loss"],
             "ci95": interval(np.subtract(replicates[a]["log_loss"], replicates[b]["log_loss"]))}
            for a, b in config["paired_log_loss_comparisons"]
        ],
        "bootstrap": {"unit": "UCI sample row", "method": "paired percentile", "confidence": 0.95,
                      "replicates": config["bootstrap_replicates"], "seed": config["bootstrap_seed"]},
    }
