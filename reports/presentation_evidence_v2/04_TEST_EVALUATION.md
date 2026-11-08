# Locked test evaluation

The release used 4,500 UCI rows and 995 defaults (22.11%). The audit verified the prediction file hash and matched IDs and labels to the locked test. Independent scikit-learn metric calls matched the four published primary point metrics. A replay of the existing evaluation function reproduced all published bootstrap CI endpoints exactly in this environment. [Frozen test report](../final/uci350-v2.0/report.json) · [Audit log](audit.log).

## Model comparison

| Model | ROC-AUC | Average Precision | Brier | Log Loss | Interpretation |
|---|---:|---:|---:|---:|---|
| Dummy train prevalence | 0.500000 | 0.221111 | 0.172221 | 0.528311 | Uninformative ranking. Sets the base rate. |
| Logistic Regression C=0.1 | 0.770987 | 0.552666 | 0.135204 | 0.435403 | Linear reference fitted on train. |
| XGBoost raw | 0.785289 | 0.573823 | 0.132516 | 0.424263 | Strongest proper scores among reported test series. |
| XGBoost sigmoid | 0.785289 | 0.573823 | 0.132663 | 0.424694 | Same ranking. Slightly higher probability error. |

ROC-AUC measures ranking across positive and negative cases. Average precision summarizes precision at recall increments and has a prevalence baseline. It is distinct from trapezoidal PR-AUC. Brier is the mean squared probability error. Log loss is mean binary cross-entropy and penalizes highly confident errors. This is a probability benchmark without a selected operating threshold.

| Model | ROC-AUC 95% CI | AP 95% CI | Brier 95% CI | Log loss 95% CI |
|---|---|---|---|---|
| Dummy train prevalence | [0.500000, 0.500000] | [0.208878, 0.233783] | [0.165400, 0.179286] | [0.512914, 0.544259] |
| Logistic Regression C=0.1 | [0.754411, 0.788283] | [0.520707, 0.584880] | [0.128179, 0.142132] | [0.417310, 0.453528] |
| XGBoost raw | [0.769552, 0.800756] | [0.541508, 0.604907] | [0.125600, 0.139358] | [0.406952, 0.441789] |
| XGBoost sigmoid | [0.769552, 0.800756] | [0.541508, 0.604907] | [0.125817, 0.139375] | [0.407548, 0.442016] |

## Absolute and relative log-loss differences

Signed changes use first model minus reference. Relative change divides by the reference value and multiplies by 100. Negative is better for log loss and Brier. Positive is better for ROC-AUC and AP. Intervals use 1,000 paired percentile draws, seed 43. Rows are sampled once per draw and reused for all series.

| First minus reference | Absolute change | 95% CI | Relative change | Relative 95% CI |
|---|---:|---:|---:|---:|
| Logistic Regression C=0.1 − Dummy train prevalence | -0.092908 | [-0.105803, -0.081017] | -17.586% | [-20.057, -15.321]% |
| XGBoost raw − Dummy train prevalence | -0.104048 | [-0.116601, -0.091862] | -19.694% | [-21.960, -17.508]% |
| XGBoost sigmoid − Dummy train prevalence | -0.103617 | [-0.115850, -0.091808] | -19.613% | [-21.827, -17.497]% |
| XGBoost raw − Logistic Regression C=0.1 | -0.011140 | [-0.015689, -0.006683] | -2.559% | [-3.630, -1.549]% |
| XGBoost sigmoid − Logistic Regression C=0.1 | -0.010709 | [-0.015328, -0.006272] | -2.460% | [-3.499, -1.453]% |
| XGBoost sigmoid − XGBoost raw | 0.000431 | [0.000024, 0.000837] | 0.102% | [0.006, 0.202]% |

The locked protocol prespecified raw XGBoost versus dummy, raw XGBoost versus logistic, and sigmoid versus raw log loss. Use the exact original intervals from `report.json::paired_log_loss` in confirmatory wording. The table reproduces them to the displayed precision. Other pairs, metrics and relative intervals are exploratory and have no multiple-comparison adjustment. [All 24 pair/metric results](test_comparisons.csv).

On this holdout, raw XGBoost has 19.69% lower log loss than dummy and 2.56% lower than LR. Raw XGBoost versus LR also shows exploratory AUC +0.01430 [0.00482, 0.02331], AP +0.02116 [0.00901, 0.03218] and Brier −0.002688 [−0.003827, −0.001519]. The intervals exclude zero under the stated sampling assumptions. They do not estimate retraining variance, performance on other institutions, or independent customer-cluster uncertainty.

**Slide visuals** · [Comparison](figures/test_comparison.svg) · [ROC](figures/roc.svg) · [Precision–recall](figures/precision_recall.svg) · [Reliability](figures/reliability.svg) · [Calibration change](figures/calibration_delta.svg) · [Learning traces](figures/training_performance.svg). Raw and sigmoid ROC/PR traces overlap because they preserve the same order on these arrays.
