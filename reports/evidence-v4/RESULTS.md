# COBI Evidence AI V4 — Results

## Scope and disposition

V4 is a technical research evaluation of document evidence defect detection. It does not estimate default risk and does not make or recommend credit decisions. The three learned models and the CS V2 rules baseline remain frozen; V4 trained no model, changed no calibration, and selected no threshold. The bank-validation gate remains **`EVIDENCE_AI_VALIDATION_BLOCKED`**.

## E1 — V3 cost and safety replay

E1 replays the previously inspected V3 synthetic test: 192 cases, 96 customer groups, 753 documents, 293 material defects, and 200 critical defects. Thresholds came from the V3 selection lock. This is retrospective evidence, not a new confirmatory test.

## E2 — independent synthetic challenge

Generator B v1.1 uses an event-ledger implementation independent of the V3 generator. It produced 1,920 cases, 960 customer groups and 7,744 documents in six registered scenarios. All documents passed the frozen input schema (0 incompatible). Gold labels are programmatic synthetic labels, not human-reviewed banking truth. The first pilot was invalidated before confirmatory analysis because model-visible text exposed event meaning; the correction and pre-confirmatory amendment are preserved in the archive.

| Model | E1 critical recall (FN/support) | E1 case workload | E1 AP | E2 critical recall (FN/support) | E2 case workload | E2 AP |
|---|---:|---:|---:|---:|---:|---:|
| CS V2 | 0.880 (24/200) | 0.818 | 0.4957 | 0.629 (277/747) | 0.609 | 0.1103 |
| Logistic regression | 0.910 (18/200) | 0.792 | 0.9063 | 0.866 (100/747) | 0.652 | 0.2230 |
| XGBoost | 0.905 (19/200) | 0.708 | 0.9828 | 0.628 (278/747) | 0.546 | 0.2015 |
| Deep Sets | 0.910 (18/200) | 0.766 | 0.9269 | 0.807 (144/747) | 0.593 | 0.2870 |

The sharp decline in average precision and, for several models, critical recall is evidence that the V3 advantage does not transfer consistently to this independent synthetic generator. In B4, logistic regression, XGBoost and Deep Sets detected none of 80 critical stale-as-current cases at their unchanged thresholds. In B6, the heuristic and XGBoost missed 106/167 and 95/167 critical defects respectively. These are scenario-conditioned outcomes, not estimates of bank prevalence.

### Legitimate-discrepancy stress test (B5)

| Model | Legitimate documents flagged / support | False-positive rate |
|---|---:|---:|
| CS V2 | 1198/1199 | 99.9% |
| Logistic regression | 1192/1199 | 99.4% |
| XGBoost | 1145/1199 | 95.5% |
| Deep Sets | 1174/1199 | 97.9% |

The B5 result is a serious failure mode: all frozen models flagged most legitimate document-level differences. High critical recall by itself is not sufficient evidence of a safe review policy.

### Descriptive A/B gaps

| Model | AP A − B | Critical recall A − B | Log loss B − A |
|---|---:|---:|---:|
| CS V2 | 0.385 | 0.251 | -0.167 |
| Logistic regression | 0.683 | 0.044 | 1.750 |
| XGBoost | 0.781 | 0.277 | 1.632 |
| Deep Sets | 0.640 | 0.103 | 0.843 |

Generator A and B have different prevalences; average precision is prevalence-sensitive. The gaps are descriptive comparisons between two fixed synthetic datasets. Intervals use independent customer-group resampling and are conditional on the frozen models and thresholds.

## E3 — illustrative costs

At 10,000 applications, with assumed review cost of VND 100,000 per flagged case and assumed missed-critical-document cost of VND 500,000, the simulated totals are:

| Model | Simulated total (VND billions) | Difference vs CS V2 (VND millions) |
|---|---:|---:|
| CS V2 | 1.443 | 0.0 |
| Logistic regression | 1.273 | 169.3 |
| XGBoost | 1.216 | 226.6 |
| Deep Sets | 1.247 | 195.3 |

These figures combine E1 synthetic rates with configurable assumptions, including VND 300 per inference and VND 10 million fixed learned-model cost. They are scenario calculations, not bank quotations, measured savings, or evidence that a model is economically deployable. E2's shift and false-positive failures further limit their use.

## Statistical and integrity checks

- 109 protected V2/V3 artifacts verified against the immutable baseline manifest; no mismatch found.
- V3 train, validation, calibration and test sets have disjoint customer groups; E1 metric replay matched the frozen report.
- E2 counts, file hashes, observed/gold separation, exact input schema and no-refit policy were checked.
- Intervals use 300 customer-cluster bootstrap draws (registered seeds); they describe sampling variability in these finite synthetic datasets and do not guarantee future performance.
- Full statistical detail: `STATISTICAL_AUDIT.md` and `statistical_audit.json`.

## Interpretation

The defensible result is a generalization warning. The V3 test made the models appear strong, while the independently generated cases exposed severe weaknesses in stale evidence and legitimate discrepancies. The next research step is to build a human-reviewed, privacy-governed benchmark and pre-register recalibration or model redesign against realistic cases. Until then, keep the model in research-only shadow mode and leave all production decisions to the existing rules and human process.

## Reproducibility and files

See `EXPERIMENT_PROTOCOL.md`, `EXPERIMENT_PROTOCOL_AMENDMENT_1.md`, `ARTIFACT_MANIFEST.json`, `final_manifest.json`, and the prediction-level CSVs. The final manifest hashes the V4 deliverables and the linked implementation files.
