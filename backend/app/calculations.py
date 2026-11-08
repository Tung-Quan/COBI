"""Versioned policy for the synthetic checkout workbench."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp, expm1, floor, isfinite, log1p
from statistics import mean, pstdev
from typing import Any


CS_WEIGHTS = {"coverage": 0.30, "consistency": 0.30, "recency": 0.20, "verification": 0.20}
RECENCY_DECAY_DAYS = 40.0
MAX_HISTORY_MONTHS = 12
MAX_DTI_ASSUMPTION = 0.35
RESIDUAL_BUFFER = 0.25
POLICY_VERSION = "cobi-checkout-policy-v2.0"
DEMO_MODEL_VERSION = "synthetic-logistic-v2.0"
FAST_TRACK_MIN_CONFIDENCE = 0.75
ENHANCED_CONFIDENCE_BELOW = 0.50
LGD_ASSUMPTION = 0.45
DEMO_INTERCEPT = -3.5
DEMO_RISK_SLOPES = {"existing_dti_ratio": 3.00, "income_cv": 1.50}
DEMO_RISK_STATUS = "DEMO_RISK_SCORE_NOT_CALIBRATED"

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
    configured = dict(CS_WEIGHTS if weights is None else weights)
    expected = set(CS_WEIGHTS)
    if set(configured) != expected:
        raise ValueError(f"Confidence weights must contain exactly: {', '.join(sorted(expected))}")
    if any(not isfinite(value) or not 0 <= value <= 1 for value in configured.values()):
        raise ValueError("Confidence weights must each be within [0, 1].")
    if abs(sum(configured.values()) - 1.0) > 1e-9:
        raise ValueError("Confidence weights must sum to 1.")
    return configured


def _evidence_as_of(application: dict[str, Any]) -> bool:
    evidence = application.get("evidence", {})
    dates = [evidence.get("feature_event_at"), evidence.get("feature_snapshot_at")]
    for source in evidence.get("sources", []):
        dates.extend([source.get("feature_event_at"), source.get("feature_snapshot_at")])
    dates = [value for value in dates if value is not None]
    if not dates:
        return True  # Legacy synthetic fixture, with unknown as-of provenance.
    try:
        decision = datetime.fromisoformat(application["submitted_at"])
        return decision.utcoffset() is not None and all(
            (event := datetime.fromisoformat(value)).utcoffset() is not None and event <= decision
            for value in dates
        )
    except (KeyError, ValueError, TypeError):
        return False


def _mandatory_gates(application: dict[str, Any]) -> list[dict[str, Any]]:
    purchase, principal = application["purchase_amount_vnd"], application["loan_amount_vnd"]
    own_funds = application.get("own_funds_vnd")
    funding_matches = 0 < principal <= purchase and (
        own_funds is None or abs(purchase - principal - own_funds) <= 1
    )
    checks = [
        ("consent", "Borrower consent active", application.get("consent") is True and not application.get("consent_revoked_at")),
        ("identity", "Simulated identity check passed", application.get("identity_verified") is True),
        ("source_permission", "Financial source permission recorded", application.get("source_permission") is True),
        ("funding_reconciliation", "Checkout funding reconciled", application.get("funding_reconciled") is True
         and funding_matches),
        ("evidence_integrity", "No reported material evidence failure", application.get("evidence", {}).get("critical_failure", False) is False),
        ("evidence_as_of", "Supplied feature dates are at or before decision", _evidence_as_of(application)),
    ]
    return [{"key": key, "label": label, "passed": passed, "mandatory": True} for key, label, passed in checks]


def financial_features(application: dict[str, Any]) -> dict[str, float | int]:
    history = [float(value) for value in application.get("monthly_income_vnd", [])]
    if not history:
        raise ValueError("At least one monthly income observation is required.")
    income_mean = mean(history)
    income_sd = pstdev(history) if len(history) > 1 else 0.0
    ordered = sorted(history)
    index = (len(ordered) - 1) * 0.25
    lower = floor(index)
    p25 = ordered[lower] + (index - lower) * (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower])
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
    total = int(evidence.get("reconciliation_fields_total", 0))
    consistent = int(evidence.get("reconciliation_fields_consistent", 0))
    available_sources = int(evidence.get("available_sources", 0))
    verified_sources = int(evidence.get("verified_sources", 0))
    age_days = max(0.0, float(evidence.get("age_days", 3650)))
    values = {
        "coverage": min(len(application["monthly_income_vnd"]) / MAX_HISTORY_MONTHS, 1.0),
        "consistency": _clamp(consistent / total) if total else 0.0,
        "recency": exp(-age_days / RECENCY_DECAY_DAYS),
        "verification": _clamp(verified_sources / available_sources) if available_sources else 0.0,
    }
    contributions = {key: values[key] * configured_weights[key] for key in configured_weights}
    score = _clamp(sum(contributions.values()))
    return {
        "score": score,
        "label": "Evidence quality index; not a probability",
        "status": "UNVALIDATED_EVIDENCE_SCORE",
        "completeness_gaps": {"history_months_missing": max(0, MAX_HISTORY_MONTHS - len(application["monthly_income_vnd"])),
                              "unreconciled_fields": total - consistent, "unverified_sources": available_sources - verified_sources},
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


def affordability(application: dict[str, Any], features: dict[str, Any], max_dti: float = MAX_DTI_ASSUMPTION,
                  buffer: float = RESIDUAL_BUFFER, installment_override: float | None = None) -> dict[str, Any]:
    monthly_income = float(features["mean_income_vnd"])
    existing_debt = float(features["existing_monthly_debt_vnd"])
    expenses = float(application.get("essential_monthly_expenses_vnd", 0))
    stress_income = float(features["income_p25_vnd"])
    dti_capacity = max(0.0, monthly_income * max_dti - existing_debt)
    residual_capacity = max(0.0, (stress_income - expenses - existing_debt) * (1 - buffer))
    capacity = min(dti_capacity, residual_capacity)
    stated = float(application["proposed_installment_vnd"])
    rate, term = application.get("annual_interest_rate"), application.get("term_months")
    principal = float(application["loan_amount_vnd"])
    pmt = payment(principal, float(rate), term) if rate is not None and term else None
    installment = installment_override if installment_override is not None else (pmt if pmt is not None else stated)
    repayment_buffer = capacity - installment
    return {
        "income_residual_vnd": float(features["income_residual_vnd"]),
        "dti_capacity_vnd": dti_capacity, "residual_capacity_vnd": residual_capacity,
        "stress_income_vnd": stress_income, "residual_buffer_assumption": buffer,
        "stressed_payment_capacity_vnd": capacity,
        "repayment_buffer_vnd": repayment_buffer,
        "installment_eligible": installment > 0 and repayment_buffer >= 0,
        "proposed_installment_vnd": installment,
        "stated_installment_vnd": stated,
        "stated_installment_differs_from_pmt": pmt is not None and abs(stated - pmt) > 1,
        "installment_basis": "WHAT_IF_OVERRIDE" if installment_override is not None else ("CONTRACT_PMT" if pmt is not None else "STATED_SYNTHETIC_INSTALLMENT"),
        "max_dti_assumption": max_dti,
        "essential_monthly_expenses_vnd": expenses,
        "calculation": "min(max(0, mean income × DTI cap − debt), max(0, (P25 income − essentials − debt) × (1 − buffer)))",
        "pmt_vnd": pmt,
        "pmt_calculation": "Monthly amortization at nominal annual rate ÷ 12, excluding fees and insurance",
    }


def payment(principal: float, annual_rate: float, term: int) -> float:
    monthly_rate = annual_rate / 12
    return principal / term if monthly_rate == 0 else principal * monthly_rate / -expm1(-term * log1p(monthly_rate))


def demo_risk_score(features: dict[str, Any]) -> dict[str, Any]:
    linear_terms = {name: slope * features[name] for name, slope in DEMO_RISK_SLOPES.items()}
    logit = DEMO_INTERCEPT + sum(linear_terms.values())
    pd = 1.0 / (1.0 + exp(-logit))
    return {
        "score": pd,
        "label": DEMO_RISK_STATUS,
        "model_type": "Illustrative logistic score",
        "calibration_status": "NOT_TRAINED_OR_CALIBRATED",
        "reference_parity": "COBI_V2_ILLUSTRATIVE_ASSUMPTIONS",
        "formula": "sigmoid(−3.5 + 3.00 × existing DTI + 1.50 × income CV)",
        "intercept": DEMO_INTERCEPT,
        "slopes": DEMO_RISK_SLOPES,
        "linear_terms": linear_terms,
        "logit": logit,
        "source_note": "Illustrative coefficients. The score has no empirically established outcome or horizon.",
    }


def expected_loss(pd: float, principal: float) -> dict[str, Any]:
    return {
        "status": "SCENARIO_EL_USING_DEMO_SCORE",
        "actual_expected_loss_status": "EL_NOT_ESTIMABLE",
        "amount_vnd": pd * LGD_ASSUMPTION * principal,
        "pd_demo": pd,
        "lgd_assumption": LGD_ASSUMPTION,
        "ead_assumption_vnd": principal,
        "calculation": "Synthetic score × assumed LGD × principal at origination",
        "sensitivity": [
            {"lgd": lgd, "ead_vnd": principal * fraction, "amount_vnd": pd * lgd * principal * fraction}
            for lgd in (0.25, 0.45, 0.65) for fraction in (0.25, 0.50, 1.00)
        ],
    }


def route_application(
    gates: list[dict[str, Any]],
    confidence: dict[str, Any] | None,
    affordability_result: dict[str, Any] | None,
    route_costs_vnd: dict[str, float] | None = None,
) -> dict[str, Any]:
    costs = dict(DEFAULT_ROUTE_COSTS_VND)
    if route_costs_vnd:
        unknown = set(route_costs_vnd) - set(ROUTE_ORDER)
        if unknown:
            raise ValueError(f"Unknown route cost(s): {', '.join(sorted(unknown))}")
        costs.update({key: float(value) for key, value in route_costs_vnd.items()})
    if any(not isfinite(value) or value < 0 for value in costs.values()):
        raise ValueError("Route costs must be finite and non-negative.")

    failed = [gate["label"] for gate in gates if gate["mandatory"] and not gate["passed"]]
    if failed:
        eligible = ["HOLD_FOR_HUMAN_HANDLING"]
        explanations = ["Mandatory validation failed; automated assessment and route selection are blocked.", *failed]
    else:
        assert confidence is not None and affordability_result is not None
        cs = confidence["score"]
        affordability_ok = affordability_result["installment_eligible"]
        eligible = ["STANDARD_REVIEW", "ENHANCED_REVIEW"]
        explanations = []
        terms_match = not affordability_result["stated_installment_differs_from_pmt"]
        if cs >= FAST_TRACK_MIN_CONFIDENCE and affordability_ok and terms_match:
            eligible.append("FAST_TRACK_CANDIDATE")
        if cs < ENHANCED_CONFIDENCE_BELOW:
            eligible = ["ENHANCED_REVIEW"]
            explanations.append("Low evidence quality requires enhanced human review.")
        elif not affordability_ok:
            explanations.append("Affordability failed. Fast-track is ineligible.")
        elif not terms_match:
            explanations.append("Stated payment differs from contract PMT. Fast-track is ineligible.")
        else:
            explanations.append("Route is eligible for consideration under illustrative demo thresholds.")

    order_index = {route: index for index, route in enumerate(ROUTE_ORDER)}
    chosen = min(eligible, key=lambda route: (costs[route], order_index[route]))
    comparisons = [
        {"route": route, "eligible": route in eligible, "estimated_cost_vnd": costs[route],
         "selected": route == chosen, "reason": "Eligible; lowest illustrative cost" if route == chosen else
         ("Ineligible under policy gate" if route not in eligible else "Eligible under cost and tie-break comparison")}
        for route in ROUTE_ORDER
    ]
    return {
        "eligible_routes": eligible,
        "recommended_route": chosen,
        "human_confirmation_required": True,
        "loan_approval_available": False,
        "policy_status": "ILLUSTRATIVE_NOT_BANK_VALIDATED",
        "policy_version": POLICY_VERSION,
        "comparison_status": "SIMULATED_ROUTE_COMPARISON",
        "objective": "Minimize estimated review cost across eligible routes after hard policy gates.",
        "estimated_route_costs_vnd": costs,
        "route_comparison": comparisons,
        "explanations": explanations,
    }


def calculate_application(application: dict[str, Any], route_costs_vnd: dict[str, float] | None = None,
                          max_dti: float = MAX_DTI_ASSUMPTION, *, buffer: float = RESIDUAL_BUFFER,
                          installment_override: float | None = None, model_requested: bool = False) -> CalculationBundle:
    gates = _mandatory_gates(application)
    failed = [gate for gate in gates if not gate["passed"]]
    provenance = {
        "policy_version": POLICY_VERSION, "fixture_version": application.get("fixture_version", "legacy-or-submitted"),
        "checkout_pd": None, "pd_status": "PD_UNAVAILABLE_SCHEMA_MISMATCH" if model_requested else "BANK_EXTERNAL_VALIDATION_BLOCKED",
        "model": {"version": DEMO_MODEL_VERSION if not failed else None, "scope": "synthetic checkout scenario"},
    }
    if failed:
        hold = route_application(gates, None, None, route_costs_vnd)
        assessment = {
            **provenance,
            "risk_source": "UNAVAILABLE",
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
    affordability_result = affordability(application, features, max_dti, buffer, installment_override)
    risk = demo_risk_score(features)
    loss = expected_loss(float(risk["score"]), float(application["loan_amount_vnd"]))
    routing = route_application(gates, confidence, affordability_result, route_costs_vnd)
    assessment = {
        **provenance,
        "risk_source": "SYNTHETIC_HEURISTIC",
        "status": "CALCULATED_DEMO_ONLY",
        "gates": gates,
        "scoring_performed": True,
        "features": features,
        "feature_method": {"percentile": "linear (Hyndman-Fan type 7)", "income_sd": "population", "unit": "VND/month"},
        "evidence_trace": {"source_class": "synthetic", "extraction_confidence": application["evidence"].get("extraction_confidence"),
                           "verification": "reported synthetic verification flags",
                           "as_of_status": "SUPPLIED_DATES_CHECKED" if any(
                               source.get(key) for source in [application["evidence"], *application["evidence"].get("sources", [])]
                               for key in ("feature_event_at", "feature_snapshot_at")
                           ) else "TIMESTAMPS_NOT_SUPPLIED"},
        "confidence": confidence,
        "risk": risk,
        "affordability": affordability_result,
        "expected_loss": loss,
        "human_decision_required": True,
    }
    return CalculationBundle(assessment, routing)
