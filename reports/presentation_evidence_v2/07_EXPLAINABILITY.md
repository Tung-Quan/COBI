# Interpretation of the persisted XGBoost model

TreeSHAP was computed from the 210-tree registry model on **all 4,500 validation rows** using native `Booster.predict(pred_contribs=True)`. It returns 85 encoded contributions and a bias term on the raw log-odds scale. The 12 one-hot contributions of each repayment field were summed within a record, then we computed the mean absolute value per source feature. This grouping preserves local additivity and does not claim a separate group-Shapley game. Summed contributions plus bias reconstructed raw margins with maximum absolute error **2.86×10⁻⁶**. [Official native prediction semantics](https://xgboost.readthedocs.io/en/release_3.0.0/prediction.html) · [Attribution values](audit_summary.json).

| Rank | Source field | Meaning | Mean absolute grouped TreeSHAP |
|---:|---|---|---:|
| 1 | `PAY_0` | September 2005 repayment status | 0.401654 |
| 2 | `LIMIT_BAL` | Credit limit including supplementary credit | 0.189523 |
| 3 | `PAY_AMT2` | August 2005 prior payment amount | 0.132829 |
| 4 | `PAY_2` | August 2005 repayment status | 0.115382 |
| 5 | `PAY_AMT1` | September 2005 prior payment amount | 0.112739 |

The full nineteen-feature ranking and encoded split gain are in `audit_summary.json::explainability`. Split gain describes average split improvement per used encoded feature. Grouped TreeSHAP describes the size of model-output contributions over the chosen validation cohort. These quantities need not order features alike.

## Two validation explanations

We selected the smallest and largest `PAY_0` attributions from sorted validation rows. These examples illustrate the model at its attribution extremes. No raw identifiers are exported.

| Validation ordinal | September code | Bias (log odds) | `PAY_0` contribution | Other feature contributions combined | Final margin | Raw probability |
|---:|---:|---:|---:|---:|---:|---:|
| 271 | −2, undocumented | −1.273632 | −0.470673 | −0.889527 | −2.633832 | 6.6993% |
| 1,740 | 2, recorded two-month delay category | −1.273632 | +1.976903 | −0.585708 | +0.117563 | 52.9357% |

The response plot substitutes an observed `PAY_0` category across all validation records and averages predictions while holding remaining inputs fixed. For code 0, 2 and 3 the resulting averages are 16.69%, 56.41% and 33.65%. The model uses categorical splits and has no monotonicity constraint. Observed support differs sharply across codes. Recombining repayment history can create implausible joint records, so the plot describes model response under a constructed input, with no causal or policy implication. [Feature response](figures/pay_0_response.svg).

TreeSHAP allocates a model output among correlated transformed inputs. It does not identify what would change default in the real world. The 2005 category definitions and NTD amount semantics remain specific to UCI. Excluding `SEX, EDUCATION, MARRIAGE, AGE` removes direct predictors but leaves proxy effects, differential error, selection and subgroup calibration unmeasured. A bank study requires authorized subgroup data, sufficient group event counts, and a prespecified risk and fairness review. [Source feature contract](../../ml/contracts.py) · [Fairness references](10_LITERATURE_REVIEW.md).

**Visuals** · [Global importance](figures/feature_importance.svg) · [TreeSHAP distribution](figures/shap_summary.svg) · [Feature response](figures/pay_0_response.svg).
