# E2 Independent Generator Challenge

**Status:** frozen V3 models evaluated on registered, independently generated synthetic cases. Labels are programmatic synthetic gold, not human-reviewed bank truth.

Generator B contains 1920 cases, 960 customer groups, and 7744 documents. Schema compatibility: 7744 documents compatible; 0 incompatible.

## Aggregate results

| Model | Critical recall | Critical FN / support | AP | Brier | Log loss | Case workload |
|---|---:|---:|---:|---:|---:|---:|
| CS V2 | 0.629 | 277 / 747 | 0.1103 | 0.1545 | 0.4861 | 0.6089 |
| Logistic regression | 0.871 | 96 / 747 | 0.2346 | 0.3927 | 2.0993 | 0.6583 |
| XGBoost | 0.648 | 263 / 747 | 0.2343 | 0.3662 | 1.6851 | 0.5479 |
| Deep Sets | 0.850 | 112 / 747 | 0.2835 | 0.3273 | 1.0152 | 0.6198 |

## Scenario results

| Scenario | Model | Cases | Critical recall | Critical FN | AP | Workload |
|---|---|---:|---:|---:|---:|---:|
| B1 | CS V2 | 320 | 0.880 | 14 | 0.1282 | 0.7594 |
| B1 | Logistic regression | 320 | 0.966 | 4 | 0.7372 | 1.0000 |
| B1 | XGBoost | 320 | 0.735 | 31 | 0.4219 | 0.9125 |
| B1 | Deep Sets | 320 | 0.932 | 8 | 0.6278 | 0.9844 |
| B2 | CS V2 | 320 | 0.820 | 31 | 0.2144 | 0.7125 |
| B2 | Logistic regression | 320 | 0.965 | 6 | 0.7761 | 0.9688 |
| B2 | XGBoost | 320 | 0.942 | 10 | 0.6363 | 0.9031 |
| B2 | Deep Sets | 320 | 0.936 | 11 | 0.7165 | 0.9469 |
| B3 | CS V2 | 320 | 0.364 | 91 | 0.1641 | 0.3125 |
| B3 | Logistic regression | 320 | 0.986 | 2 | 0.9806 | 0.4125 |
| B3 | XGBoost | 320 | 0.671 | 47 | 0.9448 | 0.2625 |
| B3 | Deep Sets | 320 | 0.979 | 3 | 0.9705 | 0.3719 |
| B4 | CS V2 | 320 | 0.575 | 34 | 0.0989 | 0.5281 |
| B4 | Logistic regression | 320 | 0.000 | 80 | 0.0742 | 0.1469 |
| B4 | XGBoost | 320 | 0.000 | 80 | 0.1255 | 0.0000 |
| B4 | Deep Sets | 320 | 0.000 | 80 | 0.2272 | 0.0000 |
| B5 | CS V2 | 320 | 0.985 | 1 | 0.0651 | 0.9969 |
| B5 | Logistic regression | 320 | 1.000 | 0 | 0.2260 | 1.0000 |
| B5 | XGBoost | 320 | 0.971 | 2 | 0.1938 | 0.9938 |
| B5 | Deep Sets | 320 | 0.985 | 1 | 0.1162 | 1.0000 |
| B6 | CS V2 | 320 | 0.365 | 106 | 0.1715 | 0.3438 |
| B6 | Logistic regression | 320 | 0.976 | 4 | 0.9749 | 0.4219 |
| B6 | XGBoost | 320 | 0.443 | 93 | 0.9543 | 0.2156 |
| B6 | Deep Sets | 320 | 0.946 | 9 | 0.9651 | 0.4156 |

## Interpretation controls

Generator A metrics are retrospective because the V3 test has already been opened and discussed. Generator B metrics are a new synthetic challenge with a different event-ledger design. Thresholds, model weights, preprocessing and calibration remain frozen. AP is reported with both A/B label prevalences because it is prevalence-sensitive.

**Failure categories:** missed critical defects, false positives on legitimate discrepancies in B5, parsing/schema incompatibility, calibration changes, and performance on the B6 source-combination scenario are itemized in `E2_RESULTS.json`.

**Limitations:** this is not real-bank validation. The scenarios, labels and parameter ranges are synthetic. Intervals condition on fixed model artifacts and thresholds. A low workload can coincide with unacceptable missed-defect performance.

**Outputs:** `E2_RESULTS.json`, `tables/robustness_by_scenario.csv`, and `figures/generator_shift_performance`, `scenario_failure_matrix`, and `generalization_gap` in SVG/PNG formats.
