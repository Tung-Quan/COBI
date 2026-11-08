import ast
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from evidence_ai.features import NAMES, build_arrays
from evidence_ai.v4_business import _cost
from evidence_ai.v4_experiments import bootstrap, metrics
from evidence_ai.v4_generator import SCENARIOS, generate, validate_observed_schema


def test_generator_b_is_independently_implemented_and_gold_is_separate():
    source_path = Path(__file__).parents[1] / "v4_generator.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(name in {"evidence_ai.synthetic", "evidence_ai.shift"} for name in imports)
    assert not any(alias.name in {"evidence_ai.synthetic", "evidence_ai.shift"}
                   for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)

    cases, labels, canonical = generate()
    assert len(cases) == 1920
    assert len({case["customer_group"] for case in cases}) == 960
    assert {row["scenario"] for row in canonical} == set(SCENARIOS)
    assert validate_observed_schema(cases)["incompatible_documents"] == 0
    assert set(cases[0]).isdisjoint({"labels", "canonical_profile", "generation_event"})
    assert set(cases[0]["documents"][0]).isdisjoint({"material_evidence_error", "critical_evidence_error", "generation_event"})
    assert len(labels) == len(canonical) == len(cases)
    assert set(NAMES).isdisjoint({"case_key", "customer_group", "document_key", "scenario", "generation_event"})
    forbidden = ("programmatic_gold", "material_evidence_error", "critical_evidence_error",
                 "generation_event", "stale record incorrectly presented as current",
                 "duplicate transaction reference reconciled", "valid net-gross")
    assert all(not any(word in doc["text"].casefold() for word in forbidden)
               for case in cases for doc in case["documents"])

    # B2's duplicate is represented by repeated observed transaction rows, not a gold-label phrase.
    b2_duplicates = [(doc, target) for case, label in zip(cases, labels, strict=True)
                     if case["case_key"].startswith("B2-")
                     for doc, target in zip(case["documents"], label["documents"], strict=True)
                     if target["generation_event"] == "duplicate_or_overlap_inflation"]
    assert b2_duplicates
    repeated_reference = [doc for doc, _ in b2_duplicates
                          if any(count > 1 for count in Counter(re.findall(r"TX-[^:;|]+-B:", doc["text"])).values())]
    assert repeated_reference


def test_v4_feature_encoder_builds_only_frozen_schema_features():
    cases, labels, _ = generate()
    data = build_arrays(cases[:8], labels)
    assert data["x"].shape == (8, 6, 32)
    assert data["mask"].shape == (8, 6)
    assert data["y"].shape == (8, 6)
    assert len(NAMES) == 32


def test_threshold_application_and_case_workload_denominators():
    data = {
        "mask": np.array([[True, True], [True, False]]),
        "y": np.array([[1, 0], [0, 0]]),
        "critical": np.array([[True, False], [True, False]]),
    }
    p = np.array([[.9, .1], [.2, 0.]])
    result = metrics(data, p, .5)
    assert result["cases"] == 2
    assert result["documents"] == 3
    assert result["critical_errors"] == 2
    assert result["critical_false_negatives"] == 1
    assert result["critical_recall"] == .5
    assert result["flagged_cases"] == 1
    assert result["review_workload"] == .5
    assert result["flagged_cases_per_100"] == 50


def test_bootstrap_rejects_customer_groups_split_across_scenarios():
    data = {"mask": np.ones((4, 1), dtype=bool), "y": np.array([[0], [1], [0], [1]]),
            "critical": np.array([[0], [1], [0], [1]], dtype=bool)}
    probability = np.array([[.1], [.9], [.1], [.9]])
    with pytest.raises(ValueError, match="customer group spans"):
        bootstrap(data, {"M": probability}, {"M": .5}, ["a", "a", "b", "b"],
                  draws=1, seed=11, strata=["B1", "B2", "B1", "B2"])


def test_cost_formula_uses_distinct_case_and_document_units():
    result = _cost(cases=5, workload=.5, critical_fn_per_case=.2, volume=100,
                   review_cost=10, missed_cost=50, inference_per_case=1, fixed=20)
    assert result["flagged_cases_expected"] == 50
    assert result["missed_critical_documents_expected"] == 20
    assert result["review_cost_vnd"] == 500
    assert result["missed_error_cost_vnd"] == 1000
    assert result["total_cost_vnd"] == 1620
