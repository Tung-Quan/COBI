# Evidence-Quality Models Under Synthetic Distribution Shift: COBI V4

## Abstract

This study evaluates whether frozen evidence-document defect models retain their cost and critical-error behavior when the synthetic data-generating process changes. The task is document evidence-quality triage, not credit-default prediction or loan approval. We replayed four frozen baselines on a previously inspected V3 synthetic test (192 cases, 96 customer groups, 753 documents) and evaluated them without refitting on an independently implemented event-ledger challenge (1,920 cases, 960 groups, 7,744 documents; six scenarios). Customer-cluster bootstrap intervals were computed at unchanged V3 thresholds. On V3, critical recall ranged from 0.880 to 0.910. On Generator B, recall ranged from 0.628 to 0.866, average precision from 0.110 to 0.287, and case review workload from 0.546 to 0.652. On the legitimate-discrepancy scenario, 95.5%–99.9% of legitimate documents were flagged. The results show that strong performance on the inspected synthetic test did not ensure robustness to the registered synthetic challenge. The evidence is limited by programmatic labels, synthetic scenarios, and a narrow input schema; it does not validate use in a bank. The required disposition remains `EVIDENCE_AI_VALIDATION_BLOCKED`.

**Keywords:** document verification, dataset shift, synthetic evaluation, cost-sensitive learning, evidence quality, human review

## 1. Introduction

Document verification systems can reduce manual work only if their detection behavior remains useful when document sources, representations, and error mechanisms change. Dataset shift can weaken both predictive accuracy and uncertainty quality, which motivates evaluation beyond a single in-distribution test [1]. Performance may also differ across predefined groups even where average performance is high [2]. In a high-impact workflow, one operating point must be evaluated in terms of missed critical evidence and human-review burden, not a single aggregate score.

This work evaluates a COBI evidence-quality prototype. Its score concerns whether an evidence document contains a material extraction or evidence-integrity defect. It is not an estimate of creditworthiness, probability of default, eligibility, or approval. V4 addresses three questions: (RQ1) what are the frozen models' critical recall and case-level review workload on V3's previously inspected synthetic test? (RQ2) how do those operating characteristics change on an independently implemented synthetic generator? (RQ3) how sensitive are illustrative costs to explicit assumptions about review, missed evidence, inference, fixed cost, and volume?

The contribution is a locked, auditable evaluation protocol, a second synthetic generator with separate observed facts and gold labels, group-resampled uncertainty intervals, a transparent scenario cost model, and a fail-closed research interface. The central finding is a negative result: synthetic generalization is inadequate to justify deployment claims.

## 2. Related Work

Ovadia et al. benchmarked predictive uncertainty under distributional shift, motivating explicit out-of-distribution and shift evaluation rather than relying only on in-distribution performance [1]. Sagawa et al. analyze group-shift failures and worst-group generalization, emphasizing that aggregate accuracy can hide subgroup failures [2]. Elkan formalizes cost-sensitive classification and the role of error-cost asymmetry [3]. We therefore report error recall and workload separately and expose cost inputs as assumptions. Brier and logarithmic scores are proper scoring rules useful for probabilistic forecasts, but no single score demonstrates operational calibration or safety [4].

## 3. Task and Research Design

### 3.1 Task definition

For each document, the model emits a material-defect score. A binary frozen threshold marks a document for human review. A case is counted as requiring review if at least one document is flagged. A critical false negative is a gold critical-defect document that does not cross the frozen threshold. This definition deliberately distinguishes document-level defect events from case-level review work.

### 3.2 Models and operating thresholds

We compare M0 CS V2 (existing deterministic cost-sensitive baseline), M1 logistic regression, M2 XGBoost and M3 Deep Sets. The three learned models' weights, the existing calibrators, feature preprocessing, 32-feature contract and V3 selection thresholds are frozen. No training, calibration, threshold search for selection, or model choice based on Generator B occurred in V4. A retrospective threshold curve is descriptive only.

### 3.3 Datasets

E1 uses the locked V3 test: 192 cases, 96 customer groups, 753 documents, 293 material defects and 200 critical defects. The data had already been opened and discussed; E1 is retrospective.

E2 was generated with an event-ledger implementation that does not call V3's synthetic generator or format-shift functions. It contains 1,920 cases, 960 customer groups, six equally sized scenarios, and 7,744 documents. The two cases in each customer group share a generated profile. Scenarios cover income reconciliation (B1), duplicate/overlap events (B2), locale and units (B3), evidence freshness (B4), legitimate discrepancies (B5), and supported source combinations (B6). Documents were compatible with the frozen schema (0/7,744 incompatible). Observations, canonical facts, and programmatic labels are stored in separate files. Labels are not human-reviewed bank truth.

The first B pilot was archived and explicitly invalidated after a post-run leakage inspection found event-dependent wording in observed text. The confirmatory generator removed evaluative text while retaining observable event evidence. Amendment 1 was registered before the confirmatory rerun; it retained the registered question, seed, scenarios, metrics, thresholds, and cost assumptions. Both pilot and amendment remain available for audit.

### 3.4 Outcomes

Primary outcomes are critical recall, critical false-negative count, and case review workload. Secondary outcomes include average precision for material defects, Brier score, log loss, document flag rate, and precision at threshold. Critical recall is TP/(TP+FN) over critical documents. Review workload is the number of cases with one or more flagged documents divided by cases. AP is reported with prevalence because it depends on the positive-class prevalence. Brier and log loss summarize probabilistic error; they do not establish transportability [4].

### 3.5 Statistical analysis

We used 300 bootstrap draws at the customer-group level, preserving all cases and documents for a sampled group. E1 model comparisons are paired. E2 aggregate intervals resample groups within scenario to retain the registered scenario mix. Generalization-gap intervals independently resample customer groups from A and B. Intervals are percentile 95% intervals conditional on fixed models, thresholds, generator and labels. With 300 draws, tail quantiles have finite Monte Carlo error; the intervals are not population guarantees.

### 3.6 E3 cost sensitivity

For application volume N, review rate r, critical false-negative documents per case f, review cost cᵣ, missed-document cost cₘ, inference cost cᵢ and fixed operating cost c₀, we calculate:

`Total cost = N × r × cᵣ + N × f × cₘ + N × cᵢ + c₀`.

Review is charged per flagged case; missed-error cost is charged per critical document. Cost inputs are illustrative VND values in `config/cost_scenarios.yaml`. E3 uses E1 rates, not the poor E2 rates; this makes it an exploratory scenario analysis, not an economic validation.

## 4. Results

| Model | E1 recall (FN/support) | E1 workload | E1 AP | E2 recall (FN/support) | E2 workload | E2 AP |
|---|---:|---:|---:|---:|---:|---:|
| CS V2 | 0.880 (24/200) | 0.818 | 0.4957 | 0.629 (277/747) | 0.609 | 0.1103 |
| Logistic regression | 0.910 (18/200) | 0.792 | 0.9063 | 0.866 (100/747) | 0.652 | 0.2230 |
| XGBoost | 0.905 (19/200) | 0.708 | 0.9828 | 0.628 (278/747) | 0.546 | 0.2015 |
| Deep Sets | 0.910 (18/200) | 0.766 | 0.9269 | 0.807 (144/747) | 0.593 | 0.2870 |

E1 critical recall was 0.880–0.910, with case workload 0.708–0.818. E2 critical recall fell to 0.628–0.866, AP was 0.110–0.287, and workload was 0.546–0.652. For example, XGBoost moved from 0.905 to 0.628 critical recall and from 0.9828 to 0.2015 AP. Logistic regression had the highest aggregate E2 critical recall (0.866; 100/747 critical defects missed), but this does not resolve subgroup failures.

On B4, logistic regression, XGBoost and Deep Sets each missed all 80 critical stale-as-current defects at the frozen thresholds. On B5, the false-positive rate among legitimate documents was 99.9% for CS V2, 99.4% for logistic regression, 95.5% for XGBoost, and 97.9% for Deep Sets. This makes a low review workload in another scenario insufficient to claim an acceptable review policy.

At 10,000 applications under the medium-medium illustrative cost assumptions, the model totals ranged from VND 1.216B to VND 1.273B versus VND 1.443B for CS V2. These differences are assumption-driven and use V3 rates. They must not be described as realized or expected bank savings.

## 5. Failure and Ablation Analysis

V4 is an evaluation of frozen models; it does not train or tune models. No feature ablation was run because changing the input representation or retraining would violate the registered no-refit challenge. The registered scenario stress tests provide failure analysis instead: B4 exposes stale evidence; B5 tests legitimate between-document differences; B6 limits each case to a pair of supported sources. The B4 and B5 failures should drive the next experiment: human-reviewed labels, adjudicated evidence freshness semantics, and a pre-registered feature/threshold study on a held-out source and time period. That follow-up must not reuse Generator B to select and report a final model on the same examples.

## 6. Discussion

The gap between E1 and E2 shows why repeated evaluation on a single synthetic process is not enough to infer robustness. The B4 result suggests that the frozen input representation and models do not reliably capture freshness semantics at this operating point. The B5 false-positive result indicates poor tolerance of legitimate per-document variation. These are construct-validity warnings: the synthetic scenarios are useful for exposing possible failure modes, but their distributions and programmatic labels may not faithfully represent a real document pipeline.

The cost analysis is subordinate to detection quality. Even where the simulated cost is lower, it inherits E1's retrospective synthetic rates and assumed costs. It cannot justify live routing, approval, or reduction of human review. The interface therefore exposes these artifacts read-only and keeps routing and approval authorization false.

## 7. Threats to Validity and Limitations

1. **External validity:** both datasets are synthetic; neither establishes performance on bank documents.
2. **Gold-label validity:** Generator B labels are derived from its own event rules, not blind human adjudication.
3. **Generator coverage:** six designed scenarios cannot represent all source, language, OCR, fraud, or workflow variations.
4. **Retrospective E1:** the V3 test was previously inspected; the E1 result is descriptive.
5. **Prevalence:** B prevalence differs from A; AP gaps reflect both ranking and prevalence change.
6. **Fixed operating point:** no V4 retuning means the study evaluates portability of the existing thresholds, not best achievable performance on B.
7. **Bootstrap scope:** intervals condition on the finite synthetic samples, fixed models, and labels.
8. **Cost assumptions:** no cost value is a bank quote, measured operational expense, or realized saving.
9. **Schema scope:** 32 features, at most six documents, and three source categories constrain applicability.

## 8. Conclusion

The frozen models did not maintain V3-level performance on an independently implemented synthetic challenge, and the legitimate-discrepancy test produced extreme false-positive rates. The evaluation is useful as a reproducible stress test and a warning against relying on a single synthetic test. It does not establish real-world validity. Keep the release research-only and blocked until a governed, human-reviewed, representative external evaluation supports any stronger claim.

## Reproducibility Statement

Protocol, amendment, data-layer hashes, predictions, bootstrap summaries, plots, code, tests, and final manifest are included in `reports/evidence-v4`. The protected baseline manifest covers the pre-existing V2/V3 and UCI artifacts. No V4 training took place; no epochs, gradients, or training losses are claimed.

## References

1. Y. Ovadia et al. “Can You Trust Your Model’s Uncertainty? Evaluating Predictive Uncertainty Under Dataset Shift.” *NeurIPS*, 2019. [Proceedings page](https://papers.nips.cc/paper/2019/hash/8558cb408c1d76621371888657d2eb1d-Abstract.html).
2. S. Sagawa, P. W. Koh, T. B. Hashimoto, and P. Liang. “Distributionally Robust Neural Networks for Group Shifts: On the Importance of Regularization for Worst-Case Generalization.” *ICLR*, 2020. [OpenReview paper](https://openreview.net/references/pdf?id=bWO5RqfDE); [arXiv:1911.08731](https://arxiv.org/abs/1911.08731).
3. C. Elkan. “The Foundations of Cost-Sensitive Learning.” *IJCAI*, 2001, pp. 973–977. [IJCAI proceedings](https://ijcai.org/proceedings/2001/133).
4. T. Gneiting and A. E. Raftery. “Strictly Proper Scoring Rules, Prediction, and Estimation.” *Journal of the American Statistical Association*, 102(477), 2007, pp. 359–378. [DOI:10.1198/016214506000001437](https://doi.org/10.1198/016214506000001437).
