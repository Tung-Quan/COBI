# COBI V4 Experiment Protocol

**Protocol ID:** `cobi-evidence-v4.0`  
**Registered:** 2026-11-08  
**Registration point:** before Generator B evaluation  
**Bank validation status:** `EVIDENCE_AI_VALIDATION_BLOCKED`

## Research question

Can learned evidence-quality models reduce financial-document verification workload while maintaining critical-error detection performance, and do these improvements remain robust when the synthetic data-generating process changes?

The experiments concern document evidence defects. A defect score is not a probability of loan default, a credit decision, or a real-bank safety guarantee.

## Hypotheses and interpretation

- **H1, cost-safety:** At the existing V3 frozen operating thresholds, each model has a measurable critical-defect recall and case-review workload on the already inspected V3 test. Any V3 comparison is retrospective.
- **H2, distribution shift:** Performance may change on the independently specified Generator B. Differences are reported without a direction-of-effect assumption; both improvements and degradations are valid findings.
- **H3, economics:** Whether any model is cheaper than CS_V2 depends on explicit, configurable assumptions for review, missed-defect, inference, and operating costs. The result is an illustrative scenario simulation, not realized savings.
- No hypothesis asserts a population recall guarantee, bank performance, or positive business value.

## Experimental units and datasets

### E1: V3 retrospective cost-safety frontier

- **Data:** Existing V3 locked synthetic test, 192 cases, 96 customer groups, 753 documents.
- **Unit for document metrics:** evidence document.
- **Unit for review workload:** case; a case is flagged when one or more documents exceed the frozen model threshold.
- **Models:** M0 CS_V2, M1 Logistic Regression, M2 XGBoost, and M3 Deep Sets.
- **Thresholds/calibration:** load the existing calibrators and thresholds from the V3 selection lock. Do not refit or retune.
- **Primary metrics:** critical recall, critical false-negative count/rate, and case review workload.
- **Secondary metrics:** material-defect average precision, Brier score, log loss, document flag rate, precision at threshold, flagged cases per 100 applications, and counts/denominators.
- **Threshold sweep:** descriptive retrospective analysis only; never used to select a release policy.

### E2: Generator B independent synthetic challenge

- **Independent implementation:** a new event-ledger/evidence-scenario generator in `evidence_ai/v4_generator.py`. It must not import or call `evidence_ai.synthetic.generate`, `build_document`, or the V3 format-shift function. It must not implement V3's independent per-field random-delta corruption loop.
- **Sample size:** six predeclared scenarios × 160 customer groups × 2 cases per group = 1,920 cases and 960 customer groups. Each scenario contributes 320 cases and 160 groups. Each case has 2–6 documents to fit the frozen model capacity.
- **Seed:** `20261108` for the generator; generated group identities are unique across scenarios.
- **Common profile law:** one customer profile per group; income is drawn from VND 3–30 million, debt from VND 0–18 million, and purchase amount from VND 1–30 million. Each case draws 2–6 evidence documents. The two cases in a group share the profile but receive independently generated evidence events. `income_history_months` is drawn from 6–24.
- **Label thresholds:** use the registered V3 field materiality values (income VND 500,000; debt VND 250,000; purchase VND 500,000). A field extraction error is material when missing or its observed normalized value differs from that document's canonical normalized value by at least the field threshold; it is critical at twice the threshold or when missing. B4 additionally labels stale evidence presented as current as a material evidence error; it is critical at age 180 days or more. Correctly identified historical evidence is not a defect solely because it is old.
- **Scenario set:**
-  1. **B1 Income reconciliation:** valid income observations use document-specific normalized net/gross or period values (0.80–1.20× profile income). Independently, 12% of documents receive one unexplained field event, selected uniformly across income/debt/purchase: omission or an offset of 1.5–3.0× that field's materiality threshold.
  2. **B2 Duplicate/overlap:** valid recurring debt observations vary within 0.70–1.30× their document-specific canonical value. Independently, 15% of documents contain one duplicate-inflated field summary (20–80% overstatement) with a duplicate transaction reference in observed text.
  3. **B3 Formatting and units:** equivalent text uses predeclared date/currency/decimal locales and varying document order while numeric values remain canonically normalized. Independently, 12% of documents receive one known parsing event: a tenfold or one-tenth amount error, or an omitted value.
  4. **B4 Freshness:** document ages are drawn from 1–365 days. A document older than 90 days that is explicitly marked as historical and applicable is valid. Independently, for 12% of documents older than 90 days, stale evidence is presented as current; those documents are labeled material and become critical at 180 days.
  5. **B5 Legitimate discrepancies:** valid per-document income representations vary within 0.65–1.35× profile income, and debt/purchase within 0.80–1.20×. Independently, 8% of documents receive one unexplained field event using the B1 omission/offset mechanism. The remaining semantically valid differences are negative examples for false-positive analysis.
  6. **B6 Source combinations:** each case uses exactly one of the supported pairs statement+payroll, statement+merchant, or payroll+merchant, selected with equal probability. Independently, 12% of documents receive one field omission or one overstatement of at least twice that field's materiality threshold. No new source type is silently mapped to an existing type; unsupported schema values are counted as incompatible.
- **Feature compatibility:** retain the exact V3 input schema and feature order. A case/document that cannot be represented without semantic substitution is marked incompatible and excluded from model scoring with explicit counts; no silent coercion or replacement occurs.
- **Separate layers:** store canonical generated facts, model-visible observations, and gold labels in separate files. Only model-visible V3-compatible fields may feed predictions. Generator-only metadata and labels are excluded from model features.
- **Gold status:** labels are programmatic synthetic gold, not human-reviewed bank truth.
- **Primary metrics:** critical recall, critical FNR/count, and case workload at the unchanged V3 thresholds.
- **Secondary metrics:** AP, Brier, log loss, document flag rate, precision at threshold, calibration error, compatibility rate, scenario-specific outcomes, and false positives in B5.
- **Generalization gaps:** report `AP_A - AP_B`, `Recall_A - Recall_B`, and `LogLoss_B - LogLoss_A`. A uses the old locked V3 test and B the new independent synthetic generator. Prevalence is reported separately; AP differences are interpreted with that limitation.

## Frozen model and threshold policy

Load the V3 artifacts exactly as registered. Do not retrain, recalibrate, retune thresholds, alter preprocessing, select a different model, or adapt missing-value semantics using Generator B. The primary results include all four registered models. Any model that fails artifact or schema validation is reported as incompatible rather than replaced.

The V3 90% calibration target is a threshold-selection procedure on V3 calibration data, not a guarantee of 90% population recall. V4 uses those frozen thresholds solely for technical comparison.

## Statistical method

- Use 300 bootstrap draws with customer group as the resampling unit, preserving every case/document belonging to the sampled group.
- E1 paired model differences use the same sampled customer groups across models.
- E2 scenario intervals resample customer groups within each scenario. Aggregate B intervals use stratified group resampling so each scenario retains its registered sample size.
- Generalization-gap intervals independently resample V3 test groups and Generator B groups, then calculate the difference for each draw. They condition on frozen models and thresholds.
- Report metric denominators and undefined metrics when a resample or subset lacks the required label class. Do not silently substitute zero.
- Describe the finite Monte Carlo precision of 300 draws; do not present the intervals as guarantees.

## E3 cost sensitivity protocol

- **Measured synthetic inputs:** flagged case rates, critical false-negative counts, documents per case, and inference counts from E1.
- **Assumptions:** VND review cost per flagged case, VND cost per missed critical document, VND inference cost per application, VND fixed operating cost, and application volume. Values are illustrative ranges only and are versioned in `config/cost_scenarios.yaml`.
- **Miss definition:** one false-negative critical evidence document is one missed defect for the cost equation. Review cost is per flagged case. A flagged case and a missed critical document are different units; no event is counted twice within the same cost term.
- **Formula:** `total_cost = flagged_cases * review_cost_per_case + missed_critical_documents * missed_critical_cost_per_document + applications * inference_cost_per_application + fixed_operating_cost`.
- Calculate savings only relative to CS_V2 when baseline cost is positive and defined. Do not call the results realized savings, bank quotations, or observed operating costs.
- Break-even is calculated analytically from the same frozen rates and assumptions. Sensitivity intervals resample synthetic customers; cost-parameter grids are scenario variation, not statistical confidence intervals.

## Model-selection, leakage, and integrity controls

- No model is selected using Generator B. No training is conducted for E1–E3.
- The existing V3 test is explicitly identified as previously inspected and retrospective.
- Keep V2/V3 model files, reports, manifests, and UCI artifacts unchanged.
- Record code/version hashes, seeds, input hashes, model hashes, split counts, thresholds, predictions, commands, exit codes, and limitations.
- Audit that customer IDs, case IDs, document IDs, scenario labels, canonical facts, and gold labels do not enter the frozen feature matrix.
- Preserve the production boundary: learned evidence scores remain read-only research outputs and cannot affect P1 gates, CS_V2, affordability, approval, routing, or human decisions.

## Registered decisions

| Item | Locked value |
|---|---|
| Generator B seed | 20261108 |
| Bootstrap seed | 20261109 |
| Bootstrap draws | 300 |
| Models | V3 M0–M3 frozen release |
| Operating thresholds | Existing V3 selection lock |
| Generator B size | 1,920 cases; 960 customer groups |
| Scenarios | B1–B6 as specified above |
| Cost assumptions | `config/cost_scenarios.yaml` version 1 |
| E4 | Deferred until E1–E3 are complete |
| Real-bank status | `EVIDENCE_AI_VALIDATION_BLOCKED` |

## Limitations known before evaluation

Generator B remains synthetic and programmatically labeled. Its scenario breadth does not establish realism or bank validity. The existing V3 test has already been inspected. The V3 feature schema is narrow and may not represent some semantically rich events without loss; unsupported cases must be counted, not coerced. Cost outputs depend on illustrative assumptions. The 300-draw bootstrap is conditional on the frozen artifacts and registered synthetic samples.
