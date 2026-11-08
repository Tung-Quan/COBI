"""Observed-only tabular/Deep Sets contract. IDs, dates and labels are excluded."""

from hashlib import sha256

import numpy as np
from sklearn.feature_extraction import FeatureHasher

from backend.app.calculations import confidence_score
from evidence_ai.synthetic import CAP, FIELDS, SOURCES
from ml.contracts import canonical

GROUPS = {
    "base": [*(f"log_amount_{field}" for field in FIELDS), *(f"missing_{field}" for field in FIELDS), "ocr_quality"],
    "metadata": ["age_days", "reported_verified", *(f"source_{source}" for source in SOURCES)],
    "relationships": [*(f"peer_gap_{field}" for field in FIELDS), "document_count"],
    "cs": ["coverage", "consistency", "recency", "verification"],
    "embedding": [f"hashed_text_{i}" for i in range(12)],
}
NAMES = [name for names in GROUPS.values() for name in names]
HASHER = FeatureHasher(n_features=12, input_type="string")


def encode(case):
    docs = case["documents"]
    values = np.array([[doc["values"][field] if doc["values"][field] is not None else np.nan
                        for field in FIELDS] for doc in docs])
    peers = np.array([np.median(col[np.isfinite(col)]) if np.isfinite(col).any() else 0.0 for col in values.T])
    finite = np.isfinite(values)
    gaps = np.abs(np.where(finite, values, peers) - peers)
    consistent = int((finite & (gaps <= 100000)).sum())
    score = confidence_score({
        "monthly_income_vnd": [1] * case["income_history_months"],
        "evidence": {"reconciliation_fields_consistent": consistent, "reconciliation_fields_total": values.size,
                     "age_days": float(np.mean([d["age_days"] for d in docs])),
                     "verified_sources": sum(d["verified"] for d in docs), "available_sources": len(docs)}
    })
    vector = np.zeros((CAP, len(NAMES)), dtype=np.float32)
    for i, doc in enumerate(docs):
        text = doc["text"].lower()
        embedding = HASHER.transform([[text[k:k + 3] for k in range(len(text) - 2)]]).toarray()[0]
        embedding = embedding / max(1., np.linalg.norm(embedding))
        vector[i] = [*np.log1p(np.nan_to_num(values[i])), *(~finite[i]), doc["ocr_quality"],
                     doc["age_days"], doc["verified"], *(doc["source"] == source for source in SOURCES),
                     *np.log1p(gaps[i]), len(docs), *score["subscores"].values(), *embedding]
    return vector, 1 - score["score"]


def build_arrays(cases, labels):
    gold = {row["case_key"]: row for row in labels}
    shape = (len(cases), CAP)
    data = {"x": np.empty((*shape, len(NAMES)), dtype=np.float32),
            "mask": np.zeros(shape, dtype=bool), "y": np.zeros(shape, dtype=np.int64),
            "critical": np.zeros(shape, dtype=bool), "fields": np.full((*shape, len(FIELDS)), -1, dtype=np.float32),
            "cs_risk": np.zeros(len(cases), dtype=np.float64)}
    for i, case in enumerate(cases):
        data["x"][i], data["cs_risk"][i] = encode(case)
        targets = gold[case["case_key"]]["documents"]
        for j, target in enumerate(targets):
            document = case["documents"][j]
            if (document["document_key"] != target["document_key"]
                    or sha256(canonical(document)).hexdigest() != target["observed_payload_sha256"]):
                raise ValueError("Observed/label alignment mismatch")
            data["mask"][i, j] = True
            data["y"][i, j] = target["material_evidence_error"]
            data["critical"][i, j] = target["critical_evidence_error"]
            data["fields"][i, j] = [target["field_extraction_error"].get(field, -1) for field in FIELDS]
    return data


def fit_scaler(data):
    valid = data["x"][data["mask"]].astype("float64")
    scale = valid.std(axis=0)
    scale[scale < 1e-8] = 1
    return {"names": NAMES, "mean": valid.mean(axis=0).tolist(), "scale": scale.tolist(), "fit_documents": len(valid)}


def apply_scaler(data, scaler):
    if scaler["names"] != NAMES:
        raise ValueError("Feature order does not match training")
    result = data.copy()
    result["x"] = ((data["x"] - scaler["mean"]) / scaler["scale"]).astype(np.float32)
    result["x"][~result["mask"]] = 0
    return result
