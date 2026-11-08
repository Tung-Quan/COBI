# Experiment Protocol Amendment 2 — XGBoost Runtime Blocker

- Protocol: `cobi-evidence-v4.1-c1.0`
- Date: 2026-11-08
- Status: registered before Generator C creation and label opening; development training and locked D test have already run.
- Reason: the execution environment lacks the preregistered `xgboost==3.0.5` package. The local package cache has no wheel, and package-index access fails because DNS/network access is unavailable. No XGBoost implementation or score is being substituted under the XGBoost name.

## Impact and handling

The preregistered model list remains unchanged. Semantic XGBoost and the frozen V3 XGBoost replay are recorded as `BLOCKED_DEPENDENCY`; their metrics are unavailable. Feasible arms continue to be reported: frozen CS_V2, frozen V3 Logistic Regression and Deep Sets, semantic rule, semantic Logistic Regression, semantic Deep Sets, semantic hybrid, and the three preregistered Logistic Regression feature ablations.

Generator C may be generated and evaluated only after the available model set has been frozen. The registered acceptance criterion comparing the hybrid against the best complete frozen baseline is **not assessable** while a registered XGBoost baseline cannot be replayed. C results for the available subset will be labeled partial, and no criterion will be relaxed or redefined. No model selection, threshold, seed, split, scenario, sample-size, metric, or acceptance threshold is changed by this amendment.

No Generator C data or labels had been generated or opened when this amendment was recorded. The D locked test had been evaluated as part of development-only selection diagnostics; it was not used to tune models or thresholds. Generator C remains the only independent challenge.

## Required audit note

The release manifest must list the unavailable model arms and the import error. C prediction/evaluation artifacts must include a model-availability table and must omit unrun scores rather than fabricate values. Final status remains `EVIDENCE_AI_VALIDATION_BLOCKED`.
