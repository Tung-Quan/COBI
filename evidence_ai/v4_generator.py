"""Independent event-ledger synthetic challenge for COBI Evidence AI V4.

This generator deliberately does not import or call the V3 synthetic generator.
It creates canonical document facts, visible observations, and programmatic gold
labels as separate payloads. It does not train models or choose thresholds.
"""
from __future__ import annotations

from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from ml.contracts import ROOT, canonical, sha, write_json

EVIDENCE_OUT = ROOT / "reports/evidence-v4"
PROTOCOL = EVIDENCE_OUT / "experiment_protocol.json"
AMENDMENT = EVIDENCE_OUT / "EXPERIMENT_PROTOCOL_AMENDMENT_1.json"
OUT = EVIDENCE_OUT / "data/generator-b-confirmatory-v1"
FIELDS = ("income", "debt", "purchase")
SOURCES = ("statement", "payroll", "merchant")
SCENARIOS = ("B1", "B2", "B3", "B4", "B5", "B6")
FIELD_THRESHOLDS = {"income": 500_000, "debt": 250_000, "purchase": 500_000}
SOURCE_PAIRS = (("statement", "payroll"), ("statement", "merchant"), ("payroll", "merchant"))


def _integer(rng: np.random.Generator, low: int, high: int) -> int:
    return int(rng.integers(low, high + 1))


def _amount(value: int | None, locale: str) -> str:
    if value is None:
        return "MISSING"
    value_text = f"{value:,}"
    if locale == "vi_vn":
        value_text = value_text.replace(",", ".")
    elif locale == "space_grouped":
        value_text = value_text.replace(",", " ")
    return f"{value_text} VND"


def _field_event(rng: np.random.Generator, scenario: str, expected: dict[str, int],
                 observed: dict[str, int | None]) -> tuple[str | None, str]:
    """Apply one scenario-specific event; return affected field and event label."""
    event_rates = {"B1": .12, "B2": .15, "B3": .12, "B5": .08, "B6": .12}
    if scenario not in event_rates or rng.random() >= event_rates[scenario]:
        return None, "none"

    field = FIELDS[int(rng.integers(0, len(FIELDS)))]
    value = expected[field]
    threshold = FIELD_THRESHOLDS[field]
    if scenario in {"B1", "B5"}:
        if rng.random() < .25:
            observed[field] = None
            return field, "unexplained_omission"
        delta = int(round(threshold * float(rng.uniform(1.5, 3.0))))
        sign = -1 if rng.random() < .5 else 1
        observed[field] = max(0, value + sign * delta)
        return field, "unexplained_amount_discrepancy"
    if scenario == "B2":
        fraction = float(rng.uniform(.20, .80))
        duplicate_amount = max(1, int(round(value * fraction)))
        observed[field] = value + duplicate_amount
        return field, "duplicate_or_overlap_inflation"
    if scenario == "B3":
        mode = int(rng.integers(0, 3))
        if mode == 0:
            observed[field] = None
            return field, "ocr_omission"
        observed[field] = max(0, value * (10 if mode == 1 else 1) if mode == 1 else int(round(value / 10)))
        return field, "locale_or_unit_parse_error"
    if rng.random() < .5:
        observed[field] = None
        return field, "source_field_omission"
    observed[field] = value + 2 * threshold
    return field, "duplicate_or_overlap_inflation"


def _case_documents(rng: np.random.Generator, scenario: str, profile: dict[str, int],
                    group_index: int, case_index: int, seed: int):
    count = _integer(rng, 2, 6)
    if scenario == "B6":
        pair = SOURCE_PAIRS[int(rng.integers(0, len(SOURCE_PAIRS)))]
        case_sources = pair
    else:
        case_sources = SOURCES

    docs: list[dict] = []
    gold_docs: list[dict] = []
    canonical_docs: list[dict] = []
    base_date = date(2025, 1, 1) + timedelta(days=(group_index * 2 + case_index) % 730)
    for doc_index in range(count):
        source = case_sources[doc_index % len(case_sources)]
        expected = dict(profile)
        semantic_note = "current normalized evidence"
        locale = "en_us"
        age_days = _integer(rng, 1, 90)
        stale_current = False

        if scenario == "B1":
            multiplier = float(rng.uniform(.80, 1.20))
            expected["income"] = int(round(profile["income"] * multiplier))
            semantic_note = "period-specific income figure"
        elif scenario == "B2":
            multiplier = float(rng.uniform(.70, 1.30))
            expected["debt"] = int(round(profile["debt"] * multiplier))
            semantic_note = "recurring payment summary"
        elif scenario == "B3":
            locale = ("en_us", "vi_vn", "space_grouped")[doc_index % 3]
            semantic_note = "amount as recorded in the source document"
        elif scenario == "B4":
            age_days = _integer(rng, 1, 365)
            stale_current = age_days > 90 and rng.random() < .12
            semantic_note = "evidence period and capture age are recorded"
        elif scenario == "B5":
            expected["income"] = int(round(profile["income"] * float(rng.uniform(.65, 1.35))))
            expected["debt"] = int(round(profile["debt"] * float(rng.uniform(.80, 1.20))))
            expected["purchase"] = int(round(profile["purchase"] * float(rng.uniform(.80, 1.20))))
            semantic_note = "reported values use a recorded effective period and normalized unit"
        elif scenario == "B6":
            semantic_note = "financial evidence record"

        observed: dict[str, int | None] = dict(expected)
        affected_field, event = _field_event(rng, scenario, expected, observed)
        if scenario == "B4" and stale_current:
            event = "stale_evidence_presented_as_current"

        verified = bool(rng.random() >= .18)
        ocr_quality = float(rng.uniform(.52, .995))
        if scenario == "B3" and locale != "en_us":
            ocr_quality = max(.20, ocr_quality - .08)
        order = list(FIELDS)
        if scenario == "B3":
            rng.shuffle(order)
        payload_values = " | ".join(f"{field.upper()}={_amount(observed[field], locale)}" for field in order)
        if scenario == "B2":
            transaction_rows = []
            for field in FIELDS:
                reference = f"TX-{group_index:04d}-{case_index}-{doc_index}-{field[:2].upper()}"
                if event == "duplicate_or_overlap_inflation" and affected_field == field:
                    duplicate_amount = observed[field] - expected[field]
                    unique_first = expected[field] - duplicate_amount
                    transaction_rows.extend((f"{reference}-A:{_amount(unique_first, locale)}",
                                             f"{reference}-B:{_amount(duplicate_amount, locale)}",
                                             f"{reference}-B:{_amount(duplicate_amount, locale)}"))
                else:
                    first_amount = expected[field] // 2
                    transaction_rows.extend((f"{reference}-A:{_amount(first_amount, locale)}",
                                             f"{reference}-B:{_amount(expected[field]-first_amount, locale)}"))
            payload_values += " | ledger rows " + "; ".join(transaction_rows)
        if scenario == "B4":
            payload_values += f" | statement period {base_date.isoformat()}"
        date_text = base_date.strftime("%d/%m/%Y") if scenario == "B3" and locale == "vi_vn" else base_date.isoformat()
        document_key = f"v4-{scenario}-g{group_index:04d}-c{case_index}-d{doc_index}"
        document = {
            "document_key": document_key,
            "source": source,
            "template": "evidence-record",
            "values": observed,
            "age_days": age_days,
            "verified": verified,
            "ocr_quality": ocr_quality,
            "text": f"{source} evidence {date_text}; {semantic_note}; {payload_values}",
            "observed_at": base_date.isoformat(),
        }

        field_errors = {
            field: int(observed[field] is None or observed[field] != expected[field])
            for field in FIELDS
        }
        material_field_errors = [
            field for field in FIELDS
            if observed[field] is None or abs(int(observed[field]) - expected[field]) >= FIELD_THRESHOLDS[field]
        ]
        critical_field_errors = [
            field for field in FIELDS
            if observed[field] is None or abs(int(observed[field]) - expected[field]) >= 2 * FIELD_THRESHOLDS[field]
        ]
        material = bool(material_field_errors) or stale_current
        critical = bool(critical_field_errors) or (stale_current and age_days >= 180)
        label = {
            "document_key": document_key,
            "observed_payload_sha256": sha256(canonical(document)).hexdigest(),
            "label_origin": "PROGRAMMATIC_GOLD",
            "scenario": scenario,
            "material_evidence_error": int(material),
            "critical_evidence_error": int(critical),
            "field_extraction_error": field_errors,
            "cross_source_inconsistency_against_synthetic_reference": {
                field: int(field in material_field_errors) for field in FIELDS
            },
            "verification_required": int(material or not verified),
            "generation_event": event,
            "affected_field": affected_field,
        }
        canonical_doc = {
            "document_key": document_key,
            "expected_normalized_values": expected,
            "semantic_note": semantic_note,
            "applicability": "not_current" if stale_current else "applicable",
            "stale_presented_as_current": stale_current,
            "generation_event": event,
        }
        docs.append(document)
        gold_docs.append(label)
        canonical_docs.append(canonical_doc)

    order = rng.permutation(len(docs)).tolist()
    return ([docs[i] for i in order], [gold_docs[i] for i in order],
            [canonical_docs[i] for i in order])


def generate(protocol: dict | None = None):
    """Generate the protocol-locked 1,920-case independent challenge."""
    protocol = protocol or json.loads(PROTOCOL.read_text(encoding="utf-8-sig"))
    cfg = protocol["e2"]
    baseline_manifest = json.loads((ROOT / "reports/evidence-v4/ARTIFACT_MANIFEST.json").read_text(encoding="utf-8-sig"))
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8-sig"))
    if sha(PROTOCOL) != baseline_manifest["experiment_protocol_sha256"]:
        raise ValueError("Registered protocol hash changed after Phase 0")
    if (amendment.get("status") != "REGISTERED_BEFORE_CONFIRMATORY_EVALUATION"
            or amendment.get("original_protocol_sha256") != sha(PROTOCOL)
            or amendment.get("no_outcome_driven_changes") is not True
            or amendment.get("confirmatory_generator_version") != "independent-event-ledger-v1.1"):
        raise ValueError("Generator B amendment is missing, mismatched, or not registered")
    if cfg["generator"] != "evidence_ai/v4_generator.py" or cfg["generator_must_not_import_v3_generator"] is not True:
        raise ValueError("Generator B protocol is not registered as independent")
    if (cfg["profile_vnd_ranges"] != {"income": [3_000_000, 30_000_000],
                                       "debt": [0, 18_000_000], "purchase": [1_000_000, 30_000_000]}
            or cfg["materiality_thresholds_vnd"] != FIELD_THRESHOLDS
            or cfg["scenario_event_rates"] != {"B1": .12, "B2": .15, "B3": .12, "B4": .12, "B5": .08, "B6": .12}
            or cfg["documents_per_case"] != [2, 6]
            or cfg["income_history_months"] != [6, 24]):
        raise ValueError("Generator B implementation differs from the registered protocol")
    seed = int(cfg["seed"])
    groups_per_scenario = int(cfg["customer_groups_per_scenario"])
    cases_per_group = int(cfg["cases_per_group"])
    if (len(cfg["scenarios"]) != len(SCENARIOS)
            or groups_per_scenario * cases_per_group * len(SCENARIOS) != cfg["total_cases"]
            or groups_per_scenario * len(SCENARIOS) != cfg["total_customer_groups"]):
        raise ValueError("Registered Generator B sample size is inconsistent")

    rng = np.random.default_rng(seed)
    cases: list[dict] = []
    labels: list[dict] = []
    facts: list[dict] = []
    scenario_index = 0
    for scenario in SCENARIOS:
        for group_index in range(groups_per_scenario):
            profile = {
                "income": _integer(rng, 3_000_000, 30_000_000),
                "debt": _integer(rng, 0, 18_000_000),
                "purchase": _integer(rng, 1_000_000, 30_000_000),
            }
            group = f"{scenario}-group-{group_index:04d}"
            for case_index in range(cases_per_group):
                documents, targets, expected_docs = _case_documents(
                    rng, scenario, profile, group_index, case_index, seed
                )
                case_key = f"{scenario}-case-{group_index:04d}-{case_index}"
                date_at = date(2025, 1, 1) + timedelta(days=(group_index * 2 + case_index) % 730)
                cases.append({
                    "case_key": case_key,
                    "customer_group": group,
                    "observed_at": date_at.isoformat(),
                    "income_history_months": _integer(rng, 6, 24),
                    "documents": documents,
                })
                labels.append({"case_key": case_key, "documents": targets})
                facts.append({
                    "case_key": case_key,
                    "customer_group": group,
                    "scenario": scenario,
                    "canonical_profile": profile,
                    "documents": expected_docs,
                })
            scenario_index += 1
    if len(cases) != int(cfg["total_cases"]) or len({row["customer_group"] for row in cases}) != int(cfg["total_customer_groups"]):
        raise ValueError("Generated case/group count differs from the registered protocol")
    return cases, labels, facts


def validate_observed_schema(cases: list[dict]) -> dict:
    """Validate exact frozen-model compatibility without coercing unsupported values."""
    errors = []
    case_fields = {"case_key", "customer_group", "observed_at", "income_history_months", "documents"}
    document_fields = {"document_key", "source", "template", "values", "age_days", "verified",
                       "ocr_quality", "text", "observed_at"}
    forbidden_text = ("programmatic_gold", "material_evidence_error", "critical_evidence_error",
                      "generation_event", "stale record incorrectly presented as current",
                      "duplicate transaction reference reconciled", "valid net-gross")
    for case in cases:
        if set(case) != case_fields:
            errors.append({"case_key": case.get("case_key"), "reason": "case_layer_contains_non_observed_fields"})
        docs = case.get("documents")
        if not isinstance(docs, list) or not 2 <= len(docs) <= 6:
            errors.append({"case_key": case.get("case_key"), "reason": "document_count_out_of_range"})
            continue
        for doc in docs:
            reason = None
            if set(doc) != document_fields:
                reason = "document_layer_contains_non_observed_fields"
            elif set(FIELDS) != set((doc.get("values") or {}).keys()):
                reason = "field_schema_mismatch"
            elif doc.get("source") not in SOURCES:
                reason = "unsupported_source_type"
            elif any(value is not None and (not isinstance(value, (int, np.integer)) or value < 0)
                     for value in doc["values"].values()):
                reason = "unsupported_value_type_or_range"
            elif not isinstance(doc.get("age_days"), int) or not isinstance(doc.get("verified"), bool):
                reason = "metadata_schema_mismatch"
            elif not isinstance(doc.get("text"), str) or not isinstance(doc.get("ocr_quality"), (int, float)):
                reason = "observed_text_or_ocr_schema_mismatch"
            elif not 0 <= float(doc["ocr_quality"]) <= 1:
                reason = "ocr_quality_out_of_range"
            elif any(pattern in doc["text"].casefold() for pattern in forbidden_text):
                reason = "gold_or_event_wording_in_observed_text"
            if reason:
                errors.append({"case_key": case.get("case_key"), "document_key": doc.get("document_key"),
                               "reason": reason})
    return {"compatible_documents": sum(len(row.get("documents", [])) for row in cases) - len(errors),
            "incompatible_documents": len(errors), "errors": errors}


def freeze(out: Path = OUT):
    """Write independent observed, canonical, and gold layers and a hash manifest."""
    cases, labels, facts = generate()
    compatibility = validate_observed_schema(cases)
    if compatibility["incompatible_documents"]:
        raise ValueError(f"Generator B emitted incompatible inputs: {compatibility['errors'][:3]}")
    out.mkdir(parents=True, exist_ok=True)
    payloads = {
        "observed.json": cases,
        "canonical_facts.json": facts,
        "gold_labels.json": labels,
    }
    for filename, payload in payloads.items():
        path = out / filename
        if path.exists():
            if json.loads(path.read_text(encoding="utf-8-sig")) != payload:
                raise ValueError(f"Protocol-locked Generator B data changed: {filename}")
        else:
            write_json(path, payload)

    scenarios = {}
    label_by_case = {row["case_key"]: row for row in labels}
    for scenario in SCENARIOS:
        scenario_cases = [row for row in cases if row["case_key"].startswith(f"{scenario}-")]
        scenario_groups = {row["customer_group"] for row in scenario_cases}
        scenario_docs = [doc for row in scenario_cases for doc in row["documents"]]
        scenario_labels = [label for row in scenario_cases for label in label_by_case[row["case_key"]]["documents"]]
        scenarios[scenario] = {
            "cases": len(scenario_cases), "customer_groups": len(scenario_groups),
            "documents": len(scenario_docs),
            "material_defects": sum(item["material_evidence_error"] for item in scenario_labels),
            "critical_defects": sum(item["critical_evidence_error"] for item in scenario_labels),
            "case_keys_sha256": sha256("\n".join(row["case_key"] for row in scenario_cases).encode()).hexdigest(),
        }
    manifest = {
        "protocol_id": "cobi-evidence-v4.0", "generator_id": "independent-event-ledger-v1.1",
        "generator_code_sha256": sha(Path(__file__)),
        "protocol_amendment_id": "cobi-evidence-v4.0-amendment-1",
        "protocol_amendment_sha256": sha(AMENDMENT),
        "generator_seed": int(json.loads(PROTOCOL.read_text(encoding="utf-8-sig"))["e2"]["seed"]),
        "protocol_sha256": sha(PROTOCOL), "scope": "SYNTHETIC_PROGRAMMATIC_GOLD_ONLY",
        "model_training": False, "calibration_or_threshold_changes": False,
        "schema_compatible": True, "compatibility": compatibility,
        "counts": {"cases": len(cases), "customer_groups": len({row["customer_group"] for row in cases}),
                   "documents": sum(len(row["documents"]) for row in cases)},
        "scenario_counts": scenarios,
        "file_sha256": {name: sha(out / name) for name in payloads},
        "labels_are_human_reviewed_bank_truth": False,
    }
    write_json(out / "generator_b_manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(freeze(), indent=2))
