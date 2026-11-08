# E1 Cost–Safety Frontier

**Status:** retrospective V3 synthetic replay; not a new confirmatory test.

The four frozen models were replayed at the thresholds registered in the V3 selection lock. The output includes document-level predictions, case-level workload, model metrics, paired cluster-bootstrap intervals, and a descriptive retrospective threshold sweep.

| Model | Critical recall | Critical FN / support | AP | Brier | Log loss | Case workload |
|---|---:|---:|---:|---:|---:|---:|
| CS V2 | 0.880 | 24 / 200 | 0.4957 | 0.2308 | 0.6529 | 0.8177 |
| Logistic regression | 0.910 | 18 / 200 | 0.9063 | 0.0840 | 0.2763 | 0.7917 |
| XGBoost | 0.905 | 19 / 200 | 0.9828 | 0.0350 | 0.1300 | 0.7083 |
| Deep Sets | 0.910 | 18 / 200 | 0.9269 | 0.0740 | 0.2356 | 0.7656 |

The test contains 192 cases from 96 customer groups and 753 documents (293 material, 200 critical). The frontier sweep was computed only as a retrospective description and was not used to alter thresholds or choose a model.

**Interpretation:** On this previously inspected synthetic test, XGBoost has the lowest observed workload (70.8%) and strongest observed AP (0.9828), while its critical recall is 90.5%. This is conditional evidence within the V3 generator; it does not establish bank performance or safety.

**Outputs:** `E1_RESULTS.json`, `tables/e1_prediction_level.csv`, `tables/model_tradeoff_table.csv`, `tables/e1_frontier_curve.csv`, and the three SVG/PNG figures under `figures/`.
