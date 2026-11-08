# Model card · uci350-v2.0-selected

| Attribute | Value |
|---|---|
| Status | `BENCHMARK_ONLY` · `PUBLIC_DATA_BENCHMARKED` |
| Independent model-risk review | `PENDING_INDEPENDENT_REVIEW` |
| Model | XGBoost binary logistic, depth 2, learning rate 0.10, 210 rounds selected on validation |
| Calibration | Separate sigmoid on held calibration data. Slope 0.962952, intercept −0.048071 |
| Outcome | Published next-payment-month default label, Taiwan credit-card customers, history April–September 2005 |
| Intended use | Reproduce the public historical benchmark and compare probability metrics |
| Prohibited use | Checkout routing, real credit decisions, extrapolation to Vietnamese applicants or another outcome horizon |
| Approved inputs | 19 UCI features only. Exact source, horizon, signature, integer bounds and feature names required. |
| Registry | [Model manifest and hashes](../reports/final/uci350-v2.0/model/model_manifest.json) |
| Evidence | [Results, confidence intervals and diagnostics](../reports/final/RESULTS.md) |

The bundle contains native XGBoost JSON, JSON preprocessing state, JSON calibration and a checksummed manifest. Candidate checkpoints are retained for the research record. MLP checkpoints contain PyTorch tensor state only and are loaded with `weights_only=True`. The API reads artifacts only from trusted local directories. Artifact hashes detect modification of released components. They do not authenticate a publisher when someone replaces the manifest and all components together.

Research API returns `PUBLIC_BENCHMARK_ONLY` on successful compatible inference. Model metadata, evaluation and artifact access are isolated from the synthetic checkout calculation module. Checkout PD and actual expected loss are unavailable. Approval status can only follow documented external governance, which has not occurred.

The sigmoid raises held-out log loss by 0.000431 compared with raw probabilities. The final report retains both series and the prespecified calibrator for reproducibility. Test results did not change model selection or calibration.
