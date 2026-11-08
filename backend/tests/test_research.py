import json
from shutil import copytree

import pytest

from app import research


def test_release_is_verified_and_requests_are_idempotent(client):
    if not (research.run_dir() / "status.json").is_file():
        pytest.skip("Canonical public research release missing")
    result = client.get("/api/research/experiments/uci350-v2.0").json()
    assert result["status"] == "PUBLIC_DATA_BENCHMARKED"
    assert len(result["candidates"]) == 11
    assert result["report"]["split"]["split_overlap"] is False
    model = client.get("/api/research/models/uci350-v2.0-selected").json()
    assert model["status"] == "BENCHMARK_ONLY"
    assert model["checkout_compatible"] is False
    assert client.post("/api/research/experiments", json={}).json()["existing"] is True
    assert client.get("/api/research/experiments/uci350-v2.0/artifacts/test_predictions.csv").status_code == 404
    assert client.get("/api/research/experiments/uci350-v2.0/artifacts/model.json").status_code == 200


def test_corrupted_artifact_fails_closed(client, tmp_path, monkeypatch):
    source = research.run_dir()
    if not (source / "report.json").is_file():
        pytest.skip("Canonical public research release missing")
    monkeypatch.setattr(research, "ROOT", tmp_path)
    copytree(source, research.run_dir(), ignore=lambda _, names: set(names) - {
        "model", "model_manifest.json", "preprocessing.json", "calibrator.json", "model.json", "model.pt", "report.json", "status.json", "candidates.json",
    })
    (research.run_dir() / "model/calibrator.json").write_text("{}")
    assert client.get("/api/research/models").status_code == 503
    assert client.get("/api/research/experiments/uci350-v2.0").status_code == 503


def test_unstarted_experiment_request_does_not_claim_success(client, tmp_path, monkeypatch):
    monkeypatch.setattr(research, "ROOT", tmp_path)
    manifest = tmp_path / "data/manifest/uci350.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"dataset_id": "UCI_350", "status": "VERIFIED"}))
    assert client.get("/api/research/experiments/uci350-v2.0").json()["status"] == "NOT_EXECUTED"
    assert client.post("/api/research/experiments", json={"dataset_id": "BANK"}).status_code == 422
    queued = client.post("/api/research/experiments", json={})
    assert queued.status_code == 202 and queued.json()["status"] == "QUEUED"
    assert client.get("/api/research/models").json() == {"items": []}
