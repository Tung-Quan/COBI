# Generator C Results — V4.1

**Status:** POST-UNBLINDING RECONCILIATION; EXPLORATORY. **Validation:** `EVIDENCE_AI_VALIDATION_BLOCKED`.

## Dataset and frozen-output record

Generator `semantic-ledger-c-v1.0`, seed `2026110802`, protocol `cobi-evidence-v4.1-c1.0`. The challenge has **840 customer groups**, **1,680 cases**, and **6,791 documents**. Predictions were frozen before labels opened: prediction SHA-256 `03d1a2a6aa3d52eae483cca2d538e8cf71777eea17aa32215160bc5be3dc7523`. This report reconciles those frozen outputs; no model, rule condition, calibration, threshold, or selection was changed using C labels.

Generator C labels have already been opened. These are observed measurements on a registered synthetic challenge, but they are not a fresh blinded confirmatory evaluation.

## Semantic Hybrid point estimates

| Metric | Numerator / denominator | Estimate | 95% customer-group bootstrap interval |
|---|---:|---:|---:|
| Critical recall | 520 / 520 | 100.00% | [1.0000, 1.0000] |
| Critical FNR | 0 / 520 | 0.00% | [0, 0] |
| Overall legitimate-document FPR | 400 / 6271 | 6.38% | [0.0594, 0.0681] |
| C1/C3/C5 legitimate-discrepancy FPR | 0 / 2927 | 0.00% | [0.0000, 0.0000] |
| C4 stale-as-current recall | 120 / 120 | 100.00% | [1.0000, 1.0000] |
| Case review workload | 520 / 1680 | 30.95% | [0.2952, 0.3238] |
| Material-defect average precision | 520 material positives / 6791 documents | 0.5652 | [0.5620, 0.5688] |
| Brier score | mean squared probability error over 6791 documents | 0.0339 | [0.0319, 0.0358] |
| Log loss | mean binary cross-entropy over 6791 documents | 0.0939 | [0.0884, 0.0992] |

Metric denominators are document-level except workload, which is case-level. FPR is FP/(FP+TN) among gold legitimate documents. Critical recall is TP/(TP+FN). AP uses the continuous material-defect probability and all 6791 documents. Brier and log loss use the calibrated frozen probability outputs. The case workload counts a case if one or more of its documents crossed the frozen decision threshold `0.50003149`.

The C1/C3/C5 zero is **0 observed errors**, not zero population risk. The bootstrap percentile interval is degenerate at this boundary. Cluster-aware bounds are reported separately in `STATISTICAL_AUDIT.md`.

## Outcomes by scenario

| Scenario | Documents | Critical TP / support | Critical recall | Legitimate FP / support | Legitimate FPR | Cases flagged / total | Workload |
|---|---:|---:|---:|---:|---:|---:|---:|
| C1_GROSS_NET_PERIODS | 974 | 0/0 | — | 0/974 | 0.00% | 0/240 | 0.00% |
| C2_SAME_PERIOD_CORRUPTION | 982 | 160/160 | 100.00% | 160/822 | 19.46% | 160/240 | 66.67% |
| C3_CORRECTION_LINEAGE | 964 | 0/0 | — | 0/964 | 0.00% | 0/240 | 0.00% |
| C4_TIME_VALIDITY | 949 | 120/120 | 100.00% | 0/829 | 0.00% | 120/240 | 50.00% |
| C5_NONCOMPARABLE_SUBJECT_ACCOUNT | 989 | 0/0 | — | 0/989 | 0.00% | 0/240 | 0.00% |
| C6_TRUE_COMPARABLE_CONFLICT | 981 | 120/120 | 100.00% | 120/861 | 13.94% | 120/240 | 50.00% |
| C7_HELD_OUT_SOURCE_PAIR | 952 | 120/120 | 100.00% | 120/832 | 14.42% | 120/240 | 50.00% |

Undefined recall/AP values for scenarios without positive examples remain null. Source-stratified detail is in `GENERATOR_C_SOURCE_METRICS.csv`; the paired model contrasts and raw grouped CIs are preserved in companion CSV files.

## Outcomes by source type

| Source | Documents | Critical TP / support | Legitimate FP / support | Case workload |
|---|---:|---:|---:|---:|
| statement | 2593 | 140/140 (100.00%) | 140/2453 (5.71%) | 280/1560 (17.95%) |
| payroll | 2071 | 200/200 (100.00%) | 180/1871 (9.62%) | 380/1315 (28.90%) |
| merchant | 2127 | 180/180 (100.00%) | 80/1947 (4.11%) | 260/1313 (19.80%) |

## Frozen baseline comparison after unblinding

| Arm | Critical recall | Legitimate FPR | Case workload | AP |
|---|---:|---:|---:|---:|
| M0_CS_V2 | 100.00% (520/520) | 99.97% (6269/6271) | 99.94% (1679/1680) | 0.1279 |
| M1_LOGISTIC | 100.00% (520/520) | 100.00% (6271/6271) | 100.00% (1680/1680) | 0.0839 |
| M3_DEEP_SETS | 100.00% (520/520) | 100.00% (6271/6271) | 100.00% (1680/1680) | 0.0928 |
| SEMANTIC_RULE | 100.00% (520/520) | 10.38% (651/6271) | 37.08% (623/1680) | 0.5652 |
| SEMANTIC_LOGISTIC | 4.81% (25/520) | 0.89% (56/6271) | 4.82% (81/1680) | 0.3731 |
| SEMANTIC_DEEP_SETS | 8.46% (44/520) | 1.02% (64/6271) | 5.42% (91/1680) | 0.3760 |
| SEMANTIC_HYBRID | 100.00% (520/520) | 6.38% (400/6271) | 30.95% (520/1680) | 0.5652 |
| V4 XGBoost | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |
| Semantic XGBoost | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |

M0/CS_V2, frozen V4 Logistic/Deep Sets, semantic rule, semantic Logistic, and semantic Deep Sets are replayable; the comparison is delayed and post-unblinding. Both XGBoost branches require the exact frozen `xgboost==3.0.5` runtime, which is unavailable in the local environments and pip cache. No model was substituted or retrained. Thus the registered all-baseline acceptance criterion remains incomplete, and no claim of superiority to all baselines is supported.

## Interpretation

On this synthetic C label set, the frozen Hybrid recorded 520/520 critical detections and 0/2,927 false alerts on the registered C1/C3/C5 endpoint. It also generated 400 false-positive document alerts overall; 160 were in C2, 120 in C6 and 120 in C7. Pairwise deterministic conflict logic flags both records in a conflicting pair because the records alone do not identify which one is wrong. This is a review alert, not a diagnosis that the paired legitimate record is erroneous.

The values are exploratory and construct-dependent. A separate audit found 100 development records whose observable temporal rule indicated critical stale-as-current evidence but whose D1.1 synthetic gold omitted a critical label; those affected training, validation, calibration, and locked test. Also, C's generator thresholds and stale semantics align with rule conditions. This prevents clean causal attribution to learned semantic features and weakens confirmatory external-validity claims.
