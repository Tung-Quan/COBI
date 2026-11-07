from __future__ import annotations

import json
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .calculations import DEFAULT_ROUTE_COSTS_VND, calculate_application
from .db import (
    append_audit_event,
    audit_history,
    create_application,
    export_bundle,
    get_application,
    persist_calculation,
    initialize_database,
    list_applications,
)
from .schemas import ApplicationCreate, ReviewActionIn, SimulationIn


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
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _require_application(application_id: str) -> dict[str, Any]:
    application = get_application(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail=f"Application {application_id} was not found.")
    return application


def _decorate(application: dict[str, Any]) -> dict[str, Any]:
    bundle = calculate_application(application)
    persist_calculation(application["application_id"], bundle.assessment, bundle.routing)
    return {
        **application,
        "assessment": bundle.assessment,
        "routing": bundle.routing,
        "review_history": audit_history(application["application_id"]),
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
    try:
        create_application(data)
    except Exception as exc:
        if "UNIQUE constraint" in str(exc):
            raise HTTPException(status_code=409, detail="That application ID already exists.") from exc
        raise
    append_audit_event(
        data["application_id"], "application_received", None,
        "Application received in synthetic demonstration workflow.",
        {"scoring_performed": False},
    )
    return _decorate(data)


@app.get("/api/applications/{application_id}", tags=["applications"])
def application_detail(application_id: str) -> dict[str, Any]:
    return _decorate(_require_application(application_id))


@app.post("/api/applications/{application_id}/simulate", tags=["simulation"])
def simulate(application_id: str, payload: SimulationIn) -> dict[str, Any]:
    original = _require_application(application_id)
    scenario = deepcopy(original)
    updates = payload.model_dump(exclude_none=True, exclude={"route_costs_vnd", "max_dti"})
    if "evidence_quality" in updates:
        quality = updates.pop("evidence_quality")
        total = max(int(scenario["evidence"].get("reconciliation_fields_total", 14)), 1)
        scenario["evidence"]["reconciliation_fields_consistent"] = round(total * quality)
        scenario["evidence"]["verified_sources"] = round(
            int(scenario["evidence"].get("available_sources", 10)) * quality
        )
    if "evidence_age_days" in updates:
        scenario["evidence"]["age_days"] = updates.pop("evidence_age_days")
    scenario.update(updates)
    bundle = calculate_application(
        scenario,
        route_costs_vnd=payload.route_costs_vnd,
        max_dti=payload.max_dti,
    )
    return {
        "application_id": application_id,
        "scenario_inputs": updates | ({"evidence_quality": payload.evidence_quality} if payload.evidence_quality is not None else {}) |
        ({"evidence_age_days": payload.evidence_age_days} if payload.evidence_age_days is not None else {}) |
        ({"route_costs_vnd": payload.route_costs_vnd} if payload.route_costs_vnd is not None else {}) |
        {"max_dti": payload.max_dti},
        "assessment": bundle.assessment,
        "routing": bundle.routing,
        "persisted": False,
    }


@app.post("/api/applications/{application_id}/review", tags=["human review"])
def review_action(application_id: str, payload: ReviewActionIn) -> dict[str, Any]:
    application = _require_application(application_id)
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
    event = append_audit_event(
        application_id,
        action,
        selected_route,
        payload.reason,
        {
            "proposed_route": current.routing["recommended_route"],
            "eligible_routes": eligible,
            "loan_approval_created": False,
            "scoring_status": current.assessment["status"],
        },
    )
    return {"event": event, "review_history": audit_history(application_id), "loan_approval_created": False}


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
        if item["assessment"]["scoring_performed"]:
            scoreable += 1
            baseline = "STANDARD_REVIEW"
            baseline_cost += DEFAULT_ROUTE_COSTS_VND[baseline]
            confidence_values.append(item["assessment"]["confidence"]["score"])
            pd_values.append(item["assessment"]["risk"]["score"])
        else:
            baseline_cost += DEFAULT_ROUTE_COSTS_VND["HOLD_FOR_HUMAN_HANDLING"]
    return {
        "synthetic_operational_snapshot": True,
        "interpretation": "Scenario outputs over the seeded synthetic cases; not observed bank performance.",
        "application_count": len(items),
        "scoreable_count": scoreable,
        "blocked_count": len(items) - scoreable,
        "route_distribution": route_counts,
        "mean_confidence_index": sum(confidence_values) / len(confidence_values) if confidence_values else None,
        "mean_demo_pd": sum(pd_values) / len(pd_values) if pd_values else None,
        "proposed_routing_cost_estimate_vnd": proposed_cost,
        "baseline_all_standard_cost_estimate_vnd": baseline_cost,
        "estimated_cost_difference_vnd": baseline_cost - proposed_cost,
        "baseline_note": "Illustrative comparison to STANDARD_REVIEW for scoreable cases and HOLD for blocked cases; not a measured saving.",
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
    from .calculations import (
        CS_WEIGHTS,
        DEMO_RISK_SLOPES,
        DEMO_RISK_STATUS,
        EAD_ASSUMPTION_VND,
        ENHANCED_CONFIDENCE_BELOW,
        ENHANCED_PD_ABOVE,
        FAST_TRACK_MAX_PD,
        FAST_TRACK_MIN_CONFIDENCE,
        LGD_ASSUMPTION,
        MAX_DTI_ASSUMPTION,
        RECENCY_DECAY_DAYS,
    )

    return {
        "confidence_weights": CS_WEIGHTS,
        "recency_decay_days": RECENCY_DECAY_DAYS,
        "maximum_dti_assumption": MAX_DTI_ASSUMPTION,
        "route_thresholds": {
            "fast_track_min_confidence": FAST_TRACK_MIN_CONFIDENCE,
            "fast_track_max_pd_demo": FAST_TRACK_MAX_PD,
            "enhanced_review_when_confidence_below": ENHANCED_CONFIDENCE_BELOW,
            "enhanced_review_when_pd_demo_above": ENHANCED_PD_ABOVE,
        },
        "risk_status": DEMO_RISK_STATUS,
        "risk_slopes": DEMO_RISK_SLOPES,
        "lgd_assumption": LGD_ASSUMPTION,
        "ead_assumption_vnd": EAD_ASSUMPTION_VND,
        "route_costs_vnd": DEFAULT_ROUTE_COSTS_VND,
        "provenance": "Prompt-level formulas and expected values; prototype coefficient/cost parity is unverified because named reference files were not supplied.",
    }
