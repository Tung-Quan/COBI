"""Build reviewer blanks and edge-case examples from existing read-only records."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from research.v4_2.tools.audit_d1_1 import INPUT_DIR, audit_dataset

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _save(name: str, bundle: dict) -> None:
    (EXAMPLES / name).write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _annotated(bundle: dict, rationale: str = "Illustrative edge case; not independently adjudicated.") -> dict:
    for claim in bundle["claims"]:
        claim.setdefault("claim_group_id", None)
        claim.setdefault("subject_state", "KNOWN" if claim.get("subject_id") else "UNKNOWN")
        claim.setdefault("account_state", "KNOWN" if claim.get("account_id") else "UNKNOWN")
        claim.setdefault("event_time_state", "KNOWN" if claim.get("event_time") else "UNKNOWN")
        claim.setdefault("provenance_state", "PARTIAL" if claim.get("provenance", {}).get("span") else "UNKNOWN")
        claim["source"].setdefault("source_issued_at", None)
        claim["source"].setdefault("source_timestamp_state", "UNKNOWN")
    for pair in bundle["pairs"]:
        pair["annotation"]["rationale"] = rationale
    return bundle


def make_review_csv() -> int:
    report, rows = audit_dataset()
    raw = json.loads((INPUT_DIR / "observed.json").read_text(encoding="utf-8-sig"))
    label_rows = json.loads((INPUT_DIR / "gold_labels.json").read_text(encoding="utf-8-sig"))
    cases = {case["case_id"]: case for case in raw}
    labels = {case["case_id"]: {record["record_id"]: record for record in case["records"]} for case in label_rows}
    fields = [
        "case_identifier", "evidence_identifier", "split", "synthetic_observed_evidence_context_json",
        "existing_label", "candidate_label", "rule_trigger", "generator_provenance",
        "reason_for_proposed_change", "alternative_interpretation", "reviewer_decision",
        "reviewer_justification", "reviewer_name", "review_date", "adjudication_status",
        "approved_gold", "evidence_pointers",
    ]
    output = ROOT / "D1_1_LABEL_REVIEW.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for audit in rows:
            if audit["candidate_label_status"] != "PENDING_ADJUDICATION":
                continue
            case = cases[audit["case_id"]]
            record = next(row for row in case["records"] if row["record_id"] == audit["record_id"])
            context = {
                "synthetic": True,
                "scenario": audit["scenario"],
                "request": case["request"],
                "record": record,
                "temporal_rule_observation": json.loads(audit["supporting_observations_json"]),
                "candidate_is_not_gold": True,
            }
            old = labels[audit["case_id"]][audit["record_id"]]
            writer.writerow({
                "case_identifier": audit["case_id"],
                "evidence_identifier": audit["record_id"],
                "split": audit["split"],
                "synthetic_observed_evidence_context_json": json.dumps(context, sort_keys=True, separators=(",", ":")),
                "existing_label": json.dumps(old, sort_keys=True, separators=(",", ":")),
                "candidate_label": json.dumps({"critical_defect": 1, "status": "CANDIDATE_ONLY"}, separators=(",", ":")),
                "rule_trigger": "time_validity => STALE_AS_CURRENT; critical=true; age_days>=180 under existing synthetic rule",
                "generator_provenance": "evidence_ai/v4_1_generator_dev.py::_make_case D4_HISTORICAL_VALIDITY; generator sets critical_idx on deliberately altered second record",
                "reason_for_proposed_change": "Temporal rule labels this current-asserted record stale/critical while programmatic gold has critical_defect=0.",
                "alternative_interpretation": "180-day threshold/criticality may be generator-specific, policy may differ, source validity/intent may be ambiguous; rule consistency does not establish independent truth.",
                "reviewer_decision": "",
                "reviewer_justification": "",
                "reviewer_name": "",
                "review_date": "",
                "adjudication_status": "PENDING_ADJUDICATION",
                "approved_gold": "NO",
                "evidence_pointers": audit["evidence_pointers"],
            })
    return report["candidate_critical_omissions"]


def make_edge_cases() -> None:
    b = _annotated(_load("missing_currency_unknown.json"))
    b["case_id"] = "case-missing-period"
    for c in b["claims"]:
        c["case_id"] = b["case_id"]
    b["claims"][0]["period"] = {"state": "MISSING", "start": None, "end": None}
    pair = b["pairs"][0]
    pair["case_id"] = b["case_id"]
    pair["comparability"] = "UNKNOWN"
    pair["relationship"] = "UNRESOLVED"
    pair["reason_codes"] = ["APPLICABLE_PERIOD_MISSING"]
    b["case_action"]["case_id"] = b["case_id"]
    b["case_action"]["reference_action"] = "REQUEST_MORE_EVIDENCE"
    b["requested_period"] = None
    b["case_action"]["requested_period"] = None
    _save("missing_applicable_period.json", b)

    b = _annotated(_load("same_period_conflict_unresolved_attribution.json"), "Third-source corroboration is present as an evidence reference, but no adjudicator has validated its independence or authority; attribution remains unresolved.")
    b["case_id"] = "case-third-source-corroboration"
    b["requested_period"] = {"start": "2025-01-01", "end": "2025-01-31"}
    template = b["claims"][0]
    corroborating = json.loads(json.dumps(template))
    corroborating.update({"claim_id": "claim-third-source", "claim_group_id": "financial-claim-001", "case_id": b["case_id"]})
    corroborating["amount"]["value"] = b["claims"][0]["amount"]["value"]
    corroborating["source"] = {"source_id": "source-third", "source_type": "independent_statement", "verification_state": "UNVERIFIED", "source_issued_at": "2025-02-02T10:00:00Z", "source_timestamp_state": "KNOWN"}
    corroborating["document"] = {"document_id": "doc-third", "version": "1", "supersedes_document_id": None}
    b["claims"].append(corroborating)
    for c in b["claims"][:2]:
        c["case_id"] = b["case_id"]
        c["claim_group_id"] = "financial-claim-001"
        c["source"]["source_issued_at"] = "2025-02-01T10:00:00Z"
        c["source"]["source_timestamp_state"] = "KNOWN"
    b["pairs"][0]["case_id"] = b["case_id"]
    b["pairs"][0]["document_attribution"][0]["independent_evidence_refs"] = ["claim-third-source"]
    b["pairs"][0]["reason_codes"].append("THIRD_SOURCE_PRESENT_NOT_ADJUDICATED")
    p2 = json.loads(json.dumps(b["pairs"][0]))
    p2.update({"pair_id": "pair-third-corroborates-first", "claim_ids": ["claim-third-source", b["claims"][0]["claim_id"]], "comparability": "COMPARABLE", "relationship": "CONSISTENT", "supersedes_direction": None, "reason_codes": ["THIRD_SOURCE_CORROBORATION_CANDIDATE"]})
    p2["document_attribution"] = [{"claim_id": cid, "status": "UNRESOLVED", "rationale": "Corroboration is not an adjudicated authority determination.", "independent_evidence_refs": []} for cid in p2["claim_ids"]]
    b["pairs"].append(p2)
    b["case_action"]["case_id"] = b["case_id"]
    _save("third_source_corroboration.json", b)

    b = _annotated(_load("same_period_conflict_unresolved_attribution.json"), "Conflicting source-issued timestamps are stored as observed; without an authoritative timestamp policy, temporal ordering is unknown.")
    b["case_id"] = "case-conflicting-source-timestamps"
    for c in b["claims"]:
        c["case_id"] = b["case_id"]
    b["claims"][0]["source"].update({"source_issued_at": "2025-02-01T10:00:00Z", "source_timestamp_state": "KNOWN"})
    b["claims"][1]["source"].update({"source_issued_at": "2025-01-31T20:00:00Z", "source_timestamp_state": "KNOWN"})
    b["pairs"][0].update({"case_id": b["case_id"], "comparability": "UNKNOWN", "relationship": "UNRESOLVED", "reason_codes": ["SOURCE_TIMESTAMP_CONFLICT_REQUIRES_POLICY"]})
    b["case_action"]["case_id"] = b["case_id"]
    b["case_action"]["reference_action"] = "REQUEST_MORE_EVIDENCE"
    _save("conflicting_source_timestamps.json", b)

    b = _annotated(_load("same_period_conflict_unresolved_attribution.json"), "Two documents contain records about one normalized financial claim; record-level provenance remains separate.")
    b["case_id"] = "case-multiple-records-one-claim"
    for c in b["claims"]:
        c["case_id"] = b["case_id"]
        c["claim_group_id"] = "financial-claim-001"
    b["pairs"][0]["case_id"] = b["case_id"]
    b["case_action"]["case_id"] = b["case_id"]
    _save("multiple_records_one_claim.json", b)

    for path in EXAMPLES.glob("*.json"):
        bundle = _annotated(_load(path.name))
        _save(path.name, bundle)


def main() -> None:
    count = make_review_csv()
    make_edge_cases()
    print(json.dumps({"review_rows": count, "new_edge_cases": 4, "status": "PENDING_ADJUDICATION"}))


if __name__ == "__main__":
    main()
