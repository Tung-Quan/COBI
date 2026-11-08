# E2 Independent Generator Challenge

**Status:** frozen V3 models evaluated on registered, independently generated synthetic cases. Labels are programmatic synthetic gold, not human-reviewed bank truth.

Generator B contains 1920 cases, 960 customer groups, and 7744 documents. Schema compatibility: 7744 documents compatible; 0 incompatible.

## Aggregate results

| Model | Critical recall | Critical FN / support | AP | Brier | Log loss | Case workload |
|---|---:|---:|---:|---:|---:|---:|
| CS V2 | 0.629 | 277 / 747 | 0.1103 | 0.1545 | 0.4861 | 0.6089 |
| Logistic regression | 0.866 | 100 / 747 | 0.2230 | 0.3743 | 2.0268 | 0.6521 |
| XGBoost | 0.628 | 278 / 747 | 0.2015 | 0.3691 | 1.7621 | 0.5464 |
| Deep Sets | 0.807 | 144 / 747 | 0.2870 | 0.3373 | 1.0790 | 0.5932 |

## Scenario results

| Scenario | Model | Cases | Critical recall | Critical FN | AP | Workload |
|---|---|---:|---:|---:|---:|---:|
| B1 | CS V2 | 320 | 0.880 | 14 | 0.1282 | 0.7594 |
| B1 | Logistic regression | 320 | 0.949 | 6 | 0.7363 | 0.9906 |
| B1 | XGBoost | 320 | 0.650 | 41 | 0.4419 | 0.9031 |
| B1 | Deep Sets | 320 | 0.667 | 39 | 0.6128 | 0.7750 |
| B2 | CS V2 | 320 | 0.820 | 31 | 0.2144 | 0.7125 |
| B2 | Logistic regression | 320 | 0.953 | 8 | 0.7575 | 0.9719 |
| B2 | XGBoost | 320 | 0.942 | 10 | 0.3756 | 0.9187 |
| B2 | Deep Sets | 320 | 0.936 | 11 | 0.6428 | 0.9844 |
| B3 | CS V2 | 320 | 0.364 | 91 | 0.1641 | 0.3125 |
| B3 | Logistic regression | 320 | 0.986 | 2 | 0.9798 | 0.3844 |
| B3 | XGBoost | 320 | 0.657 | 49 | 0.9623 | 0.2562 |
| B3 | Deep Sets | 320 | 0.930 | 10 | 0.9700 | 0.3531 |
| B4 | CS V2 | 320 | 0.575 | 34 | 0.0989 | 0.5281 |
| B4 | Logistic regression | 320 | 0.000 | 80 | 0.0802 | 0.0688 |
| B4 | XGBoost | 320 | 0.000 | 80 | 0.1048 | 0.0000 |
| B4 | Deep Sets | 320 | 0.000 | 80 | 0.0915 | 0.0000 |
| B5 | CS V2 | 320 | 0.985 | 1 | 0.0651 | 0.9969 |
| B5 | Logistic regression | 320 | 1.000 | 0 | 0.2253 | 1.0000 |
| B5 | XGBoost | 320 | 0.956 | 3 | 0.1563 | 0.9938 |
| B5 | Deep Sets | 320 | 1.000 | 0 | 0.1588 | 1.0000 |
| B6 | CS V2 | 320 | 0.365 | 106 | 0.1715 | 0.3438 |
| B6 | Logistic regression | 320 | 0.976 | 4 | 0.9742 | 0.4969 |
| B6 | XGBoost | 320 | 0.431 | 95 | 0.9533 | 0.2062 |
| B6 | Deep Sets | 320 | 0.976 | 4 | 0.9676 | 0.4469 |

## Interpretation controls

Generator A metrics are retrospective because the V3 test has already been opened and discussed. Generator B metrics are a new synthetic challenge with a different event-ledger design. Thresholds, model weights, preprocessing and calibration remain frozen. AP is reported with both A/B label prevalences because it is prevalence-sensitive.

**Failure categories:** missed critical defects, false positives on legitimate discrepancies in B5, parsing/schema incompatibility, calibration changes, and performance on the B6 source-combination scenario are itemized in `E2_RESULTS.json`.

**Limitations:** this is not real-bank validation. The scenarios, labels and parameter ranges are synthetic. Intervals condition on fixed model artifacts and thresholds. A low workload can coincide with unacceptable missed-defect performance.

**Outputs:** `E2_RESULTS.json`, `tables/robustness_by_scenario.csv`, and `figures/generator_shift_performance`, `scenario_failure_matrix`, and `generalization_gap` in SVG/PNG formats.
