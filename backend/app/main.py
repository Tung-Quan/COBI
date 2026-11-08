from __future__ import annotations

import json
from contextlib import asynccontextmanager
from copy import deepcopy
from hashlib import sha256
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import calculations as policy
from .calculations import DEFAULT_ROUTE_COSTS_VND, calculate_application
from .db import (
    append_audit_event,
    audit_history,
    connect,
    create_application,
    export_bundle,
    get_application,
    persist_calculation,
    initialize_database,
    list_applications,
    revoke_consent,
)
from .research import router as research_router
from .evidence_research import router as evidence_research_router
from .evidence_research_v41 import router as evidence_research_v41_router
from .schemas import ApplicationCreate, AssessmentSimulationIn, ReviewActionIn, ReviewReason, SimulationIn


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Checkout Credit Copilot API",
    description=(
        "Synthetic, deterministic credit-review demonstration. No endpoint approves or creates a real loan. "
        "Scores and policy values are illustrative and require human review."
    ),
    version="2.0.0",
    lifespan=lifespan,
)
app.include_router(research_router)
app.include_router(evidence_research_router)
app.include_router(evidence_research_v41_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Avoid reflecting arbitrary feature values or non-finite JSON input.
    return JSONResponse(status_code=422, content={"detail": [
        {key: error[key] for key in ("loc", "msg", "type")} for error in exc.errors()
    ]})


def _require_application(application_id: str, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
    application = get_application(application_id, connection)
    if application is None:
        raise HTTPException(status_code=404, detail=f"Application {application_id} was not found.")
    return application


def _decorate(application: dict[str, Any]) -> dict[str, Any]:
    bundle = calculate_application(application)
    persist_calculation(application, bundle.assessment, bundle.routing)
    return {
        **application,
        "assessment": bundle.assessment,
        "routing": bundle.routing,
        "review_history": audit_history(application["application_id"]),
    }


def _audit_trace(application: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
    snapshot = json.dumps(application, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return {
        "input_sha256": sha256(snapshot.encode()).hexdigest(), "policy_version": assessment["policy_version"],
        "fixture_version": assessment["fixture_version"], "model_version": assessment["model"]["version"],
        "risk_source": assessment["risk_source"],
    }


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "synthetic_demo", "decision_authority": "human_only"}


@app.get("/api/applications", tags=["applications"])
def applications(
    q: str | None = Query(default=None, max_length=120),
    route: str | None = None,
    blocked_only: bool = False,
) -> dict[str, Any]:
    items = [_decorate(item) for item in list_applications()]
    if q:
        needle = q.casefold()
        items = [item for item in items if needle in " ".join([
            item["application_id"], item.get("borrower_label", ""), item.get("merchant", ""),
            item.get("purchase_description", ""), *item.get("tags", []),
        ]).casefold()]
    if route:
        items = [item for item in items if item["routing"]["recommended_route"] == route]
    if blocked_only:
        items = [item for item in items if not item["assessment"]["scoring_performed"]]
    return {"items": items, "total": len(items), "synthetic_data": True}


@app.post("/api/applications", status_code=201, tags=["applications"])
def submit_application(payload: ApplicationCreate) -> dict[str, Any]:
    data = payload.model_dump()
    data["tags"] = ["Submitted in demo"]
    data["fixture_version"] = "submitted-v2.0"
    try:
        create_application(data, _audit_trace(data, calculate_application(data).assessment))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="That application ID already exists.") from exc
    return _decorate(data)


@app.get("/api/applications/{application_id}", tags=["applications"])
def application_detail(application_id: str) -> dict[str, Any]:
    return _decorate(_require_application(application_id))


@app.get("/api/assessments/{application_id}/explanation", tags=["methodology"])
def explanation(application_id: str) -> dict[str, Any]:
    application = _require_application(application_id)
    bundle = calculate_application(application)
    return {"application_id": application_id,
            "inputs": application if bundle.assessment["scoring_performed"] else None,
            "assessment": bundle.assessment, "routing": bundle.routing,
            "trace": _audit_trace(application, bundle.assessment)}


@app.post("/api/assessments/simulate", tags=["simulation"])
def simulate_assessment(payload: AssessmentSimulationIn) -> dict[str, Any]:
    return simulate(payload.application_id, SimulationIn.model_validate(payload.model_dump(exclude={"application_id"})))


@app.post("/api/applications/{application_id}/simulate", tags=["simulation"])
def simulate(application_id: str, payload: SimulationIn) -> dict[str, Any]:
    original = _require_application(application_id)
    scenario = deepcopy(original)
    updates = payload.model_dump(exclude_none=True, exclude={"route_costs_vnd", "max_dti", "residual_buffer",
                                                             "benchmark_model_id", "proposed_installment_vnd"})
    if "evidence_quality" in updates:
        quality = updates.pop("evidence_quality")
        total = int(scenario["evidence"].get("reconciliation_fields_total", 0))
        scenario["evidence"]["reconciliation_fields_consistent"] = round(total * quality)
        scenario["evidence"]["verified_sources"] = round(
            int(scenario["evidence"].get("available_sources", 0)) * quality
        )
    if "evidence_age_days" in updates:
        scenario["evidence"]["age_days"] = updates.pop("evidence_age_days")
    scenario.update(updates)
    bundle = calculate_application(
        scenario,
        route_costs_vnd=payload.route_costs_vnd,
        max_dti=payload.max_dti,
        buffer=payload.residual_buffer,
        installment_override=payload.proposed_installment_vnd,
        model_requested=payload.benchmark_model_id is not None,
    )
    return {
        "application_id": application_id,
        "scenario_inputs": payload.model_dump(exclude_none=True),
        "assessment": bundle.assessment,
        "routing": bundle.routing,
        "persisted": False,
    }


@app.post("/api/applications/{application_id}/review", tags=["human review"])
def review_action(application_id: str, payload: ReviewActionIn) -> dict[str, Any]:
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        application = _require_application(application_id, connection)
        event = _record_review(application, payload, connection)
    return {"event": event, "review_history": audit_history(application_id), "loan_approval_created": False}


def _record_review(application, payload, connection):
    current = calculate_application(application)
    eligible = current.routing["eligible_routes"]
    action = payload.action
    selected_route: str | None = None
    if action == "override_route":
        if payload.route is None:
            raise HTTPException(status_code=422, detail="A route is required for an override.")
        if payload.route not in eligible:
            raise HTTPException(status_code=422, detail="The requested route is ineligible under the current hard policy gates.")
        selected_route = payload.route
    elif action == "confirm_route":
        selected_route = payload.route or current.routing["recommended_route"]
        if selected_route != current.routing["recommended_route"]:
            raise HTTPException(status_code=422, detail="Use override_route to record a different eligible route with an explanation.")
    else:
        selected_route = payload.route or current.routing["recommended_route"]
        if selected_route not in eligible:
            raise HTTPException(status_code=422, detail="The requested route is ineligible under the current hard policy gates.")
    return append_audit_event(
        application["application_id"],
        action,
        selected_route,
        payload.reason,
        {
            **_audit_trace(application, current.assessment),
            "proposed_route": current.routing["recommended_route"],
            "eligible_routes": eligible,
            "loan_approval_created": False,
            "scoring_status": current.assessment["status"],
        },
        connection=connection,
    )


@app.post("/api/applications/{application_id}/revoke-consent", tags=["human review"])
def stop_scoring(application_id: str, payload: ReviewReason) -> dict[str, Any]:
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        application = _require_application(application_id, connection)
        if application.get("consent_revoked_at"):
            raise HTTPException(status_code=409, detail="Consent was already revoked.")
        blocked = calculate_application(application | {"consent": False})
        event = revoke_consent(application, payload.reason, _audit_trace(application, blocked.assessment), connection)
    return {"event": event, "assessment": blocked.assessment, "routing": blocked.routing}


@app.get("/api/metrics", tags=["evaluation"])
def metrics() -> dict[str, Any]:
    items = [_decorate(item) for item in list_applications()]
    route_counts: dict[str, int] = {route: 0 for route in DEFAULT_ROUTE_COSTS_VND}
    proposed_cost = baseline_cost = 0.0
    scoreable = 0
    confidence_values: list[float] = []
    pd_values: list[float] = []
    for item in items:
        proposed = item["routing"]["recommended_route"]
        route_counts[proposed] += 1
        proposed_cost += DEFAULT_ROUTE_COSTS_VND[proposed]
        eligible = item["routing"]["eligible_routes"]
        baseline = next(route for route in ("STANDARD_REVIEW", "ENHANCED_REVIEW", "HOLD_FOR_HUMAN_HANDLING")
                        if route in eligible)
        baseline_cost += DEFAULT_ROUTE_COSTS_VND[baseline]
        if item["assessment"]["scoring_performed"]:
            scoreable += 1
            confidence_values.append(item["assessment"]["confidence"]["score"])
            pd_values.append(item["assessment"]["risk"]["score"])
    return {
        "synthetic_operational_snapshot": True,
        "comparison_status": "SIMULATED_ROUTE_COMPARISON",
        "interpretation": "Scenario outputs for synthetic workbench cases. Measured bank outcomes are unavailable.",
        "application_count": len(items),
        "scoreable_count": scoreable,
        "blocked_count": len(items) - scoreable,
        "route_distribution": route_counts,
        "mean_confidence_index": sum(confidence_values) / len(confidence_values) if confidence_values else None,
        "mean_demo_pd": sum(pd_values) / len(pd_values) if pd_values else None,
        "proposed_routing_cost_estimate_vnd": proposed_cost,
        "baseline_all_standard_cost_estimate_vnd": baseline_cost,
        "estimated_cost_difference_vnd": baseline_cost - proposed_cost,
        "baseline_note": "Fixed order: standard when eligible, otherwise enhanced or hold. All costs are synthetic assumptions.",
    }


@app.get("/api/evaluation", tags=["evaluation"])
def evaluation() -> dict[str, Any]:
    items = [_decorate(item) for item in list_applications()]
    logs = []
    for item in items:
        assessment = item["assessment"]
        logs.append({
            "application_id": item["application_id"],
            "assessment_status": assessment["status"],
            "recommended_route": item["routing"]["recommended_route"],
            "eligible_routes": item["routing"]["eligible_routes"],
            "confidence_index": assessment["confidence"]["score"] if assessment["confidence"] else None,
            "pd_demo": assessment["risk"]["score"] if assessment["risk"] else None,
            "risk_label": assessment["risk"]["label"] if assessment["risk"] else None,
        })
    return {
        "evaluation_type": "Synthetic routing demonstration",
        "measured_model_performance": False,
        "logs": logs,
        "summary": "No observed outcomes, repayment histories, trained model metrics, or measured business improvements are present.",
    }


@app.get("/api/export", tags=["evaluation"])
def export_json() -> dict[str, Any]:
    return export_bundle()


@app.get("/api/assumptions", tags=["methodology"])
def assumptions() -> dict[str, Any]:
    return {
        "policy_version": policy.POLICY_VERSION,
        "demo_model_version": policy.DEMO_MODEL_VERSION,
        "confidence_weights": policy.CS_WEIGHTS,
        "recency_decay_days": policy.RECENCY_DECAY_DAYS,
        "maximum_dti_assumption": policy.MAX_DTI_ASSUMPTION,
        "residual_buffer": policy.RESIDUAL_BUFFER,
        "percentile_convention": "linear (Hyndman-Fan type 7)",
        "route_thresholds": {
            "fast_track_min_confidence": policy.FAST_TRACK_MIN_CONFIDENCE,
            "enhanced_review_when_confidence_below": policy.ENHANCED_CONFIDENCE_BELOW,
        },
        "risk_status": policy.DEMO_RISK_STATUS,
        "risk_slopes": policy.DEMO_RISK_SLOPES,
        "risk_intercept": policy.DEMO_INTERCEPT,
        "lgd_assumption": policy.LGD_ASSUMPTION,
        "ead_basis": "principal at origination",
        "route_costs_vnd": DEFAULT_ROUTE_COSTS_VND,
        "provenance": "Versioned synthetic policy assumptions. Bank validation required.",
    }
