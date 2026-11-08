# E3 Business Cost Sensitivity

**Interpretation: scenario-based economic feasibility, not realized operational savings.**

Measured inputs are frozen V3 synthetic case-workload and critical false-negative rates. Review costs, missed-error costs, inference costs, fixed costs, and application volumes are assumptions in `config/cost_scenarios.yaml`; they are not bank quotations.

## Cost equation

`Total cost = flagged cases × review cost + missed critical evidence documents × missed-document cost + inference cost + fixed operating cost`.

Review is charged per flagged case. Missed-error cost is charged per false-negative critical evidence document. The units differ and are not combined into one count.

## Sampling variability and assumptions

The report gives customer-cluster bootstrap distributions while holding each cost scenario fixed. Differences across cost assumptions are scenario sensitivity, not confidence intervals. The sample bootstrap conditions on the frozen models and thresholds.

| Model | Cases flagged / case | Critical FN / case |
|---|---:|---:|
| CS V2 | 0.8177 | 0.1250 |
| Logistic regression | 0.7917 | 0.0938 |
| XGBoost | 0.7083 | 0.0990 |
| Deep Sets | 0.7656 | 0.0938 |

The scenario table contains 84 model-volume-assumption rows. See `tables/business_scenarios.csv`, `E3_COST_RESULTS.json`, and the sensitivity and break-even figures.

No projected difference is a measured bank saving. The workbench's existing route-cost assumptions were not reused as document-verification costs.
