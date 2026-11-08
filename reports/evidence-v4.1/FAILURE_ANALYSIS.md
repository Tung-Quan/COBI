# Failure Analysis — COBI Evidence V4.1

## Evaluation state

The C predictions and threshold were frozen before labels opened. C labels are now open; all analyses here are post-unblinding exploratory. No tuning or model revision was made with C.

## Generator B mechanisms preserved from the V4 audit

- **B4 stale-as-current:** all 80 critical records were missed by V4 Logistic, XGBoost and Deep Sets at frozen thresholds; CS_V2 missed 34/80. Feature inspection found no explicit effective-period match or asserted-current feature in the frozen V3 contract. This is a feature representation and threshold-transfer failure, not merely an API schema rejection.
- **B5 legitimate discrepancies:** models flagged 1,145–1,198 of 1,199 legitimate records. Large numerical disagreement without semantic comparability was treated as error. Score saturation/overlap means a simple lower cutoff cannot solve this ranking problem.
- **B6 unseen source pair:** CS_V2 and XGBoost missed 106/167 and 95/167 critical records; Logistic and Deep Sets each missed 4/167. For XGBoost, high critical ranking AP with only 72/167 above the frozen threshold indicates a strong operating-point transfer component. These B observations are exploratory diagnostics, not new validation.

## Generator C observed errors and cases

- **Stale evidence:** Hybrid flags 120/120 C4 stale-as-current critical records. The development label audit finding means learned temporal attribution is invalidated; the result is consistent with the deterministic time rule matching the generated label criterion.
- **Legitimate differences:** no false alerts occurred in C1 gross/net and period differences, C3 correction lineage, or C5 different subject/account records (0/2,927). This is a finite synthetic result under rule-aligned semantics.
- **Same-period and genuine conflicts:** the Hybrid raises alerts on both records in a comparable conflicting pair. C2 contributes 160 false-positive companion records; C6 contributes 120. A record-level alert does not establish which source is incorrect. Without an adjudication signal, this is a review signal rather than a per-document defect diagnosis.
- **Held-out payroll+merchant pair:** C7 critical recall is reported by its 120/120 denominator, but C7 also contributes 120 legitimate-document false positives in mixed conflict cases. A held-out pair of known source types is a narrow source-combination challenge, not real-source validation.
- **Rules and thresholds:** `SEMANTIC_RULE` obtains full critical recall but its overall legitimate FPR is 10.38%, higher than the Hybrid's 6.38%; the rule's temporal scoping also flags valid side-field records in C4. The model+rule Hybrid combines rule alerts with calibrated probabilities.

## False alerts versus fixed thresholds

Threshold changes cannot be used post hoc to rescue C. V4 B diagnostics already showed that ranking and fixed-threshold effects vary by scenario: B4 learned models failed ranking as well as threshold transfer, B5 score overlap pointed to semantic interpretation/ranking, and B6 XGBoost retained ranking but failed at its operating point. For C, the Hybrid's 400 legitimate false-positive documents are concentrated in the positive conflict scenarios where both conflicting peers are alerted. The registered C1/C3/C5 endpoint has zero observed false alerts. C ablations have different frozen thresholds, so their point differences combine ranking and operating-point changes.

## Construct and shortcut audit

Features contain observed record semantics only; hidden canonical truth and label/corruption fields are absent from the encoder. Nonetheless, the generator and deterministic validator share field tolerances and stale-age semantics. This is target-construct overlap, not direct hidden-label leakage. A truly independent challenge should use independently adjudicated evidence rules, institutions and document workflows, and should freeze criteria before any inspection.

## Failure taxonomy and examples

Examples below are schematic, not copied from hidden Generator C truth:

1. **Valid non-comparable values:** gross monthly salary and net pay, or values covering non-overlapping periods. Values differ; a contradiction is not warranted.
2. **Correction lineage:** an original transaction is marked superseded by a corrected posting. Keeping both for audit is legitimate; the current state should use the correction.
3. **Historical evidence:** an old statement can be valid when matching a historical request; the same statement asserted as current for a later period can be stale.
4. **Comparable conflict:** same subject, account, financial meaning, direction and overlapping period with values beyond the registered tolerance. Both records merit review; additional evidence is needed to identify the erroneous one.
5. **Threshold and review granularity:** pairwise rules can correctly detect a conflict yet still flag a legitimate peer. Document-level false-positive rate and case-level workload answer different questions.

Full prediction-level failure rows and explanation records remain in the preserved C evaluation artifacts. They are not reclassified or tuned here.
