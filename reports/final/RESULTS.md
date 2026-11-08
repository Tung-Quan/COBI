# COBI V2 scientific report · public benchmark

**Status** `PUBLIC_DATA_BENCHMARKED` · `BENCHMARK_ONLY`. The evaluation ran 8 November 2026 Vietnam time. The task is next-payment-month default on historical Taiwan credit-card data.

## Provenance and locked cohorts

I-Cheng Yeh, *Default of Credit Card Clients*, UCI Machine Learning Repository, DOI `10.24432/C55S3H`, CC BY 4.0. The original XLS, official CSV and `ucimlrepo` representation agreed after normalization. There are 30,000 unique sample IDs and 6,636 defaults. [Official UCI card](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients) · [Dataset manifest](../../data/manifest/uci350.yaml).

| File | SHA-256 |
|---|---|
| Official ZIP | `56c885f84457f6680f8438f02bfcdac9579323d8a94465ee5f26e32baa727602` |
| Original XLS | `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933` |
| Normalized CSV | `957a8f0c61a409fca9831da6dc9eb38a710503f0a09a19d5725a574f48db5809` |

Stratified random split, seed 42. The four cohorts have no sample-ID overlap. The cohort lock precedes all fits. UCI lacks application dates for an out-of-time evaluation.

| Cohort | Rows | Defaults | Non-defaults | Prevalence |
|---|---:|---:|---:|---:|
| Train | 18,000 | 3,982 | 14,018 | 22.122% |
| Validation | 4,500 | 995 | 3,505 | 22.111% |
| Calibration | 3,000 | 664 | 2,336 | 22.133% |
| Locked test | 4,500 | 995 | 3,505 | 22.111% |

## Validation selection and training history

| Family | Configurations | Best validation log loss | Best in family |
|---|---:|---:|---|
| Train prevalence | 1 | 0.528311 | Train prevalence 0.221222 |
| Logistic Regression | 3 | 0.444747 | L2, C=0.1, LBFGS |
| XGBoost | 4 | **0.432396** | Depth 2, learning rate 0.10, 210 best rounds |
| PyTorch MLP | 3 | 0.435273 | Batch 128, best epoch 7 |

The batch 32, 64 and 128 MLP candidates ran 11, 12 and 13 epochs with 6,193, 3,384 and 1,833 optimizer updates. Their best epochs were 5, 6 and 7 respectively. Batch logs record BCE, pre-clip gradient L2, learning rate, actual batch size and seed. Candidate metadata records hyperparameters, epoch or round history and checkpoint hashes. The selected model, preprocessing and sigmoid with intercept −0.048071 and slope 0.962952 were frozen before the test opened. [Training log](training.log) · [Candidate metadata](uci350-v2.0/candidates.json) · [Training curves](uci350-v2.0/training.svg) · [Selection freeze](uci350-v2.0/selection.json).

## Locked test

| Prediction series | ROC-AUC | Avg. precision | Brier | Log loss |
|---|---:|---:|---:|---:|
| Train prevalence | 0.5000 | 0.2211 | 0.172221 | 0.528311 |
| Logistic Regression | 0.7710 | 0.5527 | 0.135204 | 0.435403 |
| XGBoost raw | 0.7853 | 0.5738 | 0.132516 | 0.424263 |
| XGBoost sigmoid | 0.7853 | 0.5738 | 0.132663 | 0.424694 |

| Calibrated metric | Estimate | 95% bootstrap CI |
|---|---:|---:|
| ROC-AUC | 0.785289 | [0.769552, 0.800756] |
| Average precision | 0.573823 | [0.541508, 0.604907] |
| Brier | 0.132663 | [0.125817, 0.139375] |
| Log loss | 0.424694 | [0.407548, 0.442016] |
| Default prevalence | 0.221111 | [0.208878, 0.233783] |
| Expected defaults | 973.97 | [948.88, 999.36] |
| Observed defaults | 995 | [939.95, 1052.03] |
| Observed minus expected | 21.03 | [−27.72, 68.89] |
| Expected / observed | 0.978864 | [0.933686, 1.029662] |
| Calibration intercept | 0.144319 | [0.022163, 0.257561] |
| Calibration slope | 1.094705 | [1.020849, 1.175246] |

| Prespecified difference in log loss | Delta | Paired 95% CI |
|---|---:|---:|
| XGBoost raw − train prevalence | −0.104048 | [−0.116601, −0.091862] |
| XGBoost raw − Logistic Regression | −0.011140 | [−0.015689, −0.006683] |
| XGBoost sigmoid − XGBoost raw | +0.000431 | [+0.000024, +0.000837] |

XGBoost had lower log loss than train prevalence and Logistic Regression. Sigmoid calibration slightly worsened probability error while preserving the ranking. The intervals are conditional on the fitted models and row independence. 127 test rows share an exact predictor vector with training. Customer-level linkage is unavailable. The full report includes all series' intervals, reliability bins with counts, drift diagnostics and paired estimates. [Machine-readable report](uci350-v2.0/report.json) · [Reliability](uci350-v2.0/reliability.svg) · [Test log-loss plot](uci350-v2.0/experiment-results.svg).

## Workbench experiments and verification

E0 tests deterministic calculations and guardrails. E4 is `UNVALIDATED_EVIDENCE_SCORE` because independently adjudicated defect labels are unavailable. E5 evaluated six synthetic cases under 18 combinations of DTI, residual buffer and assumed fast-track cost. The constrained policy chose the least-cost feasible route. Nine combinations had an assumed 68,000 VND total difference versus fixed eligible routing. The other nine had zero. These are results of the specified cost assumptions. E6 is `BANK_EXTERNAL_VALIDATION_BLOCKED`. [Route sensitivity](route-sensitivity.json) · [Limitations](../../docs/LIMITATIONS.md).

Validation predictions match across two clean API process starts. Mismatched checkout features are refused. Workbench scenarios calculate a separately labeled synthetic score and cost estimate. The registry remains pending independent model-risk and fairness review. [Model manifest](uci350-v2.0/model/model_manifest.json) · [API restart check](restart.log).

| Verification | Result |
|---|---|
| Baseline backend / frontend | [17 tests](../baseline/backend.log), [build passed](../baseline/frontend.log) |
| V2 numerical, unit, API, data and registry tests | [36 passed](verification.log) |
| Production frontend build | [Passed](frontend.log) |
| Chrome desktop and mobile user journey | [Passed](e2e.log) |
| Existing database startup on a read-only backup of the original | [Six original applications preserved](migration.log) |
| Docker Compose | Configuration validated. Image build stalled in package installation; container startup unverified. [Build log](docker-build.log) |
