"""Serve verified Evidence AI research artifacts and a fail-closed shadow contract."""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from .calculations import _mandatory_gates
from .db import get_application
from .research import ROOT, digest
from .security import require_user_id

router = APIRouter(prefix="/api/evidence-ai", tags=["evidence research"])
BLOCKED = "EVIDENCE_AI_VALIDATION_BLOCKED"
OUTPUT = ROOT / "reports/evidence-v3"
V4_OUTPUT = ROOT / "reports/evidence-v4"
RUNS = {"synthetic", "cord-extraction"}
PUBLIC_ARTIFACTS = {"report.json", "training_history.json", "split_manifest.json", "split_lock.json",
                    "selection_lock.json", "provenance.json", "model_manifest.json", "replay_uncertainty.json"}
V4_PUBLIC_FIGURES = {
    "cost_safety_frontier.svg", "critical_recall_comparison.svg", "review_workload_comparison.svg",
    "generator_shift_performance.svg", "scenario_failure_matrix.svg", "generalization_gap.svg",
    "business_cost_sensitivity.svg", "business_break_even.svg",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def verified_run(name):
    run = OUTPUT / name
    release_path = run / "release.json"
    if not release_path.is_file():
        return None
    try:
        release = load_json(release_path)
        if digest(run / "report.json") != release["report_sha256"]:
            raise ValueError("Evidence report checksum mismatch")
        report = load_json(run / "report.json")
        if name == "synthetic":
            manifest_path = run / "model/manifest.json"
            if digest(manifest_path) != release["model_manifest_sha256"]:
                raise ValueError("Model manifest checksum mismatch")
            manifest = load_json(manifest_path)
            if (report["status"] != "SYNTHETIC_TECHNICAL_ONLY" or manifest["status"] != report["status"]
                    or manifest["policy_authorized"] is not False or manifest["bank_validated"] is not False):
                raise ValueError("Invalid research authorization")
            files = {"preprocessing.json", *(f"{manifest['selected_variant']}-s{seed}.pt" for seed in manifest["seeds"])}
            if set(manifest["checksums"]) != files or any(
                Path(name).name != name or digest(manifest_path.parent / name) != checksum
                for name, checksum in manifest["checksums"].items()
            ):
                raise ValueError("Invalid evidence model artifacts")
        elif report["status"] != "PUBLIC_RECEIPT_EXTRACTION_PILOT":
            raise ValueError("Invalid extraction status")
        return report
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(503, "Evidence AI release integrity check failed.") from exc


@router.get("/status")
def status():
    path = OUTPUT / "datasets.json"
    data = load_json(path) if path.is_file() else {"datasets": []}
    return data | {"validation_status": BLOCKED, "routing_authorized": False, "approval_authorized": False}


@router.get("/experiments/{name}")
def experiment(name: str):
    if name not in RUNS:
        raise HTTPException(404, "Unknown evidence experiment.")
    report = verified_run(name)
    if report is None:
        return {"status": "NO_VERIFIED_RELEASE"}
    run = OUTPUT / name
    history = load_json(run / "training_history.json")
    if name == "synthetic":
        summary = [{"candidate": row["candidate"],
                    "validation_log_loss": row.get("validation_log_loss") or sum(
                        item["validation_log_loss"] for item in row["runs"]) / len(row["runs"]),
                    "runs": [{"seed": item["seed"], "best_step": item.get("best_epoch", item.get("best_round"))}
                             for item in row["runs"]]} for row in history]
    else:
        summary = [{"epoch": row["epoch"], "validation_f1": row["validation"]["exact_field_micro_f1"]}
                   for row in history]
        replay = run / "replay_uncertainty.json"
        if replay.is_file():
            uncertainty = load_json(replay)
            if (uncertainty["documents"] == report["test"]["documents"]
                    and uncertainty["exact_field_micro_f1"] == report["test"]["exact_field_micro_f1"]):
                report["replay_uncertainty"] = uncertainty
    return report | {"training_summary": summary,
                     "artifacts": sorted(filename for filename in PUBLIC_ARTIFACTS if (run / filename).is_file())}


@router.get("/experiments/{name}/artifacts/{filename}")
def artifact(name: str, filename: str):
    if name not in RUNS or filename not in PUBLIC_ARTIFACTS:
        raise HTTPException(404, "Unknown evidence artifact.")
    path = OUTPUT / name / filename
    if not path.is_file() or verified_run(name) is None:
        raise HTTPException(404, "Verified evidence artifact unavailable.")
    return FileResponse(path, filename=filename)


def _verified_v4_reports():
    manifest_path = V4_OUTPUT / "final_manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = load_json(manifest_path)
        protected = manifest["checksums"]
        required = ("E1_RESULTS.json", "E2_RESULTS.json", "E3_COST_RESULTS.json",
                    "experiment_protocol.json")
        for filename in required:
            path = V4_OUTPUT / filename
            if filename not in protected or not path.is_file() or digest(path) != protected[filename]:
                raise ValueError("V4 result checksum mismatch")
        e1 = load_json(V4_OUTPUT / "E1_RESULTS.json")
        e2 = load_json(V4_OUTPUT / "E2_RESULTS.json")
        e3 = load_json(V4_OUTPUT / "E3_COST_RESULTS.json")
        protocol = load_json(V4_OUTPUT / "experiment_protocol.json")
        if (protocol.get("protocol_id") != "cobi-evidence-v4.0"
                or e1.get("validation_status") != BLOCKED
                or e2.get("validation_status") != BLOCKED
                or e3.get("status") != "ILLUSTRATIVE_ASSUMPTION_BASED_SIMULATION"):
            raise ValueError("Invalid V4 research authorization")
        return manifest, e1, e2, e3
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(503, "V4 evidence research integrity check failed.") from exc


@router.get("/v4/summary")
def v4_summary():
    verified = _verified_v4_reports()
    if verified is None:
        return {"status": "NO_VERIFIED_V4_RELEASE", "validation_status": BLOCKED,
                "routing_authorized": False, "approval_authorized": False}
    manifest, e1, e2, e3 = verified
    return {
        "status": "V4_SYNTHETIC_RESEARCH_AVAILABLE",
        "validation_status": BLOCKED,
        "routing_authorized": False,
        "approval_authorized": False,
        "integrity": {"manifest_version": manifest.get("manifest_version"),
                      "experiment_protocol_sha256": manifest.get("experiment_protocol_sha256")},
        "e1": e1,
        "e2": e2,
        "e3": e3,
    }


@router.get("/v4/figures/{filename}")
def v4_figure(filename: str):
    if filename not in V4_PUBLIC_FIGURES:
        raise HTTPException(404, "Unknown V4 research figure.")
    if _verified_v4_reports() is None:
        raise HTTPException(404, "Verified V4 research figures unavailable.")
    path = V4_OUTPUT / "figures" / filename
    if not path.is_file():
        raise HTTPException(404, "Verified V4 research figure unavailable.")
    return FileResponse(path, filename=filename, media_type="image/svg+xml")


@router.get("/shadow/{application_id}")
def shadow(application_id: str, owner_user_id: str = Depends(require_user_id)):
    application = get_application(application_id, owner_user_id=owner_user_id)
    if application is None:
        raise HTTPException(404, "Application was not found.")
    failed = [gate["key"] for gate in _mandatory_gates(application) if not gate["passed"]]
    return {
        "application_id": application_id, "mode": "SHADOW_ONLY", "validation_status": BLOCKED,
        "status": "BLOCKED_MANDATORY_GATES" if failed else BLOCKED, "failed_gates": failed,
        "material_error_probability": None, "field_probabilities": None,
        "routing_authorized": False, "approval_authorized": False,
        "reason": "Mandatory gates failed." if failed else "This checkout case has no compatible, independently validated evidence model.",
    }
