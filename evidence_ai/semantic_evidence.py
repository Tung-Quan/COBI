"""Observable semantic normalization and conservative comparison rules."""
from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np

COMPARABILITY = ("COMPARABLE", "NOT_COMPARABLE", "UNKNOWN")
FIELD_THRESHOLDS = {"income": 500_000.0, "debt": 250_000.0, "purchase": 500_000.0}
SOURCE_TYPES = ("statement", "payroll", "merchant")
FIELD_TYPES = ("income", "debt", "purchase")
MEANINGS = ("salary", "recurring_debt", "purchase_amount", "UNKNOWN")
ORIGINAL_UNITS = ("VND", "THOUSAND_VND", "MILLION_VND", "UNKNOWN")
UNIT_TO_VND = {"VND": 1.0, "THOUSAND_VND": 1_000.0, "MILLION_VND": 1_000_000.0}
BASES = ("GROSS", "NET", "UNSPECIFIED", "UNKNOWN")
DIRECTIONS = ("INFLOW", "OUTFLOW", "NEUTRAL", "UNKNOWN")
CORRECTIONS = ("NONE", "ORIGINAL", "CORRECTED", "SUPERSEDED", "UNKNOWN")
VERIFICATION = ("VERIFIED", "UNVERIFIED", "UNKNOWN")
MISSINGNESS = ("NONE", "REQUIRED_VALUE_MISSING", "NOT_APPLICABLE", "SOURCE_UNAVAILABLE", "UNPARSED")


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def validate_record(record: dict[str, Any]) -> None:
    required = {
        "record_id", "subject_ref", "account_ref", "field_type", "financial_meaning",
        "effective_period", "source_type", "provenance", "original_value", "original_unit",
        "normalized_value", "normalized_unit", "gross_net_basis", "transaction_direction",
        "correction_status", "correction_of", "verification_status", "missingness",
        "uncertainty", "asserted_as_current", "observed_at", "age_days", "ocr_quality", "text",
    }
    if set(record) != required:
        raise ValueError(f"Semantic record keys differ: missing={required-set(record)} extra={set(record)-required}")
    if record["field_type"] not in FIELD_TYPES or record["source_type"] not in SOURCE_TYPES:
        raise ValueError("Unsupported field/source type; do not silently coerce")
    if record["financial_meaning"] not in MEANINGS:
        raise ValueError("Unknown financial meaning; encode UNKNOWN explicitly")
    period = record["effective_period"]
    if set(period) != {"start", "end"}:
        raise ValueError("effective_period must contain start and end")
    start, end = _date(period["start"]), _date(period["end"])
    if (period["start"] and start is None) or (period["end"] and end is None) or (start and end and end < start):
        raise ValueError("Invalid effective period")
    if record["normalized_unit"] not in {"VND", "UNKNOWN"} or record["original_unit"] not in ORIGINAL_UNITS:
        raise ValueError("Only normalized VND or explicit UNKNOWN is supported")
    if record["gross_net_basis"] not in BASES or record["transaction_direction"] not in DIRECTIONS:
        raise ValueError("Unknown semantic category")
    if record["correction_status"] not in CORRECTIONS or record["verification_status"] not in VERIFICATION:
        raise ValueError("Unknown provenance state")
    if record["normalized_value"] is not None and record["normalized_unit"] != "VND":
        raise ValueError("A normalized amount requires normalized VND units")
    if record["missingness"] not in MISSINGNESS:
        raise ValueError("Unknown missingness state")
    uncertainty = record["uncertainty"]
    if not isinstance(uncertainty, (int, float)) or not 0.0 <= float(uncertainty) <= 1.0:
        raise ValueError("uncertainty must be in [0, 1]")
    if not isinstance(record["age_days"], (int, float)) or float(record["age_days"]) < 0:
        raise ValueError("age_days must be nonnegative")
    if record["asserted_as_current"] is not None and not isinstance(record["asserted_as_current"], bool):
        raise ValueError("asserted_as_current must be true, false, or unknown")
    if record["verification_status"] == "UNKNOWN" or record["financial_meaning"] == "UNKNOWN":
        return
    if record["original_unit"] in UNIT_TO_VND and record["original_value"] is not None and record["normalized_value"] is not None:
        expected = float(record["original_value"]) * UNIT_TO_VND[record["original_unit"]]
        if abs(float(record["normalized_value"]) - expected) > max(1.0, abs(expected) * 1e-9):
            raise ValueError("Normalized amount does not match original amount and unit")


def compare_periods(left: dict, right: dict) -> tuple[str, str]:
    a0, a1 = _date(left.get("start")), _date(left.get("end"))
    b0, b1 = _date(right.get("start")), _date(right.get("end"))
    if None in (a0, a1, b0, b1):
        return "UNKNOWN", "MISSING_EFFECTIVE_PERIOD"
    if a1 < b0 or b1 < a0:
        return "NOT_COMPARABLE", "NON_OVERLAPPING_EFFECTIVE_PERIODS"
    if a0 == b0 and a1 == b1:
        return "COMPARABLE", "SAME_EFFECTIVE_PERIOD"
    return "UNKNOWN", "PARTIALLY_OVERLAPPING_PERIODS"


def source_comparability(left: dict, right: dict) -> dict:
    """Return three-valued comparability; source identity alone is not a veto."""
    for record in (left, right):
        try:
            validate_record(record)
        except (ValueError, TypeError, KeyError):
            return {"status": "UNKNOWN", "reason": "INVALID_OR_INCOMPLETE_RECORD"}
    if not left["subject_ref"] or not right["subject_ref"] or not left["account_ref"] or not right["account_ref"]:
        return {"status": "UNKNOWN", "reason": "MISSING_SUBJECT_OR_ACCOUNT_REFERENCE"}
    if left["subject_ref"] != right["subject_ref"]:
        return {"status": "NOT_COMPARABLE", "reason": "DIFFERENT_SUBJECT"}
    if left["account_ref"] != right["account_ref"]:
        return {"status": "NOT_COMPARABLE", "reason": "DIFFERENT_ACCOUNT"}
    if left["field_type"] != right["field_type"]:
        return {"status": "NOT_COMPARABLE", "reason": "DIFFERENT_FIELD_TYPE"}
    if "UNKNOWN" in {left["financial_meaning"], right["financial_meaning"]}:
        return {"status": "UNKNOWN", "reason": "FINANCIAL_MEANING_UNKNOWN"}
    if left["financial_meaning"] != right["financial_meaning"]:
        return {"status": "NOT_COMPARABLE", "reason": "DIFFERENT_FINANCIAL_MEANING"}
    if left["gross_net_basis"] in {"UNKNOWN", "UNSPECIFIED"} or right["gross_net_basis"] in {"UNKNOWN", "UNSPECIFIED"}:
        return {"status": "UNKNOWN", "reason": "BASIS_NOT_SPECIFIED"}
    if left["gross_net_basis"] != right["gross_net_basis"]:
        return {"status": "NOT_COMPARABLE", "reason": "GROSS_NET_BASIS_MISMATCH"}
    if left["transaction_direction"] == "UNKNOWN" or right["transaction_direction"] == "UNKNOWN":
        return {"status": "UNKNOWN", "reason": "TRANSACTION_DIRECTION_UNKNOWN"}
    if left["transaction_direction"] != right["transaction_direction"]:
        return {"status": "NOT_COMPARABLE", "reason": "TRANSACTION_DIRECTION_MISMATCH"}
    superseded_link = (
        left["correction_status"] == "SUPERSEDED" and left["correction_of"] == right["record_id"]
    ) or (
        right["correction_status"] == "SUPERSEDED" and right["correction_of"] == left["record_id"]
    ) or (
        left["correction_status"] == "CORRECTED" and left["correction_of"] == right["record_id"]
    ) or (
        right["correction_status"] == "CORRECTED" and right["correction_of"] == left["record_id"]
    )
    if superseded_link:
        return {"status": "NOT_COMPARABLE", "reason": "CORRECTION_LINEAGE_SUPERSEDES_PRIOR_VERSION"}
    if "UNKNOWN" in {left["correction_status"], right["correction_status"]}:
        return {"status": "UNKNOWN", "reason": "CORRECTION_STATE_UNKNOWN"}
    if left["normalized_value"] is None or right["normalized_value"] is None:
        return {"status": "UNKNOWN", "reason": "MISSING_NORMALIZED_AMOUNT"}
    if left["normalized_unit"] != "VND" or right["normalized_unit"] != "VND":
        return {"status": "UNKNOWN", "reason": "UNNORMALIZED_CURRENCY"}
    if left["original_unit"] == "UNKNOWN" or right["original_unit"] == "UNKNOWN":
        return {"status": "UNKNOWN", "reason": "ORIGINAL_UNIT_UNKNOWN"}
    if float(left["uncertainty"]) >= .75 or float(right["uncertainty"]) >= .75:
        return {"status": "UNKNOWN", "reason": "EXTRACTION_UNCERTAINTY_TOO_HIGH"}
    if "UNKNOWN" in {left["verification_status"], right["verification_status"]}:
        return {"status": "UNKNOWN", "reason": "VERIFICATION_STATUS_UNKNOWN"}
    period_status, reason = compare_periods(left["effective_period"], right["effective_period"])
    return {"status": period_status, "reason": reason}


def time_validity(record: dict, request: dict) -> dict:
    """Old age is not itself an error; judge applicability against the requested period."""
    period_status, reason = compare_periods(record.get("effective_period", {}), request.get("period", {}))
    asserted_current = record.get("asserted_as_current")
    if asserted_current is None or period_status == "UNKNOWN":
        return {"state": "UNKNOWN", "valid": None, "critical": None, "reason": reason}
    if period_status == "COMPARABLE":
        return {"state": "CURRENT_APPLICABLE" if asserted_current else "HISTORICAL_APPLICABLE",
                "valid": True, "critical": False, "reason": "REQUESTED_PERIOD_OVERLAPS_EVIDENCE"}
    if period_status == "NOT_COMPARABLE" and asserted_current:
        age = float(record.get("age_days") or 0)
        critical = age >= 180
        return {"state": "STALE_AS_CURRENT", "valid": False, "critical": critical,
                "reason": "EFFECTIVE_PERIOD_MISMATCH_ASSERTED_CURRENT"}
    if period_status == "NOT_COMPARABLE" and not asserted_current:
        return {"state": "HISTORICAL_NOT_APPLICABLE_TO_REQUEST", "valid": None, "critical": None,
                "reason": "HISTORICAL_RECORD_DOES_NOT_MATCH_REQUESTED_PERIOD"}
    return {"state": "UNKNOWN", "valid": None, "critical": None, "reason": reason}


def semantic_validation(case: dict) -> dict:
    records = case["records"]
    doc_results = {record["record_id"]: {"score": 0.0, "alerts": [], "time_validity": time_validity(record, case["request"])}
                   for record in records}
    comparisons = []
    for i, left in enumerate(records):
        for right in records[i + 1:]:
            result = source_comparability(left, right)
            entry = {"left_record_id": left["record_id"], "right_record_id": right["record_id"], **result}
            comparisons.append(entry)
            if result["status"] != "COMPARABLE":
                continue
            field = left["field_type"]
            threshold = FIELD_THRESHOLDS[field]
            delta = abs(float(left["normalized_value"]) - float(right["normalized_value"]))
            if delta >= threshold:
                critical = delta >= 2 * threshold
                alert = {"reason": "COMPARABLE_VALUE_CONFLICT", "severity": "CRITICAL" if critical else "MATERIAL",
                         "peer_record_id": right["record_id"], "absolute_difference_vnd": delta,
                         "field_threshold_vnd": threshold, "comparability": result["status"]}
                peer_alert = alert | {"peer_record_id": left["record_id"]}
                for record_id, explanation in ((left["record_id"], alert), (right["record_id"], peer_alert)):
                    doc_results[record_id]["score"] = max(doc_results[record_id]["score"], 1.0 if critical else .75)
                    doc_results[record_id]["alerts"].append(explanation)
    for record in records:
        result = doc_results[record["record_id"]]
        validity = result["time_validity"]
        if validity["state"] == "STALE_AS_CURRENT":
            result["score"] = max(result["score"], 1.0 if validity["critical"] else .75)
            result["alerts"].append({"reason": validity["reason"], "severity": "CRITICAL" if validity["critical"] else "MATERIAL",
                                     "state": validity["state"], "effective_period": record["effective_period"],
                                     "requested_period": case["request"]["period"], "age_days": record["age_days"]})
        if record["missingness"] == "REQUIRED_VALUE_MISSING":
            result["score"] = max(result["score"], .75)
            result["alerts"].append({"reason": "REQUIRED_FINANCIAL_VALUE_MISSING", "severity": "MATERIAL"})
    return {"documents": doc_results, "comparisons": comparisons}


FEATURE_NAMES = (
    "log_normalized_amount", "amount_missing", "uncertainty", "ocr_quality", "age_days_log",
    "field_income", "field_debt", "field_purchase", "meaning_salary", "meaning_recurring_debt", "meaning_purchase_amount", "meaning_unknown",
    "basis_gross", "basis_net", "basis_unspecified", "direction_inflow", "direction_outflow", "direction_neutral",
    "source_statement", "source_payroll", "source_merchant", "verified", "unverified",
    "correction_original", "correction_corrected", "correction_superseded", "asserted_current",
    "effective_period_known", "period_overlaps_request", "stale_as_current", "historical_applicable",
    "days_from_requested_start", "effective_period_days", "n_comparable_peers", "n_noncomparable_peers",
    "n_unknown_peers", "max_comparable_log_gap", "has_comparable_conflict", "has_correction_lineage",
)


def _onehot(value: str, choices: tuple[str, ...]) -> list[float]:
    return [float(value == choice) for choice in choices]


def feature_matrix(case: dict) -> tuple[np.ndarray, list[dict]]:
    """Encode only observable records and request metadata; never reads gold/canonical files."""
    records = case["records"]
    validation = semantic_validation(case)
    output, explanations = [], []
    req_start = _date(case["request"]["period"].get("start"))
    for record in records:
        statuses = [source_comparability(record, peer) for peer in records if peer["record_id"] != record["record_id"]]
        comparable = [peer for peer in records if peer["record_id"] != record["record_id"]
                      and source_comparability(record, peer)["status"] == "COMPARABLE"]
        gaps = [abs(np.log1p(max(0.0, float(record["normalized_value"]))) - np.log1p(max(0.0, float(peer["normalized_value"]))))
                for peer in comparable if record["normalized_value"] is not None and peer["normalized_value"] is not None]
        validity = time_validity(record, case["request"])
        period_start = _date(record["effective_period"].get("start"))
        period_end = _date(record["effective_period"].get("end"))
        amount = record["normalized_value"]
        vector = [
            float(np.log1p(max(0.0, float(amount)))) if amount is not None else 0.0,
            float(amount is None or record["missingness"] == "REQUIRED_VALUE_MISSING"),
            float(record["uncertainty"]), float(record["ocr_quality"]), float(np.log1p(max(0, record["age_days"]))),
            *_onehot(record["field_type"], FIELD_TYPES), *_onehot(record["financial_meaning"], MEANINGS),
            *_onehot(record["gross_net_basis"], ("GROSS", "NET", "UNSPECIFIED")),
            *_onehot(record["transaction_direction"], ("INFLOW", "OUTFLOW", "NEUTRAL")),
            *_onehot(record["source_type"], SOURCE_TYPES),
            float(record["verification_status"] == "VERIFIED"), float(record["verification_status"] == "UNVERIFIED"),
            *_onehot(record["correction_status"], ("ORIGINAL", "CORRECTED", "SUPERSEDED")),
            float(bool(record["asserted_as_current"])), float(period_start is not None and period_end is not None),
            float(validity["state"] == "CURRENT_APPLICABLE"), float(validity["state"] == "STALE_AS_CURRENT"),
            float(validity["state"] == "HISTORICAL_APPLICABLE"),
            float((period_start - req_start).days) / 365.25 if period_start and req_start else 0.0,
            float((period_end - period_start).days) / 365.25 if period_start and period_end else 0.0,
            float(sum(item["status"] == "COMPARABLE" for item in statuses)),
            float(sum(item["status"] == "NOT_COMPARABLE" for item in statuses)),
            float(sum(item["status"] == "UNKNOWN" for item in statuses)),
            float(max(gaps, default=0.0)),
            float(any(alert["reason"] == "COMPARABLE_VALUE_CONFLICT" for alert in validation["documents"][record["record_id"]]["alerts"])),
            float(bool(record["correction_of"]) or record["correction_status"] in {"CORRECTED", "SUPERSEDED"}),
        ]
        if len(vector) != len(FEATURE_NAMES):
            raise AssertionError(f"Feature contract mismatch {len(vector)} != {len(FEATURE_NAMES)}")
        output.append(vector)
        explanations.append(validation["documents"][record["record_id"]])
    return np.asarray(output, dtype=np.float32), explanations


def case_feature_array(cases: list[dict], capacity: int = 6) -> tuple[np.ndarray, np.ndarray, list[list[dict]]]:
    x = np.zeros((len(cases), capacity, len(FEATURE_NAMES)), dtype=np.float32)
    mask = np.zeros((len(cases), capacity), dtype=bool)
    explanation_rows = []
    for i, case in enumerate(cases):
        matrix, details = feature_matrix(case)
        if len(matrix) > capacity:
            raise ValueError(f"Case {case['case_id']} exceeds frozen capacity")
        x[i, :len(matrix)] = matrix
        mask[i, :len(matrix)] = True
        explanation_rows.append(details)
    return x, mask, explanation_rows
