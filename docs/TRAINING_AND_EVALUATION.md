# Training and evaluation · UCI 350

The research question is which prespecified candidate best predicts next-month default on the historical UCI Taiwan credit-card task. H1 predicts that a trained candidate improves unweighted log loss over train prevalence. The calibration ablation tests whether a held-out sigmoid improves the selected model's raw probabilities. No direction was assumed for calibration. Evidence quality, operational cost and officer performance have separate hypotheses and evidence requirements.

## Protocol

- [Frozen experiment configuration](../ml/protocol.json) and [split lock summary](../reports/final/split-lock.json) were written before fitting. Seed 42 gives 18,000 train, 4,500 validation, 3,000 calibration and 4,500 test rows. Stratification uses labels to allocate the cohorts. Thereafter, model search only receives train and validation arrays.
- Training-only StandardScaler for 13 numeric predictors plus fixed one-hot domains for six historical repayment-code variables. No imputation was required. No ID, target or demographics enter the predictor matrix. The fit stores train sample count and exact scaler state.
- Baselines are constant train prevalence and unweighted L2 Logistic Regression with C ∈ {0.1, 1, 10}. LBFGS operates on the full batch. Log the terminal regularized gradient norm, train loss and validation loss. The first attempt reached its iteration cap at C=10. The [failed attempt](../reports/final/training-attempt1.log) preceded any test access. The cap rose from 1,000 to 5,000 while the solver tolerance, grids, seed and selection rule stayed fixed.
- XGBoost uses native binary logistic loss, depth ∈ {2, 4}, learning rate ∈ {0.03, 0.10}, a 350-round cap and patience 20. Record train and validation loss per boosting round and save the best booster slice. The native booster computes gradients internally. This run exports boosting-round losses and model checkpoints.
- PyTorch MLP uses ReLU hidden widths 64/32, BCEWithLogitsLoss, AdamW at 0.001, weight decay 0.0001, batch ∈ {32, 64, 128}, seed 42, a 40-epoch cap and validation patience six. The pre-clip gradient L2 norm is recorded at every update. Clip norm = 5, with one optimizer update per batch including the last smaller batch. Persist each candidate’s best checkpoint and record the effective batch size, updates, gradient summaries, learning rate, best epoch and checkpoint hash per epoch.
- Rank configurations by validation log loss within each family. Traverse increasing predeclared complexity from dummy to Logistic Regression to XGBoost to MLP. Adopt the next family only if it improves validation log loss by more than 0.001. Require finite converged fits, sufficient class counts and exclusion of demographics and IDs. This permits a research comparison. Independent fairness review is pending.
- Fit unregularized sigmoid calibration on clipped raw log odds from the disjoint 3,000-row calibration set. Require a positive slope. Save parameters and selected model, verify a validation prediction round-trip, and freeze component hashes in `selection.json` before `.test-opened`. The held-out test is scored once for the prespecified four prediction series.
- Use 1,000 paired row-bootstrap resamples, seed 43, 2.5th and 97.5th percentiles. Reuse each draw for all candidates. Calibration intercept and slope are reporting regressions only. A constant predictor has no identifiable calibration slope. CI sampling assumes independent rows and holds the fitted models fixed. It cannot account for retraining variation, unknown customer clusters or temporal drift.

## Reproduction

The published report records source, split and code hashes, Python/library versions, fit parameters and all confidence intervals. `data/processed/uci350-split-v2.json` stores local split IDs and is excluded from version control. The archived split summary contains the cohort totals and membership lock hash.

From the repository root with Python 3.13 and the dependencies in `backend/requirements.txt` and `ml/requirements.txt`:

```powershell
python -m scripts.fetch_uci
python -m ml.split
python -m ml.train_pd --reproduce-locked --out data/processed/reproduction-v2
python -m scripts.make_figures
python -m scripts.route_sensitivity
python -m scripts.check_restart
```

To produce the canonical report from a source-only snapshot with no canonical output directory, run `python -m ml.train_pd`. The command claims a fresh output directory exclusively. Preserve any failed attempt. Only a failure that precedes creation of `.test-opened` can be archived and retried under the same research protocol. A replay into an isolated directory corroborates execution, not independent evidence. A new model search needs a separately preregistered design and new data reserved for test.

## Experiments

| ID | Question | Evidence |
|---|---|---|
| E0 | Do formulas, hard gates and route feasibility obey the V2 contract? | V1 and V2 numerical and API regression tests. |
| E1 | Does a trained model beat constant prevalence? | Prespecified paired test log loss, XGBoost raw vs dummy. |
| E2 | Which candidate minimizes validation loss under the selection margin? | Eleven real fits or baselines, compared on validation. Locked-test comparison of XGBoost and LR. |
| E3 | What does held-out sigmoid calibration change? | Paired calibrated-minus-raw log loss and reliability bins. |
| E4 | Does CS improve material defect detection at fixed officer capacity? | `UNVALIDATED_EVIDENCE_SCORE`. Requires independent adjudication and review labels. |
| E5 | Do constrained routes minimize cost within the synthetic feasible set? | Six fixtures, 18 scenarios. DTI 25/35/45%, buffer 15/25/35%, fast-track cost 42,000 or 130,000 VND. Comparator uses fixed feasible order. |
| E6 | Are risk, fairness and business outcomes valid in the target bank population? | `BANK_EXTERNAL_VALIDATION_BLOCKED`. Requires lawful data and a prospective or credible causal evaluation. |

See the [experimental report](../reports/final/RESULTS.md), [model card](MODEL_CARD.md) and [limitations](LIMITATIONS.md).
