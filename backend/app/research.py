"""Read-only benchmark results and a local request queue, isolated from checkout policy."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt

router = APIRouter(prefix="/api/research", tags=["research benchmark"])
ROOT = Path(os.environ.get("COBI_RESEARCH_ROOT", Path(__file__).resolve().parents[2]))
EXPERIMENT_ID = "uci350-v2.0"
MODEL_ID = "uci350-v2.0-selected"
ARTIFACTS = {
    "report.json", "candidates.json", "selection.json", "model_manifest.json",
    "preprocessing.json", "calibrator.json", "model.json", "model.pt", "reliability.svg", "training.svg",
    "experiment-results.svg",
}


class ExperimentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: Literal["UCI_350"] = "UCI_350"
    protocol: Literal["uci350-v2.0"] = "uci350-v2.0"


class BenchmarkPredictionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rows: list[dict[str, StrictInt]] = Field(min_length=1, max_length=100)
    source_domain: str
    label_horizon: str
    feature_signature: str = Field(max_length=64)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_dir():
    return ROOT / "reports/final" / EXPERIMENT_ID


def request_path():
    return run_dir().parent / f"{EXPERIMENT_ID}-request.json"


def verified_bundle():
    """Check the release and its local files before surfacing completed status."""
    run = run_dir()
    try:
        state = read(run / "status.json")
        if state["status"] != "PUBLIC_DATA_BENCHMARKED":
            return None
        directory = run / "model"
        manifest = read(directory / "model_manifest.json")
        contract = manifest["feature_contract"]
        signature = hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        checksums = manifest["sha256"]
        expected_model = "model.pt" if manifest["family"] == "mlp" else "model.json"
        if (manifest["model_id"] != MODEL_ID or manifest["status"] != "BENCHMARK_ONLY"
                or manifest["checkout_compatible"] is not False or manifest["feature_signature"] != signature
                or manifest["source_domain"] != "TAIWAN_CREDIT_CARD_2005"
                or manifest["label_horizon"] != "next payment month"
                or manifest["evaluation_status"] != "PUBLIC_DATA_BENCHMARKED"
                or set(checksums) != {expected_model, "preprocessing.json", "calibrator.json"}
                or any(digest(directory / name) != value for name, value in checksums.items())
                or digest(run / "report.json") != manifest["report_sha256"]):
            raise ValueError("Model verification failed")
        report = read(run / "report.json")
        candidates = read(run / "candidates.json")
        if (report["status"], report["feature_signature"], report["experiment_id"]) != (
            "PUBLIC_DATA_BENCHMARKED", signature, EXPERIMENT_ID
        ):
            raise ValueError("Report provenance mismatch")
        return manifest, report, candidates
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, "Benchmark release failed integrity verification.") from exc


@router.get("/datasets")
def datasets():
    manifest = ROOT / "data/manifest/uci350.yaml"
    uci = read(manifest) if manifest.is_file() else {"dataset_id": "UCI_350", "status": "NOT_ACQUIRED"}
    return {"items": [
        uci,
        {"dataset_id": "HOME_CREDIT", "status": "DOWNLOAD_NOT_AUTHORIZED"},
        {"dataset_id": "BANK", "status": "BANK_EXTERNAL_VALIDATION_BLOCKED"},
    ]}


@router.get("/experiments/{experiment_id}")
def experiment(experiment_id: str):
    if experiment_id != EXPERIMENT_ID:
        raise HTTPException(404, "Unknown experiment.")
    run = run_dir()
    if not (run / "status.json").is_file():
        return {"experiment_id": experiment_id, "status": "QUEUED" if request_path().is_file() else "NOT_EXECUTED"}
    state = read(run / "status.json")
    bundle = verified_bundle()
    result = {"experiment_id": experiment_id, **state}
    if bundle:
        manifest, report, candidates = bundle
        artifact_names = sorted(name for name in ARTIFACTS if artifact_path(name).is_file())
        result.update(report=report, candidates=candidates, model_id=manifest["model_id"], artifacts=artifact_names)
    return result


@router.post("/experiments")
def request_experiment(payload: ExperimentIn, response: Response):
    result = experiment(payload.protocol)
    if result["status"] != "NOT_EXECUTED":
        return {"experiment_id": payload.protocol, "status": result["status"], "existing": True}
    manifest = ROOT / "data/manifest/uci350.yaml"
    if not manifest.is_file() or read(manifest).get("status") != "VERIFIED":
        raise HTTPException(409, "Acquire and verify the official UCI dataset first.")
    try:
        path = request_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as request:
            json.dump(payload.model_dump() | {"requested_at": datetime.now(timezone.utc).isoformat()}, request)
    except FileExistsError:
        pass
    except OSError as exc:
        raise HTTPException(503, "The local research queue is unavailable.") from exc
    response.status_code = 202
    return {"experiment_id": payload.protocol, "status": "QUEUED", "worker_command": "python -m ml.train_pd"}


@router.get("/models")
def models():
    if not (run_dir() / "status.json").is_file():
        return {"items": []}
    bundle = verified_bundle()
    return {"items": [bundle[0]] if bundle else []}


@router.get("/models/{model_id}")
def model(model_id: str):
    if model_id == MODEL_ID:
        items = models()["items"]
        if items:
            return items[0]
    raise HTTPException(404, "Benchmark model unavailable.")


@router.post("/models/{model_id}/predict")
def predict_benchmark(model_id: str, payload: BenchmarkPredictionIn):
    manifest = model(model_id)
    if (payload.source_domain, payload.label_horizon, payload.feature_signature) != (
        manifest["source_domain"], manifest["label_horizon"], manifest["feature_signature"]
    ):
        raise HTTPException(422, "PD_UNAVAILABLE_SCHEMA_MISMATCH")
    try:
        from ml.predict import load, predict
        artifact = load(run_dir() / "model")
    except (ImportError, OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(503, "Local benchmark inference runtime or trusted artifact unavailable.") from exc
    try:
        return predict(artifact, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, "PD_UNAVAILABLE_SCHEMA_MISMATCH") from exc


def artifact_path(name):
    directory = run_dir() / "model" if name in {
        "model_manifest.json", "preprocessing.json", "calibrator.json", "model.json", "model.pt",
    } else run_dir()
    return directory / name


@router.get("/experiments/{experiment_id}/artifacts/{name}")
def artifact(experiment_id: str, name: str):
    if experiment_id != EXPERIMENT_ID or name not in ARTIFACTS:
        raise HTTPException(404, "Unknown public artifact.")
    path = artifact_path(name)
    if not path.is_file() or not verified_bundle():
        raise HTTPException(404, "Verified artifact unavailable.")
    return FileResponse(path, filename=name)
