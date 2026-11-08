# V4.1 Baseline Audit — Before Implementation Changes

**Audit:** no discrepancy found in the reviewed V4 results or protected model artifacts. This audit was run before V4.1 implementation changes.

## Integrity

- V4 final manifest files verified: **96/96**.
- Selected V3 model artifacts and selection-lock hashes: verified.
- V3 model manifest: 32 features; capacity 6; selected variant `ds-1`; seeds `[13, 29, 43]`.
- V4 bank authorization remains false; no V2–V4 artifact was changed during this audit.

## Recomputed failure counts from E2 prediction rows

The following counts were recomputed from all 7,744 rows in `reports/evidence-v4/tables/e2_prediction_level.csv` using the frozen flags and labels, then checked against the E2 JSON and narrative reports.

| Scenario / model | Critical FN / support | Legitimate FP / support |
|---|---:|---:|
| B4 / CS_V2 | 34 / 80 | 610 / 1170 |
| B4 / Logistic | 80 / 80 | 33 / 1170 |
| B4 / XGBoost | 80 / 80 | 0 / 1170 |
| B4 / Deep Sets | 80 / 80 | 0 / 1170 |
| B5 / CS_V2 | 1 / 68 | 1198 / 1199 |
| B5 / Logistic | 0 / 68 | 1192 / 1199 |
| B5 / XGBoost | 3 / 68 | 1145 / 1199 |
| B5 / Deep Sets | 0 / 68 | 1174 / 1199 |
| B6 / CS_V2 | 106 / 167 | 362 / 1152 |
| B6 / Logistic | 4 / 167 | 87 / 1152 |
| B6 / XGBoost | 95 / 167 | 1 / 1152 |
| B6 / Deep Sets | 4 / 167 | 25 / 1152 |

The recomputed counts match the V4 report. B4 has 80 critical documents: CS_V2 misses 34 and each learned model misses 80. B5 has 1,199 legitimate documents; 1,145–1,198 are flagged across models. B6 has 167 critical documents; CS_V2 misses 106 and XGBoost misses 95, while Logistic and Deep Sets each miss 4.

## Exploratory score-distribution findings

All results in this section are post-hoc diagnostics on the already evaluated Generator B; they do not modify the V4 confirmatory results.

- **B4 ranking plus threshold:** critical AP is low for the learned models. The frozen thresholds further suppress detection: none of the three learned models flags any of the 80 critical documents. This is both a ranking and operating-point transfer failure, rather than a cutoff-only issue.
- **B5 semantics and ranking:** critical and legitimate scores overlap or saturate high. For XGBoost, the legitimate score median is approximately 0.996 and critical median approximately 0.998; lowering the threshold cannot separate those classes. Logistic and Deep Sets show the same high-score overlap.
- **B6 model-specific mechanism:** XGBoost critical AP is approximately 0.953, but the frozen threshold 0.924 flags only 72/167 critical documents. This is primarily threshold transfer. CS_V2 has weak B6 critical ranking (AP approximately 0.171); Logistic and Deep Sets retain strong ranking and recall.
- Score quantiles by scenario, label and model are in `score_distributions.csv`; recomputed scenario metrics are in `scenario_metrics_recomputed.csv`.

## Feature-contract observations

The frozen 32-feature contract includes log amounts, missingness, OCR quality, age in days, verification, three source one-hot features, raw peer gaps, document count, four CS subscores and 12 hashed-text features. It omits subject/account identity, effective-period overlap, gross/net meaning, correction lineage, transaction direction, and whether old evidence is asserted current or presented historically. Peer gaps compare values without first checking semantic comparability. The CS consistency/recency subscores also use numerical similarity and age without effective-period semantics.

Schema rejection does not explain the V4 failures: all 7,744 B documents were compatible, and B used the same three individual source categories. B6 tests source-set combinations, not unseen individual source types. These are mechanism hypotheses supported by the feature contract and score patterns; they are not causal proof.
