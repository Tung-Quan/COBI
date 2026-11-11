"""Denominator helpers for the V4.2 research-only evaluation contract."""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping


def pair_confusion(actual: Iterable[str], predicted: Iterable[str], labels: tuple[str, ...] = ("COMPARABLE", "NOT_COMPARABLE", "UNKNOWN")) -> dict[str, dict[str, int]]:
    actual_rows, predicted_rows = list(actual), list(predicted)
    if len(actual_rows) != len(predicted_rows):
        raise ValueError("actual and predicted pair counts differ")
    if any(value not in labels for value in actual_rows + predicted_rows):
        raise ValueError("pair labels must be in the registered label set")
    matrix = {truth: {guess: 0 for guess in labels} for truth in labels}
    for truth, guess in zip(actual_rows, predicted_rows):
        matrix[truth][guess] += 1
    return matrix


def document_attribution_denominators(rows: Iterable[Mapping[str, str]]) -> dict[str, int]:
    """Only independent verified-correct/incorrect gold enters attribution metrics."""
    values = list(rows)
    eligible = [row for row in values if row.get("gold_status") in {"VERIFIED_CORRECT", "VERIFIED_INCORRECT"}]
    actual_incorrect = sum(row["gold_status"] == "VERIFIED_INCORRECT" for row in eligible)
    return {
        "all_rows": len(values),
        "eligible_rows": len(eligible),
        "excluded_unresolved_or_unverified": len(values) - len(eligible),
        "incorrect_document_denominator": actual_incorrect,
    }


def case_denominators(rows: Iterable[Mapping[str, str]]) -> dict[str, int | float | None]:
    """Return disjoint case-level denominators; REQUEST_MORE_EVIDENCE consumes effort."""
    values = list(rows)
    total = len(values)
    critical = [row for row in values if row.get("gold_critical") == "CRITICAL"]
    cleared = [row for row in values if row.get("predicted_action") == "NO_FLAG"]
    missed_all = sum(row.get("gold_critical") == "CRITICAL" and row.get("predicted_action") == "NO_FLAG" for row in values)
    review = sum(row.get("predicted_action") == "HUMAN_REVIEW" for row in values)
    request = sum(row.get("predicted_action") == "REQUEST_MORE_EVIDENCE" for row in values)
    action = review + request
    return {
        "all_cases": total,
        "critical_miss_numerator": missed_all,
        "critical_case_denominator": len(critical),
        "cleared_case_denominator": len(cleared),
        "review_numerator": review,
        "request_numerator": request,
        "action_workload_numerator": action,
        "critical_miss_rate_all_critical": missed_all / len(critical) if critical else None,
        "critical_miss_rate_among_cleared": missed_all / len(cleared) if cleared else None,
        "action_workload_rate": action / total if total else None,
    }
