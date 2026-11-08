# Statistical Audit — Generator C

**Disposition:** observed, post-unblinding, synthetic-only; `EVIDENCE_AI_VALIDATION_BLOCKED`.

## Metric definitions and units

| Metric | Unit and denominator |
|---|---|
| Material defect AP | Document-level precision-recall ranking, 520 positives among 6,791 documents; prevalence-dependent. |
| Critical recall / FNR | Documents labeled critical: TP/(TP+FN), FN/(TP+FN); 520 critical documents. |
| Legitimate-document FPR | Gold legitimate documents: FP/(FP+TN); 6,271 documents. |
| C1/C3/C5 FPR | Gold legitimate records in the registered subgroups: 0 FP / 2,927 records. |
| C4 stale recall | Gold critical stale-as-current records: 120 records. |
| Review workload | Cases with ≥1 flagged record / all 1,680 cases. It is not a document flag rate. |
| Brier | Mean (p-y)^2 over all 6,791 document probabilities. |
| Log loss | Mean binary cross-entropy over the same 6,791 probabilities; clips are inherited from the evaluated probability output. |

Threshold and calibration are frozen from development calibration. AP and proper scoring metrics use continuous predictions; threshold metrics use the released threshold. Results do not include any test-driven threshold change.

## Customer-group bootstrap

The stored 500-draw bootstrap resamples customer groups within the seven registered scenarios (seed `2026110803`), carrying both cases and all documents from each sampled group. It preserves within-group dependence and produces paired model contrasts. Intervals condition on these fixed generators, labels, fitted models and calibration. They do not include model-training, label-generation, generator-specification, or future institutional uncertainty.

| Hybrid metric | Point | Percentile 95% interval |
|---|---:|---:|
| AP | 0.5652 | [0.5620, 0.5688] |
| Critical recall | 100.00% | [1.0000, 1.0000] |
| Overall legitimate FPR | 6.38% | [0.0594, 0.0681] |
| C1/C3/C5 FPR | 0.00% | [0.0000, 0.0000] |
| C4 stale recall | 100.00% | [1.0000, 1.0000] |
| Case workload | 30.95% | [0.2952, 0.3238] |
| Brier | 0.0339 | [0.0319, 0.0358] |
| Log loss | 0.0939 | [0.0884, 0.0992] |

## Boundary estimates: zero observed errors are not zero risk

At 100% recall, the bootstrap percentile interval is 100%-100% because every sampled group draw also contains only detected critical records. For a group-level success estimand, exact two-sided Clopper-Pearson intervals are more informative: C2 `120/120` groups had every critical record detected (lower bound 96.97%); C4 `120/120` (lower 96.97%); C6 `120/120` (lower 96.97%); and C7 `60/60` (lower 94.04%). Each group event is that all critical records in that group were detected. Scenario-specific intervals avoid pretending that C scenarios are exchangeable.

For the C1/C3/C5 subgroup, 0 of 2927 legitimate documents were false positives, and 0 of 360 independent customer groups had any false-positive record. The pooled one-sided exact 95% upper bound on the **group event incidence** is 0.83%; it is not a document FPR bound. A conservative one-sided Hoeffding bound for equal-group-weighted document FPR is 6.45%. The latter targets an equal-group-weighted rate, not the observed document-weighted ratio. Per-scenario two-sided exact group-event upper bounds are 3.03% at 0/120 groups for C1, C3 and C5.

An iid document-level binomial interval would understate uncertainty because documents from one customer group share case context and generator structure. Therefore no independent-document assumption is used for the primary uncertainty interpretation.

## Paired comparisons

Paired group bootstrap contrasts are in `GENERATOR_C_PAIRED_BASELINE_COMPARISONS.csv`. They are post-unblinding descriptive contrasts, not a new model-selection test. The primary contrast versus semantic rule, for example, gives Hybrid minus rule legitimate FPR -0.0400 with interval [-0.0443, -0.0357]. XGBoost contrasts are absent because the frozen arms were not evaluated.

## Limitations of inference

Finite synthetic scenario frequencies are chosen by construction. Cluster resampling quantifies sampling variation among generated customer groups conditional on those scenario mechanisms; it cannot measure mismatch between synthetic and real financial workflows. Intervals do not account for D1.1 label inconsistency, shared rule/label semantics, or hidden institutional workflows.
