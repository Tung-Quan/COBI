# COBI Evidence AI V4.1 — Generator C Scientific Report

**Report date:** 2026-11-08  
**Protocol:** `cobi-evidence-v4.1-c1.0`  
**Generator:** `semantic-ledger-c-v1.0`  
**Study status:** `PARTIAL_INDEPENDENT_SYNTHETIC_EVALUATION`  
**Validation status:** `EVIDENCE_AI_VALIDATION_BLOCKED`

## Executive finding

On the preregistered synthetic Generator C challenge, the frozen semantic hybrid flagged all 520 labeled critical records, including all 120 stale-as-current records in C4. It flagged no legitimate records in the registered C1/C3/C5 endpoint (0/2,927), while its overall legitimate-record FPR was 400/6,271 (6.38%) and case review workload was 520/1,680 (30.95%). Its material-defect AP was 0.565, Brier score 0.0339, and log loss 0.0939.

These are measured outcomes on generated structured evidence. They do not establish performance on real financial documents. The development-label audit found that 100 stale records in D1.1 were missing critical labels, making feature-effect interpretations exploratory. The XGBoost replay dependency was unavailable, so the complete registered baseline acceptance criterion remains unassessable. The status remains **`EVIDENCE_AI_VALIDATION_BLOCKED`**.

**Construct-independence caveat:** Generator C is independently implemented, but its gold criteria overlap with the deterministic semantic rules. The generator uses the same VND field tolerances for C2/C6/C7 conflicts, and both C4 gold construction and the time rule use a 180-day critical-staleness criterion. The 100% recall therefore does not constitute a fully independent test of those semantic criteria. This is target-construct overlap, not evidence that hidden gold labels were passed to the predictor.

## Study question

Can a semantic representation of financial evidence improve defect detection under independent synthetic distribution shift while avoiding alerts on valid differences between records that are not comparable?

Generator C challenges a frozen release on seven registered scenarios: gross/net and period mismatch; same-period corruption; correction lineage; time validity; non-comparable subjects/accounts; true comparable conflict; and a held-out payroll+merchant source pair. Its generator implementation and seed are separate from development data and Generator B.

## Protocol and data

- Protocol ID `cobi-evidence-v4.1-c1.0`, registered before Generator C creation and label evaluation.
- 840 customer groups, 1,680 cases, and 6,791 structured evidence records. There are 520 labeled critical records.
- Predictions were frozen before label access. The prediction checksum and frozen model manifest were checked by the post-unblinding reconciliation.
- The reconciliation recomputed all aggregate metrics from the frozen predictions and labels; every aggregate matched the original evaluation (`all_previous_aggregate_metrics_match = true`). It changed no model or threshold.
- Uncertainty uses 500 scenario-stratified customer-group bootstrap draws. Intervals condition on the chosen synthetic generator, label rules, frozen models, and thresholds.
- The hybrid operating threshold was frozen at `0.500031490427`.

The data-quality endpoint records generated financial facts and semantics. It does not measure OCR, document parsing, evidence acquisition, or real-world adjudication.

### Construct independence and rule-target overlap

Generator C has a separate implementation path, seed, and templates, but the generator and deterministic semantic comparator share parts of the target definition. Both use VND tolerances of income 500,000, debt 250,000, and purchase 500,000. In the C2, C6, and C7 corruption cases, generated amount differences are 2.1-4.2 times the applicable tolerance, while the comparator marks a comparable pair critical at a difference of at least two times that tolerance. For C4, the gold marks an old record asserted as current and the rule marks a period-mismatched record critical at age 180 days or more; generated stale records are 432 days old. This is semantic-criterion overlap, not direct hidden-label leakage: corruption identifiers and canonical gold are not predictor inputs. It means strong recall demonstrates agreement with these generated constructs and rules, not independent generalization to externally adjudicated criteria.

## Primary results

| Outcome | Observed result | 95% customer-group bootstrap interval |
|---|---:|---:|
| Critical recall | 520 / 520 (100.0%) | 100.0%–100.0% |
| C4 stale-as-current recall | 120 / 120 (100.0%) | 100.0%–100.0% |
| C1/C3/C5 legitimate-discrepancy FPR | 0 / 2,927 (0.0%) | 0.0%–0.0% |
| Overall legitimate-record FPR | 400 / 6,271 (6.4%) | See group-level uncertainty note |
| Case review workload | 520 / 1,680 (31.0%) | 29.5%–32.4% |
| Material-defect average precision | 0.565 | 0.562–0.569 |
| Brier score | 0.034 | 0.032–0.036 |
| Log loss | 0.094 | 0.088–0.099 |

The 400 false-positive records are valid peers of corrupted records in comparable-pair contradiction scenarios. The pair-level rule requests review of both members because it has no independent signal identifying which peer is wrong:

| Scenario | False-positive records | Legitimate support |
|---|---:|---:|
| C2_SAME_PERIOD_CORRUPTION | 160 | 822 |
| C6_TRUE_COMPARABLE_CONFLICT | 120 | 861 |
| C7_HELD_OUT_SOURCE_PAIR | 120 | 832 |

The C1/C3/C5 zero observed false-positive rate has zero errors in the registered sample. A group-level exact binomial analysis found no group with any endpoint false positive among 360 groups; the one-sided 95% upper bound for that *group event rate* is 0.83%. A separate conservative Hoeffding upper bound for equal-group-weighted FPR is 6.45%. These are group-level quantities and are not document-weighted FPR intervals.

### Scenario breakdown

| Scenario | Documents | Critical support | Critical recall | Legitimate FPR | Review workload |
|---|---:|---:|---:|---:|---:|
| C1_GROSS_NET_PERIODS | 974 | 0 | N/A | 0.0% | 0.0% |
| C2_SAME_PERIOD_CORRUPTION | 982 | 160 | 100.0% | 19.5% | 66.7% |
| C3_CORRECTION_LINEAGE | 964 | 0 | N/A | 0.0% | 0.0% |
| C4_TIME_VALIDITY | 949 | 120 | 100.0% | 0.0% | 50.0% |
| C5_NONCOMPARABLE_SUBJECT_ACCOUNT | 989 | 0 | N/A | 0.0% | 0.0% |
| C6_TRUE_COMPARABLE_CONFLICT | 981 | 120 | 100.0% | 13.9% | 50.0% |
| C7_HELD_OUT_SOURCE_PAIR | 952 | 120 | 100.0% | 14.4% | 50.0% |

C7 contains 60 positive customer groups; all had every critical record detected. The exact 95% group-level interval for this all-critical-records-detected event is 94.0%–100%. In C7, 120/832 legitimate records were also flagged (14.4%), so recall should be read together with the review burden.

## Frozen model comparison

| Frozen model | Critical recall | Legitimate-record FPR | Case review workload | Material AP |
|---|---:|---:|---:|---:|
| Semantic hybrid | 100.0% (520/520) | 6.4% | 31.0% | 0.565 |
| Semantic rules | 100.0% (520/520) | 10.4% | 37.1% | 0.565 |
| Frozen CS V2 | 100.0% (520/520) | 100.0% | 99.9% | 0.128 |
| Frozen Logistic Regression | 100.0% (520/520) | 100.0% | 100.0% | 0.084 |
| Frozen Deep Sets | 100.0% (520/520) | 100.0% | 100.0% | 0.093 |

Frozen CS V2, Logistic Regression, and Deep Sets each achieved 100% critical recall in this challenge while flagging approximately all legitimate records and sending nearly every case to review. The semantic hybrid retained the same observed critical recall with substantially fewer alerts on this synthetic challenge. The pairwise bootstrap contrasts are descriptive and post-unblinding; they are not confirmatory model-selection evidence.

The semantic rule baseline alone also achieved 100% critical recall, with 10.38% overall legitimate FPR and 37.08% case workload. The hybrid's corresponding point estimates were 6.38% and 30.95%. Learned-model contributions remain uncertain because of the D1.1 label inconsistency described below.

## Registered feature ablations

| Logistic arm | Critical recall | C4 stale recall | C1/C3/C5 FPR | Overall legitimate FPR | Case workload |
|---|---:|---:|---:|---:|---:|
| Full semantic Logistic Regression | 4.8% | 0.0% | 0.0% | 0.9% | 4.8% |
| Without temporal features | 5.6% | 0.0% | 0.0% | 1.0% | 5.6% |
| Without comparability features | 34.4% | 100.0% | 16.9% | 21.5% | 63.0% |
| Without source/provenance features | 15.0% | 0.0% | 8.9% | 9.9% | 34.6% |

The full semantic Logistic Regression and its no-temporal ablation both had 0% C4 stale-as-current recall. This challenge therefore does not show that the learned temporal features improved stale recall. Removing comparability features raised logistic critical recall from 4.8% to 34.4%, but also raised overall legitimate FPR from 0.9% to 21.5% and case workload from 4.8% to 63.0%. These frozen-threshold outcomes show a trade-off in this experiment; they do not establish a causal or general feature contribution.

## Registered acceptance criteria

| Criterion | Result | Status |
|---|---:|---|
| Aggregate critical recall at least 90% | 520/520 = 100% | Point estimate meets |
| C4 stale-as-current recall at least 90% | 120/120 = 100% | Point estimate meets |
| C1/C3/C5 legitimate-discrepancy FPR at most 20% | 0/2,927 = 0% | Point estimate meets |
| C7 critical recall at least 85% | 120/120 = 100% | Point estimate meets |
| Recall no more than 2 percentage points below the best complete frozen baseline | Best available frozen baseline = 100%; XGBoost replay unavailable | **Unassessable as registered** |

Four criteria meet their point-estimate thresholds. The complete registered criterion set is not met as an evaluable package because the frozen XGBoost baseline could not run. No XGBoost result was fabricated or substituted.

## Data-quality audit and interpretation

The post-evaluation D1.1 audit found 200 records that the temporal rule treats as stale-as-current; 100 were labeled noncritical. The missing critical labels span the training, validation, calibration, and locked development-test partitions (60, 15, 15, and 10 records). Generator C labels and scores were not changed or reopened for tuning. This issue does not rewrite the frozen C measurements, but it weakens training and threshold evidence about temporal behavior and means that the semantic learned feature effects must be treated as exploratory.

The hybrid's 100% recall includes deterministic semantic rules. It cannot be attributed to learned semantic features alone. The strong point estimates on C are therefore evidence that this frozen, rule-plus-model system succeeded on the registered generated scenarios, not that the model learned a generally valid financial-evidence rule.

## Limitations and deployment status

1. All examples, labels, and financial facts are programmatically generated; the distributions may not represent banks, merchants, or borrower documents.
2. Structured metadata is provided to the evaluator. OCR and upstream extraction quality are outside the experiment.
3. The finite scenario taxonomy and held-out source pair do not cover all financial products, document types, languages, or source systems.
4. Bootstrap intervals are conditional on the frozen synthetic data-generating process and do not account for generator misspecification or label-policy error.
5. The D1.1 temporal-label inconsistency prevents confirmatory attribution of learned feature effects.
6. XGBoost replay was blocked by the unavailable `xgboost==3.0.5` dependency; full baseline acceptance is incomplete.
7. The pair-level comparator flags a valid peer alongside true contradictions when it cannot identify the corrupt member, contributing 400 false-positive records.
8. Generator C is independent in implementation path, seed, and templates, but its C2/C6/C7 monetary defect magnitudes and C4 stale-age criterion overlap with the deterministic rules. The 100% recall result is therefore not a fully independent validation of those semantic criteria; this is construct overlap, not direct hidden-label leakage.

Research outputs remain read-only. `routing_authorized = false`, `approval_authorized = false`, and checkout does not consume Generator C outputs. No lending or operational use is authorized.

## Reproducibility and artifact map

- Frozen primary output: `data/generator-c-v1/GENERATOR_C_RESULTS.json`
- Independent arithmetic reconciliation: `GENERATOR_C_METRICS.json`
- Full scenario/source/contrast tables: `tables/`
- Protocol: `EXPERIMENT_PROTOCOL_C.md`
- Development-label audit: `POST_EVALUATION_AUDIT_ADDENDUM.json`
- Prediction freeze manifest: `data/generator-c-v1/C_PREDICTION_MANIFEST.json`
- Evaluation manifest: `data/generator-c-v1/C_EVALUATION_MANIFEST.json`
- Release integrity manifest: `RELEASE_MANIFEST.json`

All presentation artifacts are derived from the existing frozen results. This reporting step does not train models, change predictions, or select thresholds.
