"""Pure, deterministic calculations for the Checkout Credit Copilot demo.

All thresholds and costs in this module are illustrative configuration. They
are not bank policy. The reference prototype named in the brief was not in the
provided checkout, so the demo risk coefficients below cannot claim parity with
that prototype.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log
from statistics import mean, pstdev
from typing import Any


CS_WEIGHTS = {"coverage": 0.30, "consistency": 0.30, "recency": 0.20, "verification": 0.20}
RECENCY_DECAY_DAYS = 40.0
MAX_HISTORY_MONTHS = 12
MAX_DTI_ASSUMPTION = 0.35
FAST_TRACK_MIN_CONFIDENCE = 0.75
FAST_TRACK_MAX_PD = 0.10
ENHANCED_CONFIDENCE_BELOW = 0.50
ENHANCED_PD_ABOVE = 0.25
LGD_ASSUMPTION = 0.45
EAD_ASSUMPTION_VND = 6_666_600.0
DEMO_ANCHOR_PD = 0.039675

# These coefficients are explicit synthetic demonstration parameters. The
# anchor intercept makes DEMO-001 reproduce the probability supplied in the
# acceptance brief; this is not a fitted, trained, or calibrated model.
DEMO_RISK_SLOPES = {"existing_dti_ratio": 3.00, "income_cv": 1.50, "evidence_gap": 0.80}
DEMO_RISK_STATUS = "DEMO_RISK_SCORE_NOT_CALIBRATED"
DEMO_RISK_ANCHOR = {
    "existing_dti_ratio": 0.1078125,
    "income_cv": 0.12309149097933274,
    "evidence_gap": 1.0 - 0.820938,
}

DEFAULT_ROUTE_COSTS_VND = {
    "HOLD_FOR_HUMAN_HANDLING": 95_000,
    "FAST_TRACK_CANDIDATE": 42_000,
    "STANDARD_REVIEW": 110_000,
    "ENHANCED_REVIEW": 180_000,
}
ROUTE_ORDER = (
    "HOLD_FOR_HUMAN_HANDLING",
    "FAST_TRACK_CANDIDATE",
    "STANDARD_REVIEW",
    "ENHANCED_REVIEW",
)


@dataclass(frozen=True)
class CalculationBundle:
    assessment: dict[str, Any]
    routing: dict[str, Any]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def validate_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    configured = dict(weights or CS_WEIGHTS)
    expected = set(CS_WEIGHTS)
    if set(configured) != expected:
        raise ValueError(f"Confidence weights must contain exactly: {', '.join(sorted(expected))}")
    if any(value < 0 or value > 1 for value in configured.values()):
        raise ValueError("Confidence weights must each be within [0, 1].")
    if abs(sum(configured.values()) - 1.0) > 1e-9:
        raise ValueError("Confidence weights must sum to 1.")
    return configured


def _mandatory_gates(application: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        ("consent", "Borrower consent recorded", bool(application.get("consent"))),
        ("identity", "Simulated identity check passed", bool(application.get("identity_verified"))),
        ("source_permission", "Financial source permission recorded", bool(application.get("source_permission"))),
        ("funding_reconciliation", "Checkout funding reconciled", bool(application.get("funding_reconciled"))),
    ]
    return [{"key": key, "label": label, "passed": passed, "mandatory": True} for key, label, passed in checks]


def financial_features(application: dict[str, Any]) -> dict[str, float | int]:
    history = [float(value) for value in application.get("monthly_income_vnd", [])]
    if not history:
        raise ValueError("At least one monthly income observation is required.")
    income_mean = mean(history)
    income_sd = pstdev(history) if len(history) > 1 else 0.0
    p25 = sorted(history)[max(0, int((len(history) - 1) * 0.25))]
    debt = float(application.get("existing_monthly_debt_vnd", 0))
    expenses = float(application.get("essential_monthly_expenses_vnd", 0))
    return {
        "mean_income_vnd": income_mean,
        "income_standard_deviation_vnd": income_sd,
        "income_cv": income_sd / income_mean if income_mean else 0.0,
        "income_p25_vnd": float(p25),
        "existing_monthly_debt_vnd": debt,
        "existing_dti_ratio": debt / income_mean if income_mean else 0.0,
        "income_residual_vnd": income_mean - debt - expenses,
        "history_coverage": min(len(history) / MAX_HISTORY_MONTHS, 1.0),
        "history_months": len(history),
    }


def confidence_score(application: dict[str, Any], weights: dict[str, float] | None = None) -> dict[str, Any]:
    configured_weights = validate_weights(weights)
    evidence = application.get("evidence", {})
    total = max(int(evidence.get("reconciliation_fields_total", 1)), 1)
    consistent = int(evidence.get("reconciliation_fields_consistent", 0))
    available_sources = max(int(evidence.get("available_sources", 1)), 1)
    verified_sources = int(evidence.get("verified_sources", 0))
    age_days = max(0.0, float(evidence.get("age_days", 0)))
    values = {
        "coverage": _clamp(float(financial_features(application)["history_coverage"])),
        "consistency": _clamp(consistent / total),
        "recency": exp(-age_days / RECENCY_DECAY_DAYS),
        "verification": _clamp(verified_sources / available_sources),
    }
    contributions = {key: values[key] * configured_weights[key] for key in configured_weights}
    score = _clamp(sum(contributions.values()))
    return {
        "score": score,
        "label": "Evidence quality index; not a probability",
        "subscores": values,
        "weights": configured_weights,
        "weighted_contributions": contributions,
        "inputs": {
            "income_history_months": len(application.get("monthly_income_vnd", [])),
            "maximum_history_months": MAX_HISTORY_MONTHS,
            "reconciliation_fields_consistent": consistent,
            "reconciliation_fields_total": total,
            "verified_sources": verified_sources,
            "available_sources": available_sources,
            "evidence_age_days": age_days,
            "recency_decay_days": RECENCY_DECAY_DAYS,
        },
    }


def affordability(application: dict[str, Any], features: dict[str, Any], max_dti: float = MAX_DTI_ASSUMPTION) -> dict[str, Any]:
    monthly_income = float(features["mean_income_vnd"])
    existing_debt = float(features["existing_monthly_debt_vnd"])
    expenses = float(application.get("essential_monthly_expenses_vnd", 0))
    stressed_capacity = max(0.0, monthly_income * max_dti - existing_debt)
    installment = float(application.get("proposed_installment_vnd", 0))
    repayment_buffer = stressed_capacity - installment
    result: dict[str, Any] = {
        "income_residual_vnd": float(features["income_residual_vnd"]),
        "stressed_payment_capacity_vnd": stressed_capacity,
        "repayment_buffer_vnd": repayment_buffer,
        "installment_eligible": installment > 0 and repayment_buffer >= 0 and float(features["income_residual_vnd"]) > 0,
        "proposed_installment_vnd": installment,
        "max_dti_assumption": max_dti,
        "essential_monthly_expenses_vnd": expenses,
        "calculation": "max(0, mean monthly income × illustrative maximum DTI − existing monthly debt)",
    }
    rate = application.get("annual_interest_rate")
    term = application.get("term_months")
    if rate is not None and term:
        monthly_rate = float(rate) / 12.0
        principal = float(application.get("loan_amount_vnd", 0))
        pmt = principal / term if monthly_rate == 0 else principal * monthly_rate / (1 - (1 + monthly_rate) ** (-int(term)))
        result["pmt_vnd"] = pmt
        result["pmt_calculation"] = "principal / term when rate is zero; otherwise standard amortizing-loan PMT"
    else:
        result["pmt_vnd"] = None
        result["pmt_calculation"] = "Not calculated: rate and term were not both supplied."
    return result


def demo_risk_score(application: dict[str, Any], features: dict[str, Any], confidence: dict[str, Any]) -> dict[str, Any]:
    """Return a replaceable logistic demonstration score, never an approval."""
    evidence_gap = 1.0 - float(confidence["score"])
    slopes = DEMO_RISK_SLOPES
    linear_terms = {
        "existing_dti_ratio": slopes["existing_dti_ratio"] * float(features["existing_dti_ratio"]),
        "income_cv": slopes["income_cv"] * float(features["income_cv"]),
        "evidence_gap": slopes["evidence_gap"] * evidence_gap,
    }
    # The brief supplies an expected DEMO-001 PD, but not the prototype
    # coefficients. This visibly anchored intercept preserves that expected
    # point while the slopes remain illustrative and replaceable.
    anchor_application = application.get("risk_anchor", DEMO_RISK_ANCHOR)
    anchor_linear = (
        slopes["existing_dti_ratio"] * float(anchor_application.get("existing_dti_ratio", features["existing_dti_ratio"]))
        + slopes["income_cv"] * float(anchor_application.get("income_cv", features["income_cv"]))
        + slopes["evidence_gap"] * float(anchor_application.get("evidence_gap", evidence_gap))
    )
    anchor_intercept = log(DEMO_ANCHOR_PD / (1.0 - DEMO_ANCHOR_PD)) - anchor_linear
    logit = anchor_intercept + sum(linear_terms.values())
    pd = 1.0 / (1.0 + exp(-logit))
    return {
        "score": pd,
        "label": DEMO_RISK_STATUS,
        "model_type": "Illustrative logistic regression formula",
        "calibration_status": "NOT_TRAINED_OR_CALIBRATED",
        "reference_parity": "UNVERIFIED_REFERENCE_FILES_MISSING",
        "formula": "sigmoid(intercept + 3.00 × existing DTI + 1.50 × income CV + 0.80 × evidence gap)",
        "intercept": anchor_intercept,
        "slopes": slopes,
        "linear_terms": linear_terms,
        "logit": logit,
        "source_note": "Synthetic demo slopes; anchor PD is the expected value supplied in the implementation brief.",
    }


def expected_loss(pd: float) -> dict[str, Any]:
    value = pd * LGD_ASSUMPTION * EAD_ASSUMPTION_VND
    return {
        "amount_vnd": value,
        "pd_demo": pd,
        "lgd_assumption": LGD_ASSUMPTION,
        "ead_assumption_vnd": EAD_ASSUMPTION_VND,
        "calculation": "PD demo × illustrative LGD assumption × illustrative EAD assumption",
    }


def route_application(
    gates: list[dict[str, Any]],
    confidence: dict[str, Any],
    risk: dict[str, Any],
    affordability_result: dict[str, Any],
    route_costs_vnd: dict[str, float] | None = None,
) -> dict[str, Any]:
    costs = dict(DEFAULT_ROUTE_COSTS_VND)
    if route_costs_vnd:
        unknown = set(route_costs_vnd) - set(ROUTE_ORDER)
        if unknown:
            raise ValueError(f"Unknown route cost(s): {', '.join(sorted(unknown))}")
        costs.update({key: float(value) for key, value in route_costs_vnd.items()})
    if any(value < 0 for value in costs.values()):
        raise ValueError("Route costs cannot be negative.")

    failed = [gate["label"] for gate in gates if gate["mandatory"] and not gate["passed"]]
    pd = float(risk["score"])
    cs = float(confidence["score"])
    affordability_ok = bool(affordability_result["installment_eligible"])
    if failed:
        eligible = ["HOLD_FOR_HUMAN_HANDLING"]
        explanations = ["Mandatory validation failed; automated assessment and route selection are blocked.", *failed]
    else:
        eligible = ["STANDARD_REVIEW", "ENHANCED_REVIEW"]
        explanations = []
        if cs >= FAST_TRACK_MIN_CONFIDENCE and pd <= FAST_TRACK_MAX_PD and affordability_ok:
            eligible.append("FAST_TRACK_CANDIDATE")
        if cs < ENHANCED_CONFIDENCE_BELOW or pd > ENHANCED_PD_ABOVE:
            eligible = ["ENHANCED_REVIEW"]
            explanations.append("Low evidence confidence or high demo-risk indicator requires enhanced human review.")
        elif not affordability_ok:
            explanations.append("Affordability gate failed; fast-track is ineligible regardless of demo PD.")
        else:
            explanations.append("Route is eligible for consideration under illustrative demo thresholds.")

    order_index = {route: index for index, route in enumerate(ROUTE_ORDER)}
    chosen = min(eligible, key=lambda route: (costs[route], order_index[route]))
    comparisons = [
        {"route": route, "eligible": route in eligible, "estimated_cost_vnd": costs[route],
         "selected": route == chosen, "reason": "Eligible; lowest illustrative cost" if route == chosen else
         ("Ineligible under policy gate" if route not in eligible else "Eligible, but higher cost than selected route")}
        for route in ROUTE_ORDER
    ]
    return {
        "eligible_routes": eligible,
        "recommended_route": chosen,
        "human_confirmation_required": True,
        "loan_approval_available": False,
        "policy_status": "ILLUSTRATIVE_NOT_BANK_VALIDATED",
        "objective": "Minimize estimated review cost across eligible routes after hard policy gates.",
        "estimated_route_costs_vnd": costs,
        "route_comparison": comparisons,
        "explanations": explanations,
    }


def calculate_application(application: dict[str, Any], route_costs_vnd: dict[str, float] | None = None,
                          max_dti: float = MAX_DTI_ASSUMPTION) -> CalculationBundle:
    gates = _mandatory_gates(application)
    failed = [gate for gate in gates if not gate["passed"]]
    if failed:
        hold = route_application(gates, {"score": 0.0}, {"score": 1.0}, {"installment_eligible": False}, route_costs_vnd)
        assessment = {
            "status": "BLOCKED_MANDATORY_CHECKS",
            "gates": gates,
            "scoring_performed": False,
            "features": None,
            "confidence": None,
            "risk": None,
            "affordability": None,
            "expected_loss": None,
            "notice": "Mandatory input validation failed; no automated score was calculated.",
        }
        return CalculationBundle(assessment, hold)

    features = financial_features(application)
    confidence = confidence_score(application)
    affordability_result = affordability(application, features, max_dti=max_dti)
    risk = demo_risk_score(application, features, confidence)
    loss = expected_loss(float(risk["score"]))
    routing = route_application(gates, confidence, risk, affordability_result, route_costs_vnd)
    assessment = {
        "status": "CALCULATED_DEMO_ONLY",
        "gates": gates,
        "scoring_performed": True,
        "features": features,
        "confidence": confidence,
        "risk": risk,
        "affordability": affordability_result,
        "expected_loss": loss,
        "human_decision_required": True,
    }
    return CalculationBundle(assessment, routing)
