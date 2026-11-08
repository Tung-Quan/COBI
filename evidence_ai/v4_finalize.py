"""Create the V4 research, audit, pitch, and integrity deliverables."""
from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from evidence_ai.features import NAMES
from evidence_ai.replay import read
from evidence_ai.synthetic import DATA as V3_DATA
from evidence_ai.train import RELEASE
from evidence_ai.v4_experiments import MODELS, LABELS, OUT, _v3_test, metrics
from evidence_ai.v4_generator import OUT as B_DATA, freeze, validate_observed_schema
from ml.contracts import ROOT, sha, write_json

BLOCKED = "EVIDENCE_AI_VALIDATION_BLOCKED"


def _fmt(value, digits=3):
    return "—" if value is None else f"{value:.{digits}f}"


def _report_tables(e1, e2):
    rows = []
    for model in MODELS:
        a, b = e1["models"][model], e2["models"][model]
        rows.append(f"| {LABELS[model]} | {_fmt(a['critical_recall'])} ({a['critical_false_negatives']}/{a['critical_errors']}) | {_fmt(a['review_workload'])} | {_fmt(a['average_precision'], 4)} | {_fmt(b['critical_recall'])} ({b['critical_false_negatives']}/{b['critical_errors']}) | {_fmt(b['review_workload'])} | {_fmt(b['average_precision'], 4)} |")
    return "\n".join(rows)


def _write_research_docs(e1, e2, e3, audit):
    v3 = e1["dataset"]
    gen = e2["generator_manifest"]
    table = _report_tables(e1, e2)
    b5 = e2["legitimate_discrepancies_B5"]
    b5_rows = "\n".join(
        f"| {LABELS[m]} | {x['flagged_legitimate_documents']}/{x['documents'] - x['programmatic_gold_errors']} | {_fmt(x['false_positive_rate_on_legitimate_documents'] * 100, 1)}% |"
        for m, x in b5.items()
    )
    gaps = e2["generalization_gaps"]
    gap_rows = "\n".join(
        f"| {LABELS[m]} | {_fmt(x['AP_A_minus_AP_B'])} | {_fmt(x['CriticalRecall_A_minus_B'])} | {_fmt(x['LogLoss_B_minus_A'])} |"
        for m, x in gaps.items()
    )
    e3_rows = []
    with (OUT / "tables/business_scenarios.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["scenario_id"] == "medium_medium_volume_10000":
                e3_rows.append(row)
    e3_table = "\n".join(
        f"| {LABELS[row['model']]} | {float(row['total_cost_vnd']) / 1e9:.3f} | {float(row['savings_vs_cs_v2_vnd']) / 1e6:,.1f} |"
        for row in e3_rows
    )

    results = f"""# COBI Evidence AI V4 — Results

## Scope and disposition

V4 is a technical research evaluation of document evidence defect detection. It does not estimate default risk and does not make or recommend credit decisions. The three learned models and the CS V2 rules baseline remain frozen; V4 trained no model, changed no calibration, and selected no threshold. The bank-validation gate remains **`{BLOCKED}`**.

## E1 — V3 cost and safety replay

E1 replays the previously inspected V3 synthetic test: {v3['cases']} cases, {v3['customer_groups']} customer groups, {v3['documents']} documents, {v3['material_defects']} material defects, and {v3['critical_defects']} critical defects. Thresholds came from the V3 selection lock. This is retrospective evidence, not a new confirmatory test.

## E2 — independent synthetic challenge

Generator B v1.1 uses an event-ledger implementation independent of the V3 generator. It produced {gen['counts']['cases']:,} cases, {gen['counts']['customer_groups']:,} customer groups and {gen['counts']['documents']:,} documents in six registered scenarios. All documents passed the frozen input schema ({gen['compatibility']['incompatible_documents']} incompatible). Gold labels are programmatic synthetic labels, not human-reviewed banking truth. The first pilot was invalidated before confirmatory analysis because model-visible text exposed event meaning; the correction and pre-confirmatory amendment are preserved in the archive.

| Model | E1 critical recall (FN/support) | E1 case workload | E1 AP | E2 critical recall (FN/support) | E2 case workload | E2 AP |
|---|---:|---:|---:|---:|---:|---:|
{table}

The sharp decline in average precision and, for several models, critical recall is evidence that the V3 advantage does not transfer consistently to this independent synthetic generator. In B4, logistic regression, XGBoost and Deep Sets detected none of 80 critical stale-as-current cases at their unchanged thresholds. In B6, the heuristic and XGBoost missed 106/167 and 95/167 critical defects respectively. These are scenario-conditioned outcomes, not estimates of bank prevalence.

### Legitimate-discrepancy stress test (B5)

| Model | Legitimate documents flagged / support | False-positive rate |
|---|---:|---:|
{b5_rows}

The B5 result is a serious failure mode: all frozen models flagged most legitimate document-level differences. High critical recall by itself is not sufficient evidence of a safe review policy.

### Descriptive A/B gaps

| Model | AP A − B | Critical recall A − B | Log loss B − A |
|---|---:|---:|---:|
{gap_rows}

Generator A and B have different prevalences; average precision is prevalence-sensitive. The gaps are descriptive comparisons between two fixed synthetic datasets. Intervals use independent customer-group resampling and are conditional on the frozen models and thresholds.

## E3 — illustrative costs

At 10,000 applications, with assumed review cost of VND 100,000 per flagged case and assumed missed-critical-document cost of VND 500,000, the simulated totals are:

| Model | Simulated total (VND billions) | Difference vs CS V2 (VND millions) |
|---|---:|---:|
{e3_table}

These figures combine E1 synthetic rates with configurable assumptions, including VND 300 per inference and VND 10 million fixed learned-model cost. They are scenario calculations, not bank quotations, measured savings, or evidence that a model is economically deployable. E2's shift and false-positive failures further limit their use.

## Statistical and integrity checks

- {audit['protected_baseline_artifacts_verified']} protected V2/V3 artifacts verified against the immutable baseline manifest; no mismatch found.
- V3 train, validation, calibration and test sets have disjoint customer groups; E1 metric replay matched the frozen report.
- E2 counts, file hashes, observed/gold separation, exact input schema and no-refit policy were checked.
- Intervals use 300 customer-cluster bootstrap draws (registered seeds); they describe sampling variability in these finite synthetic datasets and do not guarantee future performance.
- Full statistical detail: `STATISTICAL_AUDIT.md` and `statistical_audit.json`.

## Interpretation

The defensible result is a generalization warning. The V3 test made the models appear strong, while the independently generated cases exposed severe weaknesses in stale evidence and legitimate discrepancies. The next research step is to build a human-reviewed, privacy-governed benchmark and pre-register recalibration or model redesign against realistic cases. Until then, keep the model in research-only shadow mode and leave all production decisions to the existing rules and human process.

## Reproducibility and files

See `EXPERIMENT_PROTOCOL.md`, `EXPERIMENT_PROTOCOL_AMENDMENT_1.md`, `ARTIFACT_MANIFEST.json`, `final_manifest.json`, and the prediction-level CSVs. The final manifest hashes the V4 deliverables and the linked implementation files.
"""
    (OUT / "RESULTS.md").write_text(results, encoding="utf-8")

    paper = f"""# Evidence-Quality Models Under Synthetic Distribution Shift: COBI V4

## Abstract

This study evaluates whether frozen evidence-document defect models retain their cost and critical-error behavior when the synthetic data-generating process changes. The task is document evidence-quality triage, not credit-default prediction or loan approval. We replayed four frozen baselines on a previously inspected V3 synthetic test (192 cases, 96 customer groups, 753 documents) and evaluated them without refitting on an independently implemented event-ledger challenge (1,920 cases, 960 groups, 7,744 documents; six scenarios). Customer-cluster bootstrap intervals were computed at unchanged V3 thresholds. On V3, critical recall ranged from 0.880 to 0.910. On Generator B, recall ranged from 0.628 to 0.866, average precision from 0.110 to 0.287, and case review workload from 0.546 to 0.652. On the legitimate-discrepancy scenario, 95.5%–99.9% of legitimate documents were flagged. The results show that strong performance on the inspected synthetic test did not ensure robustness to the registered synthetic challenge. The evidence is limited by programmatic labels, synthetic scenarios, and a narrow input schema; it does not validate use in a bank. The required disposition remains `{BLOCKED}`.

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
{table}

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
"""
    (OUT / "PAPER_DRAFT.md").write_text(paper, encoding="utf-8")

    pitch = OUT / "pitch"
    pitch.mkdir(parents=True, exist_ok=True)
    (pitch / "PITCH_EVIDENCE_SUMMARY.md").write_text(f"""# Pitch Evidence Summary

## One-sentence finding

Four frozen models looked strong on one inspected synthetic test, but performance dropped on an independently generated challenge; several severe failures mean there is no basis for a deployment or bank-savings claim.

## What the study did

- Replayed four frozen systems at unchanged V3 thresholds.
- Tested on a second event-ledger generator: 1,920 cases, 960 groups, 7,744 documents, six scenarios.
- Preserved customer groups in 300-draw bootstrap intervals.
- Simulated costs under explicit assumptions, without calling them measured savings.
- Kept the workbench read-only; routing and approval authority are false.

## Evidence to show

- E1 critical recall: 0.880–0.910; case review workload: 0.708–0.818.
- E2 critical recall: 0.628–0.866; case workload: 0.546–0.652.
- B4: three learned models missed all 80 critical stale-as-current cases.
- B5 false-positive rate on legitimate documents: 95.5%–99.9%.
- E3 medium assumptions at 10,000 applications: illustrative totals VND 1.216B–1.273B, versus VND 1.443B baseline. This is not a bank quote or realized saving.

## Claim boundary

Say “synthetic stress test” and “research-only.” Do not say “validated for banks,” “safe,” “reduces real review workload,” or “saves VND X.” The release remains `{BLOCKED}`.

## Suggested visuals

- `figures/generator_shift_performance.png` — show the drop from A to B.
- `figures/scenario_failure_matrix.png` — show scenario-level recall and workload.
- `figures/business_cost_sensitivity.png` — show assumption sensitivity, with the “illustrative only” footnote.

All captions and limitations are in `FIGURE_CAPTIONS.md`.
""", encoding="utf-8")

    (pitch / "SLIDE_READY_ENGLISH.md").write_text(f"""# Slide-Ready Research Pitch (English)

### Slide 1 — Question
**Can frozen document-evidence models transfer beyond one synthetic data process?** We evaluate evidence-quality triage, not credit risk or loan approval.

### Slide 2 — Locked evaluation
Four frozen systems; unchanged V3 thresholds and 32-feature contract. E1 is a retrospective replay. E2 is a separately implemented event-ledger challenge: 1,920 cases, 960 customer groups, 7,744 documents, six scenarios. No retraining or threshold tuning.

### Slide 3 — The apparent V3 result
Critical recall was 88.0%–91.0%; case review workload was 70.8%–81.8%. Because the test had been inspected, these are descriptive results.

### Slide 4 — Independent synthetic challenge
Critical recall fell to 62.8%–86.6%. Average precision fell to 0.110–0.287. At the frozen threshold, logistic regression, XGBoost and Deep Sets missed all 80 critical B4 stale-as-current cases.

### Slide 5 — False-positive stress test
On B5 legitimate discrepancies, 95.5%–99.9% of legitimate documents were flagged. High critical recall alone does not establish a usable or safe review policy.

### Slide 6 — Cost is assumption-dependent
At 10,000 applications under illustrative medium costs, simulated totals were VND 1.216B–1.273B vs VND 1.443B for CS V2. These are scenario calculations using E1 rates, not observed bank costs or realized savings.

### Slide 7 — Conclusion and next evidence
The independent challenge exposed major generalization and false-positive failures. Keep the release research-only. Next: a governed, human-reviewed external benchmark, pre-registered evaluation, and independent replication. **Status: `{BLOCKED}`.**

**Footer for every results slide:** Synthetic programmatic gold; no human-reviewed bank truth. E1 is retrospective. Bootstrap intervals condition on frozen models and sampled synthetic groups. No routing or approval authority.
""", encoding="utf-8")

    (pitch / "PRESENTER_SCRIPT_EN.md").write_text(f"""# Presenter Script (English, ~4 minutes)

**Slide 1.** Our research question is whether document evidence-quality models that perform well on one synthetic process remain useful when the process changes. This is not a model of credit default or loan approval.

**Slide 2.** We froze four systems, their input features, calibration, and operating thresholds. E1 replays a V3 synthetic test that had already been inspected, so it is retrospective. E2 uses a separately implemented event-ledger generator with 1,920 cases, 960 customer groups, and 7,744 compatible documents across six scenarios. We did not retrain or tune on the challenge data.

**Slide 3.** On E1, critical recall ranges from 88 to 91 percent. Review workload ranges from 71 to 82 percent of cases. These numbers describe that one known synthetic dataset; they are not a bank performance estimate.

**Slide 4.** On E2, critical recall falls to roughly 63 to 87 percent, and average precision is much lower. The clearest failure is evidence freshness: three learned models miss all 80 critical stale-as-current cases at the frozen operating point. This is a warning that the apparent V3 performance does not transfer consistently.

**Slide 5.** We also tested legitimate discrepancies. Between 95 and 100 percent of legitimate documents were flagged by the four systems. That is a substantial false-positive problem and would make a simple “high recall” story incomplete.

**Slide 6.** We built an explicit cost sensitivity model. Under one illustrative scenario at 10,000 applications, learned models appear less costly than the rules baseline. However, those numbers use assumed costs and E1 event rates; they are not bank quotations, observed savings, or evidence of deployability. The E2 failures make them especially unsuitable as a business case.

**Slide 7.** Our conclusion is a negative but useful research result: one synthetic test is not enough. The next step is a privacy-governed benchmark with human-reviewed labels and a pre-registered external evaluation. For now, the model remains research-only. The bank-validation status is `{BLOCKED}`, and the interface has no routing or approval authority.
""", encoding="utf-8")

    (pitch / "JUDGE_QA.md").write_text(f"""# Judge Q&A

### What exactly does the score predict?
Whether a document contains a material evidence or extraction defect under the defined synthetic/annotation task. It is not default probability, creditworthiness, eligibility, or approval.

### Why use synthetic data?
It allows controlled, reproducible stress scenarios and explicit gold rules. It cannot establish external validity or replace real, adjudicated documents. That limitation is central to the result.

### Why is E1 retrospective?
The V3 test had already been inspected and discussed before V4. We label it retrospective and do not treat its threshold sweep as model selection.

### What is independent about Generator B?
It is implemented as a new event-ledger process and does not call the V3 generator or its format-shift function. Its observed documents, canonical facts, and labels are separate. A first pilot was invalidated after a leakage audit; the corrected generator and amendment are preserved, and only the amended run is reported as confirmatory within the synthetic protocol.

### Why not tune thresholds on B?
That would turn the challenge set into selection data and undermine the portability test. The aim was to evaluate the registered V3 operating point. A future tuning study needs a separate development set and untouched test set.

### Why use customer-group bootstrap?
Two cases from one generated customer share profile-level information. Resampling groups keeps those dependent cases together. The resulting intervals remain conditional on the designed synthetic sample and are not population guarantees.

### Does 90% recall target mean 90% guaranteed recall?
No. It was part of threshold selection on V3 calibration data. It is not a population guarantee and did not hold consistently on Generator B.

### Is the E3 cost saving real?
No. It is an assumption-based simulation using retrospective E1 synthetic rates. Unit costs and volume are configurable assumptions, not bank quotations or measured savings.

### Can the interface change loan outcomes?
No. The V4 research page is read-only. Both routing and approval authorization are false; the production workbench and mandatory gates are not changed by these research artifacts.

### What is the strongest conclusion?
The independent synthetic test exposes serious transfer failures, especially on stale evidence and legitimate discrepancies. The evidence supports a need for a human-reviewed external benchmark, not deployment.

### What is not yet done?
No human review, bank validation, external validation, or V4 model training/tuning. There are no V4 epochs, gradients, or training-loss claims. The status remains `{BLOCKED}`.
""", encoding="utf-8")

    (pitch / "CLAIMS_AND_LIMITATIONS.md").write_text(f"""# Claims and Limitations

| Claim | Evidence | Safe wording | Limitation |
|---|---|---|---|
| Frozen systems were replayed on V3 | E1 output and V3 release replay | “Retrospective synthetic replay” | Previously inspected test; not confirmatory |
| Generator B differs in implementation | New event-ledger code, hashes, separate data layers | “Independently implemented synthetic challenge” | Independent code does not imply realistic or independent human labels |
| Performance changed between A and B | E1/E2 results and group bootstrap | “Synthetic cross-generator performance changed” | Different prevalence and designed scenarios; no bank inference |
| B4 and B5 expose important failure modes | Scenario metrics and B5 legitimate-document denominator | “Models failed these predeclared synthetic stress tests” | Scenario assumptions may not match real documents |
| E3 explores cost sensitivity | YAML assumptions, cost equation, scenario table | “Illustrative assumption-based simulation” | Not measured cost, quote, savings, or feasibility |
| Research page is non-authoritative | API response, route tests, read-only UI | “No routing or approval authority” | Does not itself prove the upstream bank workflow is safe |

## Disallowed claims

- Bank validated, production ready, safe, fair, compliant, or guaranteed recall.
- Real-world workload reduction or VND savings.
- A model is selected as the best operating policy based on Generator B.
- Human-validated labels or real customer outcomes.

**Disposition:** `{BLOCKED}` until a separately governed and representative evaluation supports a new decision.
""", encoding="utf-8")

    (pitch / "FIGURE_CAPTIONS.md").write_text("""# Figure Captions and Method Footnotes

1. **Generator shift performance** (`figures/generator_shift_performance.png`). Frozen V3 thresholds applied to V3 test A and independent synthetic generator B; critical recall, average precision, and case-level workload. Customer-cluster bootstrap intervals are conditional on fixed systems and synthetic groups. A was previously inspected; B uses programmatic gold.
2. **Scenario failure matrix** (`figures/scenario_failure_matrix.png`). Scenario-specific critical recall and case review workload for B1–B6. Each scenario contains 320 synthetic cases from 160 customer groups. These designed scenarios are not estimates of real-world prevalence.
3. **Generalization gap** (`figures/generalization_gap.png`). Descriptive A−B gaps for AP and critical recall, and B−A log-loss difference. A/B prevalence differs; AP is prevalence-sensitive. Independent customer-group bootstrap intervals are not population guarantees.
4. **Cost sensitivity** (`figures/business_cost_sensitivity.png`). Simulated difference versus CS V2 at 10,000 applications over the assumed review and missed-document costs. Positive values denote lower simulated cost. All monetary inputs are illustrative assumptions; no measured saving is shown.
5. **Break-even frontier** (`figures/business_break_even.png`). Analytic break-even missed-document cost under fixed E1 synthetic rates and assumed review costs. The frontier is a conditional sensitivity illustration, not a bank business case.

**Required slide footnote:** Synthetic datasets and programmatic labels only; no human-reviewed bank truth. E1 is retrospective. E3 uses assumed costs and E1 rates. No model training or threshold changes in V4. Routing and approval authority are false.
""", encoding="utf-8")

    figure_names = ["generator_shift_performance", "scenario_failure_matrix", "generalization_gap",
                    "business_cost_sensitivity", "business_break_even"]
    pitch_figures = pitch / "figures"
    pitch_figures.mkdir(parents=True, exist_ok=True)
    for name in figure_names:
        for ext in ("png", "svg"):
            source = OUT / "figures" / f"{name}.{ext}"
            if source.is_file():
                shutil.copy2(source, pitch_figures / source.name)
    for name in ("robustness_by_scenario.csv", "business_scenarios.csv", "model_tradeoff_table.csv"):
        shutil.copy2(OUT / "tables" / name, pitch / name)


def build_audit():
    baseline_path = OUT / "ARTIFACT_MANIFEST.json"
    baseline = read(baseline_path)
    if baseline.get("manifest_type") != "protected_v2_v3_baseline":
        raise ValueError("Protected baseline manifest invalid")
    verified = []
    for item in baseline["artifacts"]:
        path = ROOT / item["path"].replace("/", "\\")
        if not path.is_file() or sha(path) != item["sha256"]:
            raise ValueError(f"Protected V2/V3 artifact changed: {item['path']}")
        verified.append(item["path"])

    protocol = read(OUT / "experiment_protocol.json")
    amendment = read(OUT / "EXPERIMENT_PROTOCOL_AMENDMENT_1.json")
    e1, e2, e3 = (read(OUT / filename) for filename in
                  ("E1_RESULTS.json", "E2_RESULTS.json", "E3_COST_RESULTS.json"))
    generator_manifest = read(B_DATA / "generator_b_manifest.json")
    for filename, expected in generator_manifest["file_sha256"].items():
        if sha(B_DATA / filename) != expected:
            raise ValueError(f"Generator B input hash mismatch: {filename}")
    generated = freeze()
    if generated != generator_manifest:
        raise ValueError("Deterministic Generator B regeneration differs from frozen manifest")
    if (sha(OUT / "experiment_protocol.json") != baseline["experiment_protocol_sha256"]
            or amendment.get("original_protocol_sha256") != baseline["experiment_protocol_sha256"]
            or amendment.get("status") != "REGISTERED_BEFORE_CONFIRMATORY_EVALUATION"
            or e2.get("generator_manifest", {}).get("protocol_amendment_sha256") != sha(OUT / "EXPERIMENT_PROTOCOL_AMENDMENT_1.json")):
        raise ValueError("Protocol/amendment chain is inconsistent")
    if e1.get("validation_status") != BLOCKED or e2.get("validation_status") != BLOCKED:
        raise ValueError("A V4 result incorrectly changed the validation gate")
    if e2["generator_manifest"]["counts"] != generator_manifest["counts"]:
        raise ValueError("E2 counts differ from frozen Generator B manifest")

    # Replay and split/group integrity checks: _v3_test verifies locked predictions and all result metrics.
    test_cases, data, predictions, lock = _v3_test()
    observed_cases = read(V3_DATA / "observed.json")
    split = read(V3_DATA / "locked_split.json")
    group_by_case = {case["case_key"]: case["customer_group"] for case in observed_cases}
    split_groups = {part: {group_by_case[key] for key in keys} for part, keys in split.items()}
    partitions = list(split_groups)
    for i, left in enumerate(partitions):
        for right in partitions[i + 1:]:
            if split_groups[left] & split_groups[right]:
                raise ValueError(f"Customer group leakage between {left} and {right}")

    b_cases = read(B_DATA / "observed.json")
    b_schema = validate_observed_schema(b_cases)
    if b_schema["incompatible_documents"] != 0:
        raise ValueError("Generator B observed schema is incompatible")
    if len(NAMES) != 32 or any(term in name.casefold() for name in NAMES
                               for term in ("scenario", "customer_group", "case_key", "document_key", "generation_event")):
        raise ValueError("Frozen feature contract contains generator-only identity or scenario fields")
    if (e2.get("generator_manifest", {}).get("model_training") is not False
            or e2.get("generator_manifest", {}).get("calibration_or_threshold_changes") is not False):
        raise ValueError("V4 unexpectedly refit or retuned the models")

    e3_cfg = e3["assumptions"]
    with (OUT / "tables/business_scenarios.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != e3["scenario_rows"] or e3["status"] != "ILLUSTRATIVE_ASSUMPTION_BASED_SIMULATION":
        raise ValueError("E3 rows/status failed integrity check")

    audit = {
        "audit_id": "cobi-evidence-v4-final-audit",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation_status": BLOCKED,
        "protected_baseline_manifest_sha256": sha(baseline_path),
        "protected_baseline_artifacts_verified": len(verified),
        "protected_baseline_mismatches": [],
        "original_protocol_sha256": sha(OUT / "experiment_protocol.json"),
        "amendment_sha256": sha(OUT / "EXPERIMENT_PROTOCOL_AMENDMENT_1.json"),
        "generator_code_sha256": sha(ROOT / "evidence_ai/v4_generator.py"),
        "generator_data_hashes": generator_manifest["file_sha256"],
        "generator_counts": generator_manifest["counts"],
        "generator_schema": b_schema,
        "frozen_feature_count": len(NAMES),
        "frozen_feature_names": list(NAMES),
        "v3_split_group_counts": {part: len(groups) for part, groups in split_groups.items()},
        "v3_customer_group_overlap_pairs": 0,
        "v3_locked_test_cases_replayed": len(test_cases),
        "v3_frozen_thresholds": {model: float(lock["all_thresholds"][model]) for model in MODELS},
        "v3_replay_matches_frozen_report": True,
        "e1_cases_documents_critical_support": [e1["dataset"][key] for key in ("cases", "documents", "critical_defects")],
        "e2_cases_groups_documents": [generator_manifest["counts"][key] for key in ("cases", "customer_groups", "documents")],
        "bootstrap": {"draws": protocol["bootstrap"]["draws"], "seed": protocol["bootstrap"]["seed"], "unit": "customer_group"},
        "e3_rows": len(rows),
        "e3_cost_inputs_are_assumptions": True,
        "v4_training_performed": False,
        "routing_authorized": False,
        "approval_authorized": False,
    }
    write_json(OUT / "statistical_audit.json", audit)
    audit_md = f"""# Statistical and Integrity Audit

**Disposition:** `{BLOCKED}`. This audit verifies artifact integrity and the registered analysis; it does not validate bank use.

## Baseline and protocol

- Protected V2/V3 manifest: `{audit['protected_baseline_manifest_sha256']}`.
- Protected files checked: {len(verified)}; mismatches: 0.
- Original registered protocol SHA-256: `{audit['original_protocol_sha256']}`.
- Pre-confirmatory generator amendment SHA-256: `{audit['amendment_sha256']}`.
- The initial generator pilot remains archived as invalidated because observed text disclosed event meaning. Its outputs are not used in confirmatory results.

## Split integrity and replay

| V3 partition | Customer groups |
|---|---:|
{chr(10).join(f"| {part} | {len(groups)} |" for part, groups in split_groups.items())}

No customer group overlaps across V3 partitions. The V3 locked test replay resolved {len(test_cases)} cases and reproduced frozen report metrics for all four models. Thresholds, calibration, and model weights remain frozen.

## Generator B and feature contract

- Cases / customer groups / documents: {generator_manifest['counts']['cases']} / {generator_manifest['counts']['customer_groups']} / {generator_manifest['counts']['documents']}.
- Schema compatibility: {b_schema['compatible_documents']} compatible; {b_schema['incompatible_documents']} incompatible.
- Frozen features: {len(NAMES)}; customer/case/document identifiers, scenario labels, and generator-event fields are excluded.
- Observed documents, canonical facts and labels are separate files with SHA-256 values in `generator_b_manifest.json`.
- Labels are programmatic synthetic gold; no human-reviewed bank truth is present.

## Statistical analysis

The registered bootstrap used {protocol['bootstrap']['draws']} customer-group resamples with seed {protocol['bootstrap']['seed']}. E1 model comparisons are paired. E2 is stratified by scenario. Generalization gaps independently resample the two synthetic datasets. Intervals are conditional on frozen systems and the generated samples; 300 draws have finite Monte Carlo quantile precision and do not guarantee future performance.

Metric denominators are explicit in E1/E2 JSON and prediction-level CSVs. Critical recall is document-level. Review workload is case-level (at least one flagged evidence document). AP is prevalence-sensitive; do not compare it without base-rate context.

## E3 unit and arithmetic audit

E3 has {len(rows)} rows. It charges review costs by flagged case and missed-error costs by false-negative critical document. Costs, volumes, inference charges, and fixed costs are assumptions from `config/cost_scenarios.yaml`; the result is not a bank quote or measured saving.

## Training disclosure

V4 performed no training. There are no V4 epochs, gradients, optimization traces, or V4 training losses to report. The compared learned model weights are frozen V3 artifacts and protected by the baseline manifest.
"""
    (OUT / "STATISTICAL_AUDIT.md").write_text(audit_md, encoding="utf-8")
    return audit, e1, e2, e3


def build_final_manifest():
    baseline = read(OUT / "ARTIFACT_MANIFEST.json")
    outputs = ["E1_RESULTS.json", "E2_RESULTS.json", "E3_COST_RESULTS.json", "experiment_protocol.json"]
    checksums = {name: sha(OUT / name) for name in outputs}
    files = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "final_manifest.json":
            files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "bytes": path.stat().st_size})
    linked = [ROOT / "evidence_ai/v4_generator.py", ROOT / "evidence_ai/v4_experiments.py",
              ROOT / "evidence_ai/v4_business.py", ROOT / "evidence_ai/v4_finalize.py",
              ROOT / "evidence_ai/tests/test_v4.py", ROOT / "backend/app/evidence_research.py",
              ROOT / "backend/tests/test_evidence_research.py", ROOT / "frontend/src/EvidenceResearch.tsx",
              ROOT / "frontend/src/evidence-research.css"]
    for path in linked:
        if path.is_file():
            files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "bytes": path.stat().st_size})
    manifest = {
        "manifest_version": "cobi-evidence-v4-final-1",
        "validation_status": BLOCKED,
        "routing_authorized": False,
        "approval_authorized": False,
        "baseline_manifest_sha256": sha(OUT / "ARTIFACT_MANIFEST.json"),
        "experiment_protocol_sha256": baseline["experiment_protocol_sha256"],
        "experiment_protocol_amendment_sha256": sha(OUT / "EXPERIMENT_PROTOCOL_AMENDMENT_1.json"),
        "checksums": checksums,
        "artifacts": files,
        "artifact_count": len(files),
        "self_hash_excluded": True,
    }
    write_json(OUT / "final_manifest.json", manifest)
    return manifest


def main():
    audit, e1, e2, e3 = build_audit()
    _write_research_docs(e1, e2, e3, audit)
    manifest = build_final_manifest()
    print(json.dumps({"audit": "PASS", "protected_artifacts": audit["protected_baseline_artifacts_verified"],
                      "output_artifacts": manifest["artifact_count"], "manifest_sha256": sha(OUT / "final_manifest.json"),
                      "validation_status": BLOCKED}, indent=2))


if __name__ == "__main__":
    main()
