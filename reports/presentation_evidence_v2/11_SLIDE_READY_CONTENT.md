# Slide-ready English copy

Keep the original ten-slide narrative and navigation strip. Page 11 of the source is a concept poster with legacy rules. The A1–A8 material below is separate backup. Replace the body of slides 5–10 using the specified evidence. [Original deck](<C:/Users/tungq/Downloads/AI4Biz_Adudu_2026.pdf>).

## 1. Checkout Credit Copilot

**Takeaway** · An officer workspace for small checkout loans.

**Slide copy**

Checkout Credit Copilot gives bank officers a structured place to review small checkout loans. The prototype shows the available evidence, the repayment capacity calculation and a suggested review path. A separate research workspace evaluates historical default predictions under a documented protocol.

**Visual and values** · Keep the original 2026 cover and ISBKU team panel. Populate team member names from the approved team list. **Source** · Original PDF p. 1, Title and Team.

## 2. Checkout Lending in the Supplied HLBVN Case

**Takeaway** · The case reports delays and costs that matter for small loans.

**Slide copy**

The supplied HLBVN case reports 1.8–4.6 business days to a decision and VND 380,000 in processing cost per application. Separate submission, verification and underwriting steps interrupt the checkout journey. These figures describe the supplied case and need a verified baseline before a pilot.

**Visual and values** · Two big figures, 1.8–4.6 days and VND 380,000/application. **Source** · Original PDF p. 2, Decision Speed and Processing Cost.

## 3. Retail Banks and Merchant Checkout Partners

**Takeaway** · The bank owns the process and officers use the workbench.

**Slide copy**

Bank lending and risk teams would sponsor the workbench. Credit officers would use it to assess evidence and record review actions. Merchant staff and checkout applicants would benefit from a clearer handoff if a later pilot verifies the integration and its operational effects.

**Visual and values** · Retain four stakeholder groups. Put bank sponsor and officers above merchants and shoppers. **Source** · Original PDF p. 3, Target Business & Users.

## 4. The Document-to-Decision Bottleneck

**Takeaway** · The case diagnosis focuses on evidence preparation and repeated review.

**Slide copy**

The original case analysis identifies fragmented documents, disconnected records and repeated manual review as sources of delay. COBI organizes the available evidence in a single case and lets officers see which checks remain open. Pilot data will be needed to test the effect on review effort.

**Visual and values** · Keep the case bottleneck diagram. Operational effect `NOT_MEASURED`. **Source** · Original PDF p. 4, Business Insight. [Business evidence](09_BUSINESS_IMPACT_AND_LIMITATIONS.md).

## 5. Proposed Solution

**Takeaway** · Workbench and Research Lab have separate input contracts and purposes.

**Slide copy**

The Credit Review Workbench runs evidence checks, calculates affordability and proposes an eligible review path. The officer records the action and reason. Research Lab trains and evaluates next-month default models on UCI credit-card data. Its model contract prevents these probabilities from entering checkout assessment or routing.

**Visual and values** · [Two-lane architecture](figures/architecture.svg). Two modes, `BENCHMARK_ONLY` and `PD_UNAVAILABLE_SCHEMA_MISMATCH`. **Source** · `frontend/src/App.tsx` navigation, `backend/app/main.py::simulate` and `ml/predict.py::predict`.

## 6. How AI Helps

**Takeaway** · The trained model supports a public research task.

**Slide copy**

Research Lab compared eleven configurations across a constant baseline, logistic regression, XGBoost and a neural network. The pipeline transforms 19 predictors into 85 inputs and selects models by validation log loss. XGBoost led this comparison at 0.432396. Checkout review uses deterministic calculations and rules.

**Visual and values** · Left [cohort pipeline](figures/dataset_processing.svg), right [validation chart](figures/validation_performance.svg). 11 configurations, 19 → 85, 0.432396. **Source** · `ml/preprocessing.py::transform`, `selection.json::selected,validation_log_loss`.

## 7. How It Works

**Takeaway** · A case must clear the policy gates before scoring or routing.

**Slide copy**

Consent, simulated identity, source permission, funding and evidence checks gate assessment. Passing cases receive evidence and affordability calculations. Routing compares costs only among eligible paths. A failed gate sends the case to hold and suppresses scoring. A credit officer records the review action and reason.

**Visual and values** · [P1–P9 flow](figures/workbench_flow.svg) with HOLD callout. Replace legacy PD thresholds. Fast-track CS ≥0.75 with affordable, reconciled terms. Enhanced-only CS <0.50. **Source** · `backend/app/calculations.py::_mandatory_gates,route_application`, `backend/app/main.py::_record_review`.

## 8. MVP Demo

**Takeaway** · The current DEMO-001 traces the monthly payment to usable capacity.

**Slide copy**

DEMO-001 combines VND 5 million in principal with VND 1 million in own funds. At zero interest over four months, payment is VND 1.25 million per month against VND 2.91 million in usable capacity. Evidence confidence is 0.821. Fast-track is an officer review option.

**Visual and values** · Crop the affordability section of the [actual screen](figures/demo_001_workbench.png) beside the [capacity chart](figures/demo_001_trace.svg). VND 6m purchase, 1.25m payment, 2,906,250 capacity, 1,656,250 headroom. **Source** · `backend/data/demo_001_v2.json`, `audit_summary.json::workbench.assessment.affordability`. [Full trace](08_MVP_MATHEMATICAL_TRACE.md).

## 9. Feasibility and Business Value

**Takeaway** · The prototype and UCI benchmark are verified. Bank impact requires a pilot.

**Slide copy**

The synthetic workbench passed browser and automated checks. On 4,500 historical UCI test records, XGBoost reached ROC-AUC 0.785 with a 95% interval of 0.770–0.801. A bank-approved pilot must measure processing cost, decision time, checkout conversion, credit loss and officer workload.

**Visual and values** · [Test comparison](figures/test_comparison.svg) above prototype, bank validation and pilot stages. Test n=4,500, 995 defaults, AUC 0.7853 [0.7696, 0.8008]. Impact `NOT_MEASURED`. **Source** · `report.json::split.cohorts.test,models.selected_calibrated.metrics.roc_auc`, original PDF p. 9.

## 10. Competitive Advantage

**Takeaway** · The demonstrated distinction is traceability within the supplied case workflow.

**Slide copy**

Officers can inspect the source evidence, affordability formula and reason for each review path in one case. The audit records the input digest, policy version, model version and reviewer reason. Research results remain linked to a specific dataset and model artifact. Lending decisions remain with the bank.

**Visual and values** · Supplied workflow versus V2 controls, beside [officer audit](figures/officer_audit.png). Policy `cobi-checkout-policy-v2.0`, model `BENCHMARK_ONLY`. **Source** · Original PDF p. 10, `backend/app/main.py::_audit_trace`, `backend/app/db.py::append_audit_event`.

## A1. Data and Dataset Selection

**Takeaway** · The holdout measures performance within historical Taiwanese credit-card data.

**Slide copy**

UCI 350 contains 30,000 Taiwanese credit-card records and 6,636 next-month defaults. The benchmark uses 19 source predictors and a stratified random split with seed 42. A separate cohort fits calibration. The data provide no reliable application chronology or customer grouping for out-of-time testing.

**Visual and values** · [Class balance](figures/class_distribution.svg) and [split and transformation](figures/dataset_processing.svg). 22.12% default, 60/15/10/15, 13 numeric + 72 indicators. **Source** · `data/manifest/uci350.yaml::label_counts,snapshot,feature_allowlist` and `report.json::split`.

## A2. Mathematical Methods

**Takeaway** · Log loss scores probabilities, while tree regularization constrains the fit.

**Slide copy**

Logistic boosting adds small trees to the predicted log odds. Each tree follows the loss gradient and curvature, with penalties on tree structure and leaf weights. Log loss scores the resulting probabilities and penalizes confident errors. The benchmark fits a sigmoid on a separate calibration cohort.

**Visual and values** · Editable loss and regularizer equations from [training methods](03_TRAINING_AND_MODEL_SELECTION.md). λ=1, γ=0, η=0.10, depth 2. **Source** · `candidates.json::parameters` and `ml/evaluation.py::calibrate`. [Chen and Guestrin](https://arxiv.org/abs/1603.02754).

## A3. Training and Hyperparameter Tuning

**Takeaway** · Training inspected 230 rounds and exported the best 210.

**Slide copy**

Validation log loss selects the candidate and its stopping point. The winning XGBoost reached its best at round 210, then ran 20 additional rounds under the stopping rule. The exported model contains 210 trees. Logistic regression uses full-batch LBFGS. The neural network alone uses minibatches.

**Visual and values** · [Train/validation traces](figures/training_performance.svg). 210/230, MLP batches 32/64/128, family margin >0.001. **Source** · `candidates.json::history,parameters.resolved_config`, `audit_summary.json::parity`.

## A4. Test Results and Statistical Confidence

**Takeaway** · The selected tree model improves log loss over both baselines on this holdout.

**Slide copy**

On the locked UCI test, XGBoost achieved ROC-AUC 0.7853 and average precision 0.5738. The raw model’s log loss was 0.01114 lower than logistic regression. The paired 95% interval spans −0.01569 to −0.00668. These estimates describe this sample and its next-month outcome.

**Visual and values** · [Test comparison](figures/test_comparison.svg), with [ROC](figures/roc.svg) and [PR](figures/precision_recall.svg) as backup. 4,500 rows, 995 defaults, 1,000 draws. **Source** · `report.json::models,bootstrap,paired_log_loss`.

## A5. Probability Calibration and Limitations

**Takeaway** · The fitted sigmoid slightly worsened test log loss.

**Slide copy**

The sigmoid fit used a separate cohort and preserved XGBoost’s ranking. On the test set, log loss increased from 0.424263 to 0.424694. About 2.82% of test rows share an exact predictor vector with training. The sensitivity check describes this overlap without changing the frozen result.

**Visual and values** · [Reliability](figures/reliability.svg) beside [paired change](figures/calibration_delta.svg). +0.000431 [0.000024, 0.000837], 127/4,500. **Source** · `report.json::paired_log_loss,data_diagnostics`, `audit_summary.json::duplicates`.

## A6. Explainability and Fairness

**Takeaway** · Attribution describes what the model uses. Fairness needs separate evaluation.

**Slide copy**

TreeSHAP on the validation cohort attributes the fitted model’s raw log odds to its inputs. September repayment status has the largest mean absolute contribution. The model excludes four demographic predictors. Correlated features may still act as proxies, and subgroup error and calibration remain unmeasured.

**Visual and values** · [Grouped importance](figures/feature_importance.svg) and [SHAP distributions](figures/shap_summary.svg). 4,500 validation rows, 19 source features, `PAY_0` first. **Source** · `audit_summary.json::explainability.mean_abs_grouped_shap`, `ml/contracts.py::DEMOGRAPHICS`.

## A7. Business Model and Future Validation

**Takeaway** · The bank pilot needs a comparator, mature outcomes and human oversight.

**Slide copy**

A bank sponsor would first validate the workflow in shadow mode, then compare assisted and usual review in a controlled pilot. The study would measure decision time, processing cost and conversion alongside mature repayment losses and officer workload. All five impact measures currently remain unmeasured.

**Visual and values** · [Pilot stages](figures/pilot_measurement.svg). Five KPIs `NOT_MEASURED`, `BANK_EXTERNAL_VALIDATION_BLOCKED`. **Source** · `docs/LIMITATIONS.md`, `data/manifest/restricted-sources.yaml::BANK_PARTNER`.

## A8. Academic References

**Takeaway** · The literature supports methods and evaluation safeguards.

**Slide copy**

Credit-scoring benchmarks motivate model comparison. Calibration studies motivate probability checks on separate data. Data quality and learning-to-defer research support visible evidence and officer review. Profit-sensitive evaluation and selective-label studies define what the bank pilot must measure before COBI can claim business value.

**Visual and values** · Editable paper-to-component table. Lessmann 2015, Niculescu-Mizil and Caruana 2005, Wang and Strong 1996, Verbraken 2014, Mozannar and Sontag 2020, Lakkaraju 2017, Kozodoi 2025. **Source** · [Verified references and limits](10_LITERATURE_REVIEW.md).
