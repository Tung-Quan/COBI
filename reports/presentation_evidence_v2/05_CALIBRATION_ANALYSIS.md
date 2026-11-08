# Calibration analysis

**Slide conclusion.** The independent sigmoid preserved the ranking and slightly increased test log loss. The full paired interval excludes zero under row resampling. After excluding exact train-vector overlap, the descriptive interval crosses zero. Treat the effect as small and cohort-sensitive.

| Diagnostic | XGBoost raw | XGBoost sigmoid |
|---|---:|---:|
| Log loss | 0.42426259 | 0.42469407 |
| Brier | 0.13251609 | 0.13266297 |
| Calibration intercept, jointly fitted on test | 0.09170 [−0.02787, 0.20187] | 0.14432 [0.02216, 0.25756] |
| Calibration slope, jointly fitted on test | 1.05415 [0.98303, 1.13171] | 1.09470 [1.02085, 1.17525] |
| Expected defaults | 977.39 | 973.97 |
| Observed defaults | 995 | 995 |
| Observed minus expected | 17.61 | 21.03 |
| Expected / observed | 0.98230 | 0.97886 |
| ROC-AUC / AP | 0.785289 / 0.573823 | 0.785289 / 0.573823 |

Paired sigmoid minus raw log loss is **+0.00043148**, a **0.1017%** relative deterioration. Original paired 95% CI is **[+0.00002409, +0.00083681]**. Brier rises by **0.00014687**. The exploratory paired Brier interval is **[−0.00000664, +0.00030096]**. Test discrimination metrics coincide because the transformation is monotone on the observed prediction range. [Published metrics](../final/uci350-v2.0/report.json) · [Exploratory pairwise CSV](test_comparisons.csv).

## What was fitted

For calibrated predictions, observed frequencies should approximate predicted probabilities, `P(Y=1 | p)=p`. The saved Platt-style map is `p′=σ(a+b·logit(clip(p)))`, where `a=−0.04807096`, `b=0.96295244` and clipping is to `[1e−7,1−1e−7]`. The fit used unpenalized LBFGS on the 3,000-record calibration cohort with 664 defaults. These coefficients belong to the trained calibrator. [Frozen selection](../final/uci350-v2.0/selection.json) · [Implementation](../../ml/evaluation.py).

The separate test regression `logit(P(Y=1 | p))=α+β·logit(p)` estimates calibration diagnostics, with ideal joint intercept/slope `(0,1)`. A slope below one usually points to overly extreme probabilities and a slope above one to probabilities compressed toward the center. The intercept shifts the diagnostic curve at logit zero when the slope is fitted jointly. Calibration-in-the-large is a distinct diagnostic that fixes the slope at one. The ten fixed-width reliability bins plot mean prediction against observed fraction, with counts shown to flag sparse tails. The curve and intercept/slope summarize different aspects of calibration.

The sigmoid minimizes calibration-cohort log loss within a restricted family. Test-cohort prevalence and score distributions can differ by sampling variation. A two-parameter fit can add estimation error or impose the wrong shape, especially when the raw probabilities are already reasonably aligned. The data show the change in error. They do not identify a single cause. [Calibration literature](10_LITERATURE_REVIEW.md).

The release retains the frozen sigmoid and reports both outputs. A subsequent study can preregister raw, sigmoid and isotonic candidates using development-only calibration/selection with nested or cross-fitted partitions, then evaluate once on a new external cohort or a genuinely untouched set. Reusing this test to choose a map would invalidate its confirmatory role.

**Visuals** · [Reliability and bin counts](figures/reliability.svg) · [Paired error change](figures/calibration_delta.svg) · [Duplicate sensitivity](figures/duplicate_sensitivity.svg).
