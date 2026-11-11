# D1.1 Root-Cause Analysis

## Reproduced symptom

The read-only audit over `reports/evidence-v4.1/data/development-d1.1/{observed.json,gold_labels.json,split_*.json}` applies the current `time_validity` function. It finds 200 stale-as-current records and 100 disagreements where the rule says critical but the generated gold label is zero. Candidate omissions: train 60, validation 15, calibration 15, locked test 10. Input hashes and exact counts are in `D1_1_AUDIT_SUMMARY.json`.

## Source trace

- `evidence_ai/v4_1_generator_dev.py::_make_case` creates D4 historical-validity cases with two records asserted current although their effective period is outside the request period. Its `critical_idx` identifies only the deliberately modified second record.
- The generator later derives `critical_defect` from whether a record index equals `critical_idx`. The other stale record receives zero even though it has the same current-asserted / disjoint-period structure.
- `evidence_ai/semantic_evidence.py::time_validity` independently returns `STALE_AS_CURRENT` for both records and makes the result critical under the existing rule at age >=180 days.
- `research/v4_2/tools/audit_d1_1.py` joins raw observations, labels and split manifests by case and record identifiers and hashes every input. It does not write source files.

## Cause classification

| Candidate explanation | Finding |
|---|---|
| Wrong/omitted generated annotation | **Supported as internal inconsistency with the current rule:** generator intent labels only the perturbation, while the rule labels both stale-current records critical. This does not establish the correct independent gold. |
| Inconsistent semantic policy | **Also supported:** perturbation-based target semantics and rule-based stale-critical semantics differ. The repository does not show an approved policy resolving this distinction. |
| Parsing/extraction failure | **Not supported by inspected records:** the disagreement exists in structured synthetic fields before model extraction. |
| Legitimate real-world/policy ambiguity | **Unresolved and material:** 180 days is synthetic, source authority and request intent matter, and an old document can validly support a historical request. |
| Reporting/counting error | **Not supported for the reproduced counts:** raw join and split manifests reproduce 200/100 and 60/15/15/10. |

## Root cause statement

The immediate code-level cause is **target construction by perturbation index rather than by the full semantic condition later used for critical stale-as-current evaluation**. In D4, `critical_idx` makes the intentionally altered row critical; the first unchanged peer remains zero-labeled even though its current assertion and old effective period independently satisfy the registered stale rule. The broader root cause is an unapproved conflation between “the record we intentionally perturbed” and “every record that is materially stale for this request.”

This is a label-policy inconsistency in synthetic development data. It is not evidence that either row is incorrect in an independent bank workflow. Therefore every correction remains a candidate pending human/policy adjudication.
