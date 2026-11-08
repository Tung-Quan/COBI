"""Train, calibrate, evaluate on development-only data, and freeze V4.1 models."""
from __future__ import annotations

import json
import math
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss
from sklearn.preprocessing import StandardScaler
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
    XGBOOST_IMPORT_ERROR = None
except ImportError as exc:  # Keep the non-XGBoost research arms runnable offline.
    XGBClassifier = None
    XGBOOST_AVAILABLE = False
    XGBOOST_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

from evidence_ai.features import build_arrays as build_legacy_arrays
from evidence_ai.model import DeepSets as LegacyDeepSets
from evidence_ai.features import NAMES as LEGACY_FEATURE_NAMES
from evidence_ai.semantic_evidence import FEATURE_NAMES, case_feature_array, semantic_validation
from evidence_ai.v4_1_generator_dev import OUT as DEV, SCENARIOS
from ml.contracts import ROOT, canonical, sha, write_json

OUT = ROOT / "reports/evidence-v4.1"
MODELS_DIR = OUT / "models/frozen-v1"
SEED = 2026110805
TORCH_SEED = 2026110806
CAPACITY = 6
BASELINES = ("M0_CS_V2", "M1_LOGISTIC", "M2_XGBOOST", "M3_DEEP_SETS")
SEMANTIC_MODELS = ("SEMANTIC_LOGISTIC", "SEMANTIC_XGBOOST", "SEMANTIC_DEEP_SETS",
                   "SEMANTIC_RULE", "SEMANTIC_HYBRID",
                   "ABLATION_NO_TEMPORAL", "ABLATION_NO_COMPARABILITY", "ABLATION_NO_SOURCE_PROVENANCE")


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read(path):
    return _json(path)


def _sigmoid(x):
    x = np.clip(np.asarray(x, dtype=float), -35, 35)
    return 1.0 / (1.0 + np.exp(-x))


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


class DeepSetsContext(torch.nn.Module):
    """Permutation-invariant document encoder with pooled semantic case context."""
    def __init__(self, input_dim: int, hidden: int = 48):
        super().__init__()
        self.phi = torch.nn.Sequential(torch.nn.Linear(input_dim, hidden), torch.nn.ReLU(),
                                       torch.nn.Linear(hidden, hidden), torch.nn.ReLU())
        self.rho = torch.nn.Sequential(torch.nn.Linear(hidden * 2, hidden), torch.nn.ReLU(),
                                       torch.nn.Dropout(.10), torch.nn.Linear(hidden, 1))

    def forward(self, x, mask):
        h = self.phi(x)
        w = mask.to(h.dtype).unsqueeze(-1)
        pooled = (h * w).sum(dim=1, keepdim=True) / w.sum(dim=1, keepdim=True).clamp_min(1)
        pooled = pooled.expand_as(h)
        return self.rho(torch.cat([h, pooled], dim=-1)).squeeze(-1)


def _load_development():
    manifest = _json(DEV / "dataset_manifest.json")
    for filename, digest in manifest["file_sha256"].items():
        if sha(DEV / filename) != digest:
            raise ValueError(f"Development file checksum mismatch: {filename}")
    cases = _json(DEV / "observed.json")
    labels = _json(DEV / "gold_labels.json")
    label_by_case = {row["case_id"]: row for row in labels}
    x, mask, explanations = case_feature_array(cases, CAPACITY)
    y = np.zeros(mask.shape, dtype=np.int64)
    critical = np.zeros(mask.shape, dtype=np.int64)
    for i, case in enumerate(cases):
        for j, target in enumerate(label_by_case[case["case_id"]]["records"]):
            if target["record_id"] != case["records"][j]["record_id"]:
                raise ValueError("Development label/record alignment error")
            y[i, j] = int(target["material_defect"])
            critical[i, j] = int(target["critical_defect"])
    split = {name: set(_json(DEV / f"split_{name}.json")["case_ids"])
             for name in ("train", "validation", "calibration", "locked_test")}
    id_to_index = {case["case_id"]: i for i, case in enumerate(cases)}
    indexes = {name: np.asarray([id_to_index[key] for key in ids], dtype=int) for name, ids in split.items()}
    groups = {name: {cases[i]["customer_group"] for i in idx} for name, idx in indexes.items()}
    for i, left in enumerate(groups):
        for right in list(groups)[i+1:]:
            if groups[left] & groups[right]:
                raise ValueError(f"Customer group split leakage: {left}/{right}")
    return cases, labels, x, mask, y, critical, indexes, explanations


def _flat(x, mask, y, critical, case_indexes, feature_indexes=None):
    X = x[case_indexes]
    M = mask[case_indexes]
    Y = y[case_indexes]
    C = critical[case_indexes]
    if feature_indexes is not None:
        X = X[..., feature_indexes]
    case_ids = np.repeat(np.arange(len(case_indexes)), M.sum(axis=1))
    return X[M], Y[M].astype(int), C[M].astype(int), case_ids


def _prepare_scaled(x, mask, case_indexes, feature_indexes):
    selected = x[case_indexes][..., feature_indexes].astype(np.float64)
    valid = selected[mask[case_indexes]]
    scaler = StandardScaler().fit(valid)
    scaled = ((selected - scaler.mean_) / scaler.scale_).astype(np.float32)
    scaled[~mask[case_indexes]] = 0.0
    return scaled, scaler


def _transform_scaled(x, mask, case_indexes, feature_indexes, scaler):
    selected = x[case_indexes][..., feature_indexes].astype(np.float64)
    scaled = ((selected - scaler.mean_) / scaler.scale_).astype(np.float32)
    scaled[~mask[case_indexes]] = 0.0
    return scaled


def _fit_deepsets(x, mask, y, case_indexes, feature_indexes, hidden, max_epochs=36, patience=6,
                  seed=TORCH_SEED, validation_indexes=None, refit_epochs=None, prefix=""):
    train_set = set(map(int, case_indexes))
    fit_indexes = np.asarray(sorted(train_set), dtype=int)
    fit_x, scaler = _prepare_scaled(x, mask, fit_indexes, feature_indexes)
    fit_y = y[fit_indexes].astype(np.float32)
    fit_m = mask[fit_indexes]
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.set_num_threads(1)
    model = DeepSetsContext(len(feature_indexes), hidden)
    pos = max(1, int(fit_y[fit_m].sum()))
    neg = max(1, int(fit_m.sum() - pos))
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(neg / pos, dtype=torch.float32))
    optimizer = torch.optim.Adam(model.parameters(), lr=.001, weight_decay=1e-4)
    train_x_t = torch.tensor(fit_x)
    train_m_t = torch.tensor(fit_m)
    train_y_t = torch.tensor(fit_y)
    best_state, best_ap, best_epoch, stale = None, -1.0, 1, 0
    history = []
    if validation_indexes is not None:
        val_x = _transform_scaled(x, mask, validation_indexes, feature_indexes, scaler)
        val_m, val_y = mask[validation_indexes], y[validation_indexes]
        val_x_t, val_m_t = torch.tensor(val_x), torch.tensor(val_m)
    target_epochs = int(refit_epochs) if refit_epochs is not None else max_epochs
    for epoch in range(1, target_epochs + 1):
        model.train()
        order = np.random.permutation(len(fit_indexes))
        losses = []
        for start in range(0, len(order), 64):
            batch = order[start:start+64]
            optimizer.zero_grad()
            logits = model(train_x_t[batch], train_m_t[batch])
            loss = loss_fn(logits[train_m_t[batch]], train_y_t[batch][train_m_t[batch]])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            losses.append(float(loss.detach()))
        model.eval()
        if validation_indexes is not None and refit_epochs is None:
            with torch.no_grad():
                val_logits = model(val_x_t, val_m_t).cpu().numpy()
            val_scores = _sigmoid(val_logits[val_m])
            val_labels = val_y[val_m]
            val_ap = float(average_precision_score(val_labels, val_scores))
            history.append({"epoch": epoch, "train_loss": float(np.mean(losses)), "validation_ap": val_ap})
            if val_ap > best_ap + 1e-7:
                best_ap, best_epoch, stale = val_ap, epoch, 0
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            else:
                stale += 1
            if stale >= patience:
                break
        else:
            history.append({"epoch": epoch, "train_loss": float(np.mean(losses)), "validation_ap": None})
    if validation_indexes is not None and refit_epochs is None:
        model.load_state_dict(best_state)
    return model, scaler, {"best_epoch": best_epoch, "best_validation_ap": best_ap if validation_indexes is not None and refit_epochs is None else None,
                           "history": history, "training_loss_final": history[-1]["train_loss"]}


def _deep_raw(model, scaler, x, mask, indexes, feature_indexes):
    selected = x[indexes][..., feature_indexes].astype(np.float64)
    sx = ((selected - scaler.mean_) / scaler.scale_).astype(np.float32)
    m = mask[indexes]
    sx[~m] = 0.0
    model.eval()
    with torch.no_grad():
        return model(torch.tensor(sx), torch.tensor(m)).cpu().numpy()


def _metric(probabilities, y, critical, case_ids, threshold):
    p = np.asarray(probabilities, dtype=float)
    y = np.asarray(y, dtype=int)
    critical = np.asarray(critical, dtype=int)
    flagged = p >= threshold
    case_ids = np.asarray(case_ids, dtype=int)
    n_cases = len(set(case_ids.tolist()))
    flagged_cases = len(set(case_ids[flagged].tolist()))
    crit_n = int(critical.sum())
    crit_tp = int((flagged & (critical == 1)).sum())
    legit = y == 0
    legit_n = int(legit.sum())
    legit_fp = int((flagged & legit).sum())
    return {
        "documents": len(y), "material_errors": int(y.sum()), "critical_errors": crit_n,
        "critical_false_negatives": crit_n - crit_tp,
        "critical_recall": float(crit_tp / crit_n) if crit_n else None,
        "critical_fnr": float((crit_n - crit_tp) / crit_n) if crit_n else None,
        "material_average_precision": float(average_precision_score(y, p)) if len(np.unique(y)) > 1 else None,
        "critical_average_precision": float(average_precision_score(critical, p)) if len(np.unique(critical)) > 1 else None,
        "brier": float(brier_score_loss(y, p)), "log_loss": float(log_loss(y, np.clip(p, 1e-6, 1-1e-6), labels=[0, 1])),
        "legitimate_false_positives": legit_fp, "legitimate_support": legit_n,
        "legitimate_fpr": float(legit_fp / legit_n) if legit_n else None,
        "review_workload": float(flagged_cases / max(1, n_cases)), "flagged_cases": flagged_cases,
        "frozen_threshold": float(threshold),
    }


def _fit_platt(raw, y):
    lr = LogisticRegression(C=1e6, solver="lbfgs", max_iter=2000, random_state=SEED)
    logits = _logit(raw).reshape(-1, 1)
    lr.fit(logits, y)
    return {"intercept": float(lr.intercept_[0]), "slope": float(lr.coef_[0, 0]),
            "input_transform": "logit_clipped_probability"}


def _apply_platt(raw, calibration):
    return _sigmoid(calibration["intercept"] + calibration["slope"] * _logit(raw))


def _threshold_policy(probabilities, y, critical, case_ids):
    p = np.asarray(probabilities, dtype=float)
    candidates = np.unique(np.r_[0.0, p, 1.0 + 1e-9])
    rows = []
    for threshold in candidates:
        result = _metric(p, y, critical, case_ids, float(threshold))
        rows.append(result)
    feasible = [row for row in rows if row["critical_recall"] is not None and row["critical_recall"] >= .90
                and row["legitimate_fpr"] is not None and row["legitimate_fpr"] <= .20]
    if feasible:
        selected = min(feasible, key=lambda row: (row["review_workload"], -row["frozen_threshold"]))
        status = "CALIBRATION_TARGET_MET"
    else:
        selected = min(rows, key=lambda row: (-(row["critical_recall"] or 0), row["review_workload"], -row["frozen_threshold"]))
        status = "CALIBRATION_TARGET_UNMET"
    return selected["frozen_threshold"], status, {"candidate_count": len(rows), "selected_calibration_metrics": selected,
                                                  "constraints": {"critical_recall_min": .90, "legitimate_fpr_max": .20}}


def _feature_groups():
    temporal_keys = ("age_days", "asserted_current", "effective_period", "period_overlaps", "stale_as_current", "historical_applicable", "days_from", "effective_period_days")
    comparability_keys = ("n_comparable", "n_noncomparable", "n_unknown", "max_comparable", "has_comparable_conflict")
    source_keys = ("source_", "verified", "unverified", "correction_", "has_correction_lineage", "uncertainty")
    return {
        "temporal": [i for i, n in enumerate(FEATURE_NAMES) if any(k in n for k in temporal_keys)],
        "comparability": [i for i, n in enumerate(FEATURE_NAMES) if any(k in n for k in comparability_keys)],
        "source_provenance": [i for i, n in enumerate(FEATURE_NAMES) if any(k in n for k in source_keys)],
    }


def _fit_flat_model(kind, x, mask, y, critical, indexes, feature_indexes, params):
    Xcases, scaler = _prepare_scaled(x, mask, indexes, feature_indexes)
    M = mask[indexes]
    X = Xcases[M].astype(np.float32)
    Y = y[indexes][M].astype(int)
    if kind == "logistic":
        model = LogisticRegression(C=float(params["C"]), class_weight="balanced", max_iter=2000,
                                   solver="lbfgs", random_state=SEED)
    else:
        positives = max(1, int(Y.sum()))
        model = XGBClassifier(
            n_estimators=int(params["n_estimators"]), max_depth=int(params["max_depth"]),
            learning_rate=float(params["learning_rate"]), min_child_weight=2,
            subsample=.90, colsample_bytree=.90, reg_lambda=2.0,
            scale_pos_weight=float((len(Y)-positives)/positives), objective="binary:logistic",
            eval_metric="logloss", n_jobs=1, random_state=SEED, verbosity=0,
        )
    model.fit(X, Y)
    return model, scaler


def _predict_flat(model, scaler, x, mask, indexes, feature_indexes, kind):
    Xcases = _transform_scaled(x, mask, indexes, feature_indexes, scaler)
    M = mask[indexes]
    flat = Xcases[M]
    if kind == "logistic" or kind == "xgboost":
        return model.predict_proba(flat)[:, 1]
    raise ValueError(kind)


def _fit_platt_and_threshold(raw_cal, y_cal, crit_cal, case_ids_cal):
    calibrator = _fit_platt(raw_cal, y_cal)
    calibrated = _apply_platt(raw_cal, calibrator)
    threshold, status, trace = _threshold_policy(calibrated, y_cal, crit_cal, case_ids_cal)
    return calibrator, threshold, status, trace


def _legacy_cases(cases, labels):
    label_by_case = {row["case_id"]: row for row in labels}
    legacy_cases, legacy_labels = [], []
    for case in cases:
        documents, targets = [], []
        for record in case["records"]:
            values = {field: None for field in ("income", "debt", "purchase")}
            values[record["field_type"]] = record["normalized_value"]
            source = record["source_type"]
            doc = {"document_key": record["record_id"], "source": source, "template": "semantic-evidence-v1",
                   "values": values, "age_days": record["age_days"],
                   "verified": record["verification_status"] == "VERIFIED", "ocr_quality": record["ocr_quality"],
                   "text": record["text"].lower(), "observed_at": record["observed_at"]}
            documents.append(doc)
            gold = next(row for row in label_by_case[case["case_id"]]["records"] if row["record_id"] == record["record_id"])
            field_errors = {field: (int(gold["material_defect"]) if field == record["field_type"] else 0)
                            for field in ("income", "debt", "purchase")}
            targets.append({"document_key": record["record_id"], "observed_payload_sha256": __import__("hashlib").sha256(canonical(doc)).hexdigest(),
                            "material_evidence_error": gold["material_defect"], "critical_evidence_error": gold["critical_defect"],
                            "field_extraction_error": field_errors})
        legacy_cases.append({"case_key": case["case_id"], "customer_group": case["customer_group"],
                             "observed_at": case["request"]["requested_at"], "income_history_months": 12, "documents": documents})
        legacy_labels.append({"case_key": case["case_id"], "documents": targets})
    return legacy_cases, legacy_labels


def _semantic_rule(cases):
    scores, explanations = [], []
    for case in cases:
        result = semantic_validation(case)
        row = []
        for record in case["records"]:
            item = result["documents"][record["record_id"]]
            row.append(float(item["score"]))
            explanations.append({"case_id": case["case_id"], "record_id": record["record_id"],
                                 "score": item["score"], "alerts": item["alerts"],
                                 "time_validity": item["time_validity"],
                                 "comparisons": [pair for pair in result["comparisons"]
                                                 if record["record_id"] in {pair["left_record_id"], pair["right_record_id"]}]})
        scores.append(row)
    return scores, explanations


def _flatten_padded(rows, indexes, mask):
    docs, case_ids = [], []
    for local, global_idx in enumerate(indexes):
        vals = rows[local] if len(rows) == len(indexes) else rows[global_idx]
        mask_index = global_idx if len(mask) > int(np.max(indexes, initial=-1)) else local
        n = int(mask[mask_index].sum())
        docs.extend(vals[:n])
        case_ids.extend([local] * n)
    return np.asarray(docs, dtype=float), np.asarray(case_ids, dtype=int)


def _baseline_development_test(cases, labels, indexes, y, critical, mask):
    test_cases = [cases[i] for i in indexes["locked_test"]]
    test_labels = [labels[i] for i in indexes["locked_test"]]
    projected_cases, projected_labels = _legacy_cases(test_cases, test_labels)
    release_dir = ROOT / "reports/evidence-v3/synthetic"
    model_dir = release_dir / "model"
    old_manifest = read(model_dir / "manifest.json")
    lock = read(release_dir / "selection_lock.json")
    preprocessing = read(model_dir / "preprocessing.json")
    if old_manifest["feature_names"] != LEGACY_FEATURE_NAMES:
        raise ValueError("Frozen V3 feature contract changed")
    data = build_legacy_arrays(projected_cases, projected_labels)
    legacy_x = ((data["x"] - np.asarray(preprocessing["mean"])) / np.asarray(preprocessing["scale"])).astype(np.float32)
    legacy_x[~data["mask"]] = 0
    flat_x = legacy_x[data["mask"]]
    base = read(release_dir / "logistic.json")
    base_prob = _sigmoid(flat_x @ np.asarray(base["coefficients"]) + float(base["intercept"]))
    probabilities = {
        "M0_CS_V2": np.broadcast_to(data["cs_risk"][:, None], data["mask"].shape).copy(),
        "M1_LOGISTIC": np.zeros(data["mask"].shape, dtype=float),
    }
    probabilities["M1_LOGISTIC"][data["mask"]] = base_prob
    networks = []
    for seed in old_manifest["seeds"]:
        network = LegacyDeepSets(len(LEGACY_FEATURE_NAMES), old_manifest["hidden"], len(old_manifest["field_names"]))
        network.load_state_dict(torch.load(model_dir / f"{old_manifest['selected_variant']}-s{seed}.pt",
                                           map_location="cpu", weights_only=True))
        networks.append(network.eval())
    with torch.no_grad():
        legacy_tensor = torch.from_numpy(legacy_x)
        mask_tensor = torch.from_numpy(data["mask"])
        deep_raw = np.mean([network(legacy_tensor, mask_tensor)[0].cpu().numpy() for network in networks], axis=0)
    probabilities["M3_DEEP_SETS"] = _sigmoid(deep_raw)
    for name, raw in list(probabilities.items()):
        probabilities[name] = _apply_platt(raw[data["mask"]] if raw.shape == data["mask"].shape else raw,
                                           lock["all_model_calibrators"][name])
    # Restore padded shape only for common metric aggregation below.
    results, predictions = {}, {}
    yy = data["y"][data["mask"]]
    cc = data["critical"][data["mask"]]
    case_ids = np.repeat(np.arange(len(projected_cases)), data["mask"].sum(axis=1))
    for model_name in ("M0_CS_V2", "M1_LOGISTIC", "M3_DEEP_SETS"):
        results[model_name] = _metric(probabilities[model_name], yy, cc, case_ids,
                                      float(lock["all_thresholds"][model_name]))
        predictions[model_name] = _prediction_rows(
            test_cases, test_labels, probabilities[model_name], y=yy, critical=cc,
            threshold=float(lock["all_thresholds"][model_name]), model_name=model_name)
    results["M2_XGBOOST"] = {"status": "BLOCKED_DEPENDENCY", "dependency": "xgboost==3.0.5",
                             "reason": XGBOOST_IMPORT_ERROR or "XGBoost replay unavailable"}
    return results, predictions


def _prediction_rows(cases, labels, scores, y=None, critical=None, threshold=None, model_name=""):
    label_by_case = {row["case_id"]: row for row in labels}
    out, cursor = [], 0
    for case in cases:
        targets = label_by_case[case["case_id"]]["records"]
        for record, target in zip(case["records"], targets, strict=True):
            score = float(scores[cursor])
            out.append({"model": model_name, "case_id": case["case_id"],
                        "customer_group": case["customer_group"], "scenario": case["scenario"],
                        "record_id": record["record_id"], "score": score,
                        "flagged": bool(score >= threshold) if threshold is not None else None,
                        "material_defect": int(target["material_defect"]),
                        "critical_defect": int(target["critical_defect"])})
            cursor += 1
    if cursor != len(scores):
        raise ValueError(f"Prediction alignment mismatch for {model_name}: {cursor} != {len(scores)}")
    return out


def _group_ablation_indices():
    groups = _feature_groups()
    return {
        "ABLATION_NO_TEMPORAL": [i for i in range(len(FEATURE_NAMES)) if i not in set(groups["temporal"])],
        "ABLATION_NO_COMPARABILITY": [i for i in range(len(FEATURE_NAMES)) if i not in set(groups["comparability"])],
        "ABLATION_NO_SOURCE_PROVENANCE": [i for i in range(len(FEATURE_NAMES)) if i not in set(groups["source_provenance"])],
    }


def train_and_freeze():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    cases, labels, x, mask, y, critical, indexes, explanations = _load_development()
    training_indexes = np.concatenate([indexes["train"], indexes["validation"]])
    validation_indexes = indexes["validation"]
    calibration_indexes = indexes["calibration"]
    test_indexes = indexes["locked_test"]

    # The locked D test is held until after all hyperparameters and thresholds are fixed.
    selected_params, tuning_log = {}, {}
    full_features = list(range(len(FEATURE_NAMES)))
    candidates = {
        "SEMANTIC_LOGISTIC": ("logistic", [{"C": value} for value in (.05, .2, 1., 5., 20.)]),
    }
    if XGBOOST_AVAILABLE:
        candidates["SEMANTIC_XGBOOST"] = ("xgboost", [{"max_depth": depth, "n_estimators": trees, "learning_rate": .05}
                                                         for depth in (2, 3, 4) for trees in (120, 240)])
    fitted = {}
    for name, (kind, grid) in candidates.items():
        records = []
        best = None
        for params in grid:
            model, scaler = _fit_flat_model(kind, x, mask, y, critical, indexes["train"], full_features, params)
            raw = _predict_flat(model, scaler, x, mask, validation_indexes, full_features, kind)
            _, yy, cc, local_case = _flat(x, mask, y, critical, validation_indexes, full_features)
            row = {"params": params, "validation_ap": float(average_precision_score(yy, raw)),
                   "validation_critical_recall_at_0_5": float(((raw >= .5) & (cc == 1)).sum()/max(1,int(cc.sum())))}
            records.append(row)
            rank = (row["validation_ap"], row["validation_critical_recall_at_0_5"])
            if best is None or rank > best[0]:
                best = (rank, params)
        selected_params[name] = best[1]
        tuning_log[name] = {"candidates": records, "selected_params": best[1], "selection_metric": "validation AP then critical recall"}
        final_model, scaler = _fit_flat_model(kind, x, mask, y, critical, training_indexes, full_features, best[1])
        fitted[name] = {"kind": kind, "model": final_model, "scaler": scaler, "feature_indices": full_features}

    # Deep Sets model selection uses validation AP for hidden size and early-stopped epoch.
    ds_candidates = []
    ds_best = None
    for hidden in (32, 48, 64):
        model, scaler, training = _fit_deepsets(x, mask, y, indexes["train"], full_features, hidden,
                                                max_epochs=36, patience=6, seed=TORCH_SEED,
                                                validation_indexes=validation_indexes)
        raw_logits = _deep_raw(model, scaler, x, mask, validation_indexes, full_features)
        raw_flat, val_case_ids = _flatten_padded(raw_logits, validation_indexes, mask)
        yy, cc = y[validation_indexes][mask[validation_indexes]], critical[validation_indexes][mask[validation_indexes]]
        ap = float(average_precision_score(yy, _sigmoid(raw_flat)))
        candidate = {"hidden": hidden, "best_epoch": training["best_epoch"], "validation_ap": ap,
                     "validation_training_log": training["history"]}
        ds_candidates.append(candidate)
        if ds_best is None or (ap, -hidden) > (ds_best["validation_ap"], -ds_best["hidden"]):
            ds_best = candidate
    ds_final, ds_scaler, ds_refit = _fit_deepsets(x, mask, y, training_indexes, full_features,
                                                 ds_best["hidden"], seed=TORCH_SEED,
                                                 refit_epochs=ds_best["best_epoch"])
    fitted["SEMANTIC_DEEP_SETS"] = {"kind": "deepsets", "model": ds_final, "scaler": ds_scaler,
                                    "feature_indices": full_features}
    selected_params["SEMANTIC_DEEP_SETS"] = {"hidden": ds_best["hidden"], "epochs": ds_best["best_epoch"], "seed": TORCH_SEED}
    tuning_log["SEMANTIC_DEEP_SETS"] = {"candidates": ds_candidates, "selected_params": selected_params["SEMANTIC_DEEP_SETS"],
                                         "refit_train_plus_validation": ds_refit["history"]}

    # Pre-registered feature ablations: independently tune/fit each LR variant on D only.
    ablation_groups = _group_ablation_indices()
    ablation_params = {}
    for name, features in _group_ablation_indices().items():
        records, best = [], None
        for C in (.05, .2, 1., 5., 20.):
            model, scaler = _fit_flat_model("logistic", x, mask, y, critical, indexes["train"], features, {"C": C})
            raw = _predict_flat(model, scaler, x, mask, validation_indexes, features, "logistic")
            _, yy, cc, _ = _flat(x, mask, y, critical, validation_indexes, features)
            ap = float(average_precision_score(yy, raw))
            recall = float(((raw >= .5) & (cc == 1)).sum()/max(1,int(cc.sum())))
            records.append({"C": C, "validation_ap": ap, "validation_critical_recall_at_0_5": recall})
            if best is None or (ap, recall) > best[0]:
                best = ((ap, recall), C)
        ablation_params[name] = {"C": best[1], "features_retained": [FEATURE_NAMES[i] for i in features]}
        model, scaler = _fit_flat_model("logistic", x, mask, y, critical, training_indexes, features, {"C": best[1]})
        fitted[name] = {"kind": "logistic", "model": model, "scaler": scaler, "feature_indices": features}
        tuning_log[name] = {"candidates": records, "selected_params": ablation_params[name],
                            "selection_metric": "validation AP then critical recall"}

    # Assemble semantic rule and hybrid selection using validation only.
    rule_validation, _ = _semantic_rule([cases[i] for i in validation_indexes])
    rule_flat, rule_case_ids = _flatten_padded(rule_validation, np.arange(len(validation_indexes)), mask[validation_indexes])
    val_y = y[validation_indexes][mask[validation_indexes]]
    val_crit = critical[validation_indexes][mask[validation_indexes]]
    raw_candidate_ap = {}
    for name, item in fitted.items():
        if name.startswith("ABLATION"):
            continue
        if item["kind"] in {"logistic", "xgboost"}:
            raw = _predict_flat(item["model"], item["scaler"], x, mask, validation_indexes,
                                item["feature_indices"], item["kind"])
        else:
            raw = _sigmoid(_flatten_padded(_deep_raw(item["model"], item["scaler"], x, mask,
                                                      validation_indexes, item["feature_indices"]),
                                              validation_indexes, mask)[0])
        raw_candidate_ap[name] = float(average_precision_score(val_y, raw))
    hybrid_base = max(raw_candidate_ap, key=raw_candidate_ap.get)
    selected_params["SEMANTIC_HYBRID_BASE"] = hybrid_base
    tuning_log["SEMANTIC_HYBRID"] = {"base_model_selected_on_validation": hybrid_base,
                                     "validation_ap": raw_candidate_ap[hybrid_base],
                                     "rule": "max(rule score, base probability) then calibrate on calibration partition"}

    # Calibration and thresholds are fit only on the separate calibration partition.
    frozen = {}
    calibration_log = {}
    for name, item in fitted.items():
        if item["kind"] in {"logistic", "xgboost"}:
            raw_cal = _predict_flat(item["model"], item["scaler"], x, mask, calibration_indexes,
                                    item["feature_indices"], item["kind"])
        else:
            raw_logits = _deep_raw(item["model"], item["scaler"], x, mask, calibration_indexes,
                                   item["feature_indices"])
            raw_cal, _ = _flatten_padded(raw_logits, calibration_indexes, mask)
            raw_cal = _sigmoid(raw_cal)
        _, yy, cc, case_ids = _flat(x, mask, y, critical, calibration_indexes, item["feature_indices"])
        calibrator, threshold, status, trace = _fit_platt_and_threshold(raw_cal, yy, cc, case_ids)
        frozen[name] = {"kind": item["kind"], "calibrator": calibrator, "threshold": threshold,
                        "threshold_status": status, "threshold_trace": trace,
                        "feature_indices": item["feature_indices"],
                        "feature_names": [FEATURE_NAMES[i] for i in item["feature_indices"]]}
        calibration_log[name] = {"calibrator": calibrator, "threshold": threshold,
                                 "threshold_status": status, "threshold_trace": trace}

    # The rules-only baseline is fixed; its score is a deterministic review signal, not a probability.
    frozen["SEMANTIC_RULE"] = {"kind": "semantic_rule", "threshold": .5,
                               "threshold_status": "FIXED_DETERMINISTIC_RULE_THRESHOLD",
                               "feature_names": list(FEATURE_NAMES)}
    if not XGBOOST_AVAILABLE:
        frozen["SEMANTIC_XGBOOST"] = {"kind": "unavailable", "status": "BLOCKED_DEPENDENCY",
                                     "dependency": "xgboost==3.0.5", "reason": XGBOOST_IMPORT_ERROR,
                                     "feature_names": list(FEATURE_NAMES)}

    base_item = fitted[hybrid_base]
    raw_cal_base = None
    if base_item["kind"] in {"logistic", "xgboost"}:
        raw_cal_base = _predict_flat(base_item["model"], base_item["scaler"], x, mask, calibration_indexes,
                                     base_item["feature_indices"], base_item["kind"])
    else:
        raw_logits = _deep_raw(base_item["model"], base_item["scaler"], x, mask, calibration_indexes,
                               base_item["feature_indices"])
        raw_cal_base, _ = _flatten_padded(raw_logits, calibration_indexes, mask)
        raw_cal_base = _sigmoid(raw_cal_base)
    rule_cal, _ = _semantic_rule([cases[i] for i in calibration_indexes])
    rule_cal_flat, rule_cal_cases = _flatten_padded(rule_cal, np.arange(len(calibration_indexes)), mask[calibration_indexes])
    hybrid_raw_cal = np.maximum(raw_cal_base, rule_cal_flat)
    _, y_cal, c_cal, cal_case_ids = _flat(x, mask, y, critical, calibration_indexes, full_features)
    hybrid_calibrator, hybrid_threshold, hybrid_status, hybrid_trace = _fit_platt_and_threshold(
        hybrid_raw_cal, y_cal, c_cal, cal_case_ids)
    frozen["SEMANTIC_HYBRID"] = {"kind": "hybrid", "base_model": hybrid_base,
                                 "calibrator": hybrid_calibrator, "threshold": hybrid_threshold,
                                 "threshold_status": hybrid_status, "threshold_trace": hybrid_trace,
                                 "rule_threshold": .5, "feature_names": list(FEATURE_NAMES)}
    calibration_log["SEMANTIC_HYBRID"] = {"base_model": hybrid_base, "calibrator": hybrid_calibrator,
                                          "threshold": hybrid_threshold, "threshold_status": hybrid_status,
                                          "threshold_trace": hybrid_trace}

    # Save model and preprocessing files; no C data has been generated or read.
    saved = {}
    for name, item in fitted.items():
        if item["kind"] == "deepsets":
            path = MODELS_DIR / "semantic_deepsets.pt"
            torch.save(item["model"].state_dict(), path)
            saved[name] = {"weights": path.relative_to(ROOT).as_posix(),
                           "preprocess": {"mean": item["scaler"].mean_.tolist(), "scale": item["scaler"].scale_.tolist(),
                                          "feature_names": [FEATURE_NAMES[i] for i in item["feature_indices"]],
                                          "hidden": selected_params[name]["hidden"]}}
        else:
            path = MODELS_DIR / f"{name.casefold()}.joblib"
            joblib.dump(item["model"], path)
            saved[name] = {"weights": path.relative_to(ROOT).as_posix(),
                           "preprocess": {"mean": item["scaler"].mean_.tolist(), "scale": item["scaler"].scale_.tolist(),
                                          "feature_names": [FEATURE_NAMES[i] for i in item["feature_indices"]]}}
    write_json(MODELS_DIR / "training_configuration.json", {"seed": SEED, "torch_seed": TORCH_SEED,
               "development_manifest_sha256": sha(DEV / "dataset_manifest.json"),
               "feature_names": FEATURE_NAMES, "selected_parameters": selected_params,
               "ablation_groups": ablation_groups, "selected_hybrid_base": hybrid_base,
               "xgboost_available": XGBOOST_AVAILABLE, "xgboost_import_error": XGBOOST_IMPORT_ERROR})
    write_json(MODELS_DIR / "training_log.json", {"protocol_id": "cobi-evidence-v4.1-c1.0",
               "training_cases": len(training_indexes), "training_groups": len({cases[i]["customer_group"] for i in training_indexes}),
               "hyperparameter_selection_partition": "validation", "calibration_partition": "calibration",
               "training_configuration": selected_params, "tuning_log": tuning_log,
               "calibration_threshold_log": calibration_log,
               "training_history": {name: row.get("refit_train_plus_validation", []) for name, row in tuning_log.items()},
               "training_data_hashes": read(DEV / "dataset_manifest.json")["file_sha256"],
               "training_performed": True, "no_generator_c_loaded": True,
               "model_availability": {"SEMANTIC_XGBOOST": "AVAILABLE" if XGBOOST_AVAILABLE else "BLOCKED_DEPENDENCY"}})

    # Development locked test is opened only after model/threshold selection is complete.
    test_results = {}
    for name, item in fitted.items():
        if item["kind"] in {"logistic", "xgboost"}:
            raw_test = _predict_flat(item["model"], item["scaler"], x, mask, test_indexes,
                                     item["feature_indices"], item["kind"])
        else:
            raw_logits = _deep_raw(item["model"], item["scaler"], x, mask, test_indexes,
                                   item["feature_indices"])
            raw_test, _ = _flatten_padded(raw_logits, test_indexes, mask)
            raw_test = _sigmoid(raw_test)
        _, yy, cc, case_ids = _flat(x, mask, y, critical, test_indexes, item["feature_indices"])
        calibrated = _apply_platt(raw_test, frozen[name]["calibrator"])
        test_results[name] = _metric(calibrated, yy, cc, case_ids, frozen[name]["threshold"])
    rule_test, rule_explanations = _semantic_rule([cases[i] for i in test_indexes])
    rule_flat, _ = _flatten_padded(rule_test, np.arange(len(test_indexes)), mask[test_indexes])
    _, y_test, c_test, test_case_ids = _flat(x, mask, y, critical, test_indexes, full_features)
    test_results["SEMANTIC_RULE"] = _metric(rule_flat, y_test, c_test, test_case_ids, .5)
    test_results["SEMANTIC_RULE"]["brier"] = None
    test_results["SEMANTIC_RULE"]["log_loss"] = None
    test_results["SEMANTIC_RULE"]["probability_status"] = "UNSCORED_DETERMINISTIC_RULE_SIGNAL"
    hybrid_name = frozen["SEMANTIC_HYBRID"]["base_model"]
    base_frozen = frozen[hybrid_name]
    if fitted[hybrid_name]["kind"] in {"logistic", "xgboost"}:
        base_raw_test = _predict_flat(fitted[hybrid_name]["model"], fitted[hybrid_name]["scaler"], x, mask,
                                      test_indexes, fitted[hybrid_name]["feature_indices"], fitted[hybrid_name]["kind"])
    else:
        base_logits = _deep_raw(fitted[hybrid_name]["model"], fitted[hybrid_name]["scaler"], x, mask,
                                test_indexes, fitted[hybrid_name]["feature_indices"])
        base_raw_test, _ = _flatten_padded(base_logits, test_indexes, mask)
        base_raw_test = _sigmoid(base_raw_test)
    rule_test_flat, _ = _flatten_padded(rule_test, np.arange(len(test_indexes)), mask[test_indexes])
    hybrid_cal = _apply_platt(np.maximum(base_raw_test, rule_test_flat), frozen["SEMANTIC_HYBRID"]["calibrator"])
    test_results["SEMANTIC_HYBRID"] = _metric(hybrid_cal, y_test, c_test, test_case_ids, frozen["SEMANTIC_HYBRID"]["threshold"])
    if not XGBOOST_AVAILABLE:
        test_results["SEMANTIC_XGBOOST"] = {"status": "BLOCKED_DEPENDENCY", "dependency": "xgboost==3.0.5",
                                             "reason": XGBOOST_IMPORT_ERROR}

    prediction_rows = []
    for name, result in test_results.items():
        if result.get("status") == "BLOCKED_DEPENDENCY":
            continue
        # Existing result vectors retain the locked test's case/document order.
        if name == "SEMANTIC_RULE":
            score_vector, threshold = rule_flat, .5
        elif name == "SEMANTIC_HYBRID":
            score_vector, threshold = hybrid_cal, frozen[name]["threshold"]
        else:
            item = fitted[name]
            if item["kind"] in {"logistic", "xgboost"}:
                raw_vec = _predict_flat(item["model"], item["scaler"], x, mask, test_indexes,
                                        item["feature_indices"], item["kind"])
            else:
                raw_logits = _deep_raw(item["model"], item["scaler"], x, mask, test_indexes,
                                       item["feature_indices"])
                raw_vec, _ = _flatten_padded(raw_logits, test_indexes, mask)
                raw_vec = _sigmoid(raw_vec)
            score_vector = _apply_platt(raw_vec, frozen[name]["calibrator"])
            threshold = frozen[name]["threshold"]
        prediction_rows.extend(_prediction_rows([cases[i] for i in test_indexes],
                                                [labels[i] for i in test_indexes], score_vector,
                                                threshold=threshold, model_name=name))
    baseline_results, baseline_predictions = _baseline_development_test(cases, labels, indexes, y, critical, mask)
    test_results.update(baseline_results)
    for model_name, rows in baseline_predictions.items():
        prediction_rows.extend(rows)
    # Write V3 replay predictions on a separate result file; no V3 artifact is changed.
    write_json(OUT / "DEVELOPMENT_TEST_RESULTS.json", {"status": "DEVELOPMENT_ONLY_NOT_GENERATOR_C",
               "models": test_results, "locked_test_case_count": int(len(test_indexes)),
               "thresholds_frozen_before_development_test": True,
               "semantic_rule_explanations": rule_explanations})
    write_json(OUT / "DEVELOPMENT_TEST_PREDICTIONS.json", {"status": "DEVELOPMENT_ONLY_NOT_GENERATOR_C",
               "rows": prediction_rows, "row_count": len(prediction_rows),
               "locked_test_manifest_sha256": sha(DEV / "dataset_manifest.json")})

    # Freeze the complete model/calibration/threshold contract before Generator C exists.
    frozen_models = {}
    for name, item in frozen.items():
        entry = dict(item)
        if name in saved:
            entry["artifact"] = saved[name]
        frozen_models[name] = entry
    manifest = {
        "release_id": "cobi-evidence-v4.1-semantic-v1",
        "protocol_id": "cobi-evidence-v4.1-c1.0",
        "status": "SYNTHETIC_RESEARCH_ONLY",
        "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED",
        "routing_authorized": False, "approval_authorized": False,
        "checkout_consumes_research_outputs": False,
        "development_manifest_sha256": sha(DEV / "dataset_manifest.json"),
        "protocol_sha256": sha(OUT / "experiment_protocol_c.json"),
        "protocol_amendments_sha256": {
            "amendment_1": sha(OUT / "EXPERIMENT_PROTOCOL_AMENDMENT_1.json"),
            "amendment_2": sha(OUT / "EXPERIMENT_PROTOCOL_AMENDMENT_2.json"),
        },
        "feature_names": FEATURE_NAMES, "models": frozen_models,
        "selected_hybrid_base": hybrid_base,
        "implementation_sha256": {
            "semantic_evidence.py": sha(ROOT / "evidence_ai/semantic_evidence.py"),
            "v4_1_training.py": sha(ROOT / "evidence_ai/v4_1_training.py"),
            "v4_1_generator_dev.py": sha(ROOT / "evidence_ai/v4_1_generator_dev.py"),
        },
        "xgboost_available": XGBOOST_AVAILABLE, "xgboost_import_error": XGBOOST_IMPORT_ERROR,
        "source_pair_held_out_for_c": ["payroll", "merchant"],
        "model_training": True, "generator_c_loaded": False,
    }
    write_json(MODELS_DIR / "frozen_model_manifest.json", manifest)
    hashes = {}
    for path in sorted(MODELS_DIR.iterdir()):
        if path.is_file() and path.name != "frozen_release.json":
            hashes[path.name] = sha(path)
    write_json(MODELS_DIR / "frozen_release.json", {"release_id": manifest["release_id"],
               "manifest_sha256": sha(MODELS_DIR / "frozen_model_manifest.json"),
               "artifact_sha256": hashes, "frozen_before_generator_c": True,
               "generator_c_created": False, "validation_status": "EVIDENCE_AI_VALIDATION_BLOCKED"})
    return {"release_id": manifest["release_id"], "hybrid_base": hybrid_base,
            "model_thresholds": {name: row.get("threshold") for name, row in frozen_models.items()},
            "threshold_status": {name: row.get("threshold_status") for name, row in frozen_models.items()},
            "development_test_models": test_results,
            "frozen_manifest_sha256": sha(MODELS_DIR / "frozen_model_manifest.json"),
            "frozen_release_sha256": sha(MODELS_DIR / "frozen_release.json")}


if __name__ == "__main__":
    torch.use_deterministic_algorithms(True)
    print(json.dumps(train_and_freeze(), indent=2))
