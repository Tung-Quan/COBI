"""Calibrated probabilities, fixed-sensitivity review metrics and group bootstrap."""
import numpy as np
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss


def logits(p):
    return logit(np.clip(p.astype("float64"), 1e-6, 1 - 1e-6))


def calibrator(p, labels):
    if len(np.unique(labels)) != 2:
        raise ValueError("Calibration requires both labels")
    fit = LogisticRegression(penalty=None, max_iter=1000, tol=1e-8).fit(logits(p).reshape(-1, 1), labels)
    return {"intercept": float(fit.intercept_[0]), "slope": float(fit.coef_[0, 0])}


def calibrate(p, params):
    return expit(params["intercept"] + params["slope"] * logits(p))


def lock_threshold(calibrated, critical, sensitivity):
    positives = np.sort(calibrated[critical])[::-1]
    if not len(positives):
        raise ValueError("Calibration lacks critical-error labels")
    threshold = float(positives[int(np.ceil(sensitivity * len(positives))) - 1])
    return {"threshold": threshold, "critical_support": len(positives),
            "achieved_critical_recall": float(np.mean(positives >= threshold))}


def scores(p, data, threshold, subset=None):
    mask = data["mask"] if subset is None else data["mask"] & subset
    valid_cases = mask.any(axis=1)
    y, raw = data["y"][mask], p[mask]
    critical = data["critical"][mask]
    flagged = p >= threshold
    recall = float(flagged[mask][critical].mean()) if critical.any() else None
    return {
        "cases": int(valid_cases.sum()), "documents": len(y), "material_errors": int(y.sum()),
        "critical_errors": int(critical.sum()), "critical_recall": recall,
        "critical_fnr": None if recall is None else 1 - recall,
        "average_precision": float(average_precision_score(y, raw)) if len(np.unique(y)) == 2 else None,
        "brier": float(brier_score_loss(y, raw)), "log_loss": float(log_loss(y, raw, labels=[0, 1])),
        "document_flag_rate": float(flagged[mask].mean()),
        "review_workload": float((flagged & mask).any(axis=1)[valid_cases].mean()),
    }


def reliability(p, y):
    bins = np.minimum((p * 10).astype(int), 9)
    return [{"lower": i / 10, "count": int((bins == i).sum()),
             "mean_prediction": float(p[bins == i].mean()), "event_rate": float(y[bins == i].mean())}
            for i in range(10) if (bins == i).any()]


def bootstrap(test, predictions, thresholds, groups, config):
    keys = ("critical_recall", "critical_fnr", "average_precision", "brier", "log_loss", "review_workload")
    unique = sorted(set(groups))
    group_rows = {group: np.flatnonzero(np.array(groups) == group) for group in unique}
    rng = np.random.default_rng(config["bootstrap_seed"])
    distributions = {name: {key: [] for key in keys} for name in predictions}
    for _ in range(config["bootstrap_draws"]):
        rows = np.concatenate([group_rows[group] for group in rng.choice(unique, len(unique), replace=True)])
        data = {key: test[key][rows] for key in ("mask", "y", "critical")}
        for name, p in predictions.items():
            result = scores(p[rows], data, thresholds[name])
            for key in keys:
                distributions[name][key].append(result[key])
    intervals = {name: {key: np.quantile(values, [.025, .975]).tolist() for key, values in draws.items()}
                 for name, draws in distributions.items()}
    differences = {}
    for baseline in ("M0_CS_V2", "M1_LOGISTIC", "M2_XGBOOST"):
        differences[baseline] = {key: np.quantile(np.subtract(distributions["M3_DEEP_SETS"][key],
                                                               distributions[baseline][key]), [.025, .975]).tolist()
                                 for key in keys}
    return intervals, differences
