"""Exportable train-fitted z-scoring and fixed-category one-hot encoding."""

import numpy as np
from sklearn.preprocessing import StandardScaler

from ml.contracts import ALLOWLIST, CATEGORIES, NUMERIC, STATUS


def fit(frame):
    scaler = StandardScaler().fit(frame[NUMERIC])
    return {
        "numeric_names": NUMERIC, "status_names": STATUS, "status_categories": CATEGORIES,
        "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(), "fit_rows": len(frame),
    }


def transform(frame, state):
    if frame.columns.tolist() != ALLOWLIST:
        raise ValueError("PD_UNAVAILABLE_SCHEMA_MISMATCH")
    numeric = (frame[state["numeric_names"]].to_numpy() - state["mean"]) / state["scale"]
    categorical = frame[state["status_names"]].to_numpy()[:, :, None] == state["status_categories"]
    return np.concatenate([numeric, categorical.reshape(len(frame), -1)], axis=1).astype(np.float32)
