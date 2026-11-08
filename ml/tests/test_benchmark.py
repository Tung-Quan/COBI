"""Verification of the published experiment without reopening the test partition."""

import json
from shutil import copytree

import numpy as np
import pytest

from ml.candidates import select
from ml.contracts import ALLOWLIST, DOMAIN, HORIZON, NUMERIC, SIGNATURE, TARGET, sha
from ml.predict import CANONICAL_RUN, load, load_manifest, predict
from ml.split import LOCK, PROTOCOL, assignments, audit_membership, dataset

MODEL = CANONICAL_RUN / "model"


def read(path):
    return json.loads(path.read_text())


def test_locked_dataset_and_training_only_fit():
    assert LOCK.is_file(), "Acquire UCI and freeze the split before running research verification"
    manifest, data = dataset()
    config = read(PROTOCOL)
    lock = read(LOCK)
    membership = lock["membership"]
    assert manifest["label_counts"] == {"0": 23364, "1": 6636}
    assert set(ALLOWLIST).isdisjoint({"ID", "SEX", "EDUCATION", "MARRIAGE", "AGE", TARGET})
    assert membership == assignments(data[TARGET], config)
    assert lock["cohorts"] == audit_membership(data[TARGET], membership, config)
    training = data.loc[membership["train"], NUMERIC]
    scaler = read(MODEL / "preprocessing.json")
    assert scaler["fit_rows"] == len(training) == 18000
    np.testing.assert_allclose(scaler["mean"], training.mean(), rtol=1e-12)
    np.testing.assert_allclose(scaler["scale"], training.std(ddof=0), rtol=1e-12)
    bad = membership | {"test": membership["test"][:-1] + [membership["train"][0]]}
    with pytest.raises(ValueError, match="overlap"):
        audit_membership(data[TARGET], bad, config)


def test_winner_history_and_ci_provenance():
    from types import SimpleNamespace
    import pandas as pd

    rows = read(CANONICAL_RUN / "candidates.json")
    config = read(PROTOCOL)
    result = read(CANONICAL_RUN / "report.json")
    manifest = load_manifest(MODEL)
    winner = select([SimpleNamespace(**row) for row in rows], config["minimum_validation_improvement_over_simpler"])
    assert winner.candidate == manifest["selected_candidate"] == result["selected_candidate"]
    for row in rows:
        assert np.isfinite(row["validation_loss"])
        assert "test" not in row
        extension = "pt" if row["family"] == "mlp" else "json"
        assert sha(CANONICAL_RUN / "checkpoints" / f"{row['candidate']}.{extension}") == row["checkpoint_sha256"]
        if row["family"] == "mlp":
            history = row["history"]
            csv = pd.read_csv(CANONICAL_RUN / f"batch-{row['candidate']}.csv")
            assert len(csv) == history[-1]["optimizer_updates"]
            assert history[-1]["best_checkpoint_sha256"] == row["checkpoint_sha256"]
            assert (csv.groupby("epoch").batch_rows.sum() == 18000).all()
            assert np.isfinite(csv.gradient_l2_pre_clip).all()
    assert manifest["report_sha256"] == sha(CANONICAL_RUN / "report.json")
    assert manifest["split"] == result["split"]
    local_lock = read(LOCK)
    for key in ("cohorts", "seed", "strategy", "normalized_sha256", "protocol_sha256", "split_code_sha256"):
        assert manifest["split"][key] == local_lock[key]
    assert result["bootstrap"]["replicates"] == 1000
    for model in result["models"].values():
        assert sum(row["n"] for row in model["reliability"]) == 4500
        for value in model["metrics"].values():
            assert np.isfinite([value["estimate"], *value["ci95"]]).all()


def test_reload_and_schema_guards(tmp_path):
    _, data = dataset()
    sample = data.loc[read(LOCK)["membership"]["validation"][:5], ALLOWLIST].to_dict("records")
    contract = {"source_domain": DOMAIN, "label_horizon": HORIZON, "feature_signature": SIGNATURE}
    original = predict(load(MODEL), sample, **contract)
    restarted = predict(load(MODEL), sample, **contract)
    assert original == restarted and original["risk_source"] == "PUBLIC_BENCHMARK_ONLY"
    assert all(0 < value < 1 for value in original["calibrated"])
    with pytest.raises(ValueError, match="PD_UNAVAILABLE_SCHEMA_MISMATCH"):
        predict(load(MODEL), sample, **(contract | {"feature_signature": "forged"}))
    with pytest.raises(ValueError, match="PD_UNAVAILABLE_SCHEMA_MISMATCH"):
        predict(load(MODEL), [sample[0] | {"AGE": 35}], **contract)
    corrupt = tmp_path / "model"
    copytree(MODEL, corrupt)
    (corrupt / "preprocessing.json").write_text("{}")
    with pytest.raises(ValueError, match="Corrupted model artifact"):
        load_manifest(corrupt)
