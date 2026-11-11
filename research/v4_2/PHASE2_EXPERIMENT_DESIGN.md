# Phase 2 Experiment Design

**State:** preregistration-ready draft; no experiment run, no winner selected, no labels accessed.

## Registered model families

| Candidate | Observable features | Training/selection | Calibration |
|---|---|---|---|
| Semantic rules baseline | identity, field/basis, units, periods, valid/recorded/source times, supersession and source state under approved rules | Freeze deterministic rule versions from policy before test access; no fitted parameters | None unless it produces probabilities; report deterministic coverage/errors |
| Logistic Regression | predeclared sparse/normalized semantic, temporal and provenance features | Fit only training; select regularization on validation with group-safe folds | Dedicated calibration split; fit method prespecified |
| XGBoost | same permitted observable structured features, no generator/label access markers | Training only; bounded search predeclared on validation; freeze configuration | Dedicated calibration split |
| Deep Sets | claim/record embeddings plus explicit missingness, time and provenance features | Training only with group-aware validation; fixed architecture/search budget | Dedicated calibration split |
| Semantic Hybrid | frozen rule outputs plus structured model scores/features; no gold-derived inference | Train/validate under same splits; ablation and thresholds frozen | Dedicated calibration split |
| Selective review policy | calibrated task-specific risks and explicit uncertainty/eligibility indicators | Select action threshold/policy on calibration only against approved epsilon and costs | Report UCB feasibility on sealed groups; no feasible point means no certified operating point |

All exact features, hyperparameter spaces, seeds, transformations, candidate count and selection tie-breakers remain to be finalized and hashed before opening locked labels. No candidate is declared the winner in this draft. Generator C is not a candidate-selection dataset.

## Evaluation flow

1. Independently construct dataset and annotation gold; reserve group-held-out locked test before model development.
2. Train candidate families on training groups; select only from validation using frozen primary comparison and Holm-controlled multiplicity.
3. Fit probability calibration/action threshold only on the calibration groups.
4. Freeze candidate, code, environment, threshold and analysis hashes; lock test labels and obtain independent timestamped preregistration.
5. Evaluate once on locked ID and planned OOD/shift groups; report pair, document, case, calibration, trace and abstention endpoints with support and group-aware intervals.
6. Report all failures, missingness, policy deviations and model families; no unregistered winner search on locked test.

## Primary estimands and analysis

Primary endpoint, effect size, risk epsilon and target population are unresolved dependencies. The final registration must choose one primary endpoint per RQ, define paired group resampling (>=2,000 replicates proposed), independent-group exact intervals where valid, one-sided risk UCB, Holm family, missing-label handling, unresolved attribution handling, and a practical effect threshold. See `METRIC_SPECIFICATION.md`, `STATISTICAL_ANALYSIS_PLAN.md` and `SAMPLE_SIZE_AND_POWER_PLAN.md`.
