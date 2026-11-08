# Semantic-Aware Financial Evidence Validation under Synthetic Distribution Shift

## Abstract

Financial evidence screening must distinguish true contradictions from valid differences caused by reporting periods, subjects, accounts, units, gross/net basis, transaction direction, and correction history. We report an exploratory evaluation of a frozen semantic rule-plus-model hybrid on a preregistered independent synthetic challenge with 840 customer groups, 1,680 cases, 6,791 structured evidence records, and 520 labeled critical records. At its frozen operating threshold, the hybrid detected 520/520 critical records, including 120/120 stale-as-current records, and flagged 0/2,927 legitimate records in the C1/C3/C5 endpoint. Overall it flagged 400/6,271 legitimate records, yielding a 6.38% legitimate-record FPR, and sent 520/1,680 cases to review. Material-defect AP was 0.565; Brier score was 0.0339 and log loss 0.0939. However, a post-evaluation audit identified 100 missing critical labels among stale records in the D1.1 development data, the frozen XGBoost baseline could not be replayed, and 400 valid peer records were flagged in comparable-conflict scenarios. Findings are exploratory synthetic measurements; they do not demonstrate real-document or bank performance.

## 1. Introduction

Evidence validation systems can over-flag when numeric disagreement is treated as a contradiction without checking whether records describe the same person, account, field meaning, period, units, or transaction direction. A second challenge is temporal: evidence can be historically accurate yet invalid when asserted as current for a later request. This study evaluates a semantic-aware representation and hybrid detector under a deliberately constructed distribution shift. The research goal is to test an explicit synthetic challenge, not to validate a lending policy.

## 2. Research question

Can semantic-aware financial-evidence validation maintain critical-defect detection while reducing alerts on valid non-comparable differences and stale evidence under an independent synthetic generator?

The preregistered outcomes are material-defect average precision, critical recall and false-negative count, C1/C3/C5 legitimate-discrepancy FPR, C4 stale-as-current recall, C7 held-out source-pair critical recall, case review workload, calibration losses, and scenario/source strata.

## 3. Method

### 3.1 Synthetic challenge

Generator C (`semantic-ledger-c-v1.0`, seed 2026110802) is implemented independently from the development and Generator B paths. The challenge includes seven scenarios: gross/net and period differences; same-period corruption; correction lineage; time validity; different subjects/accounts; genuine comparable conflict; and a held-out payroll+merchant source pair. The target design is 120 groups per scenario and two cases per group. The observed release has 840 groups, 1,680 cases, and 6,791 evidence records. Canonical truth and event identifiers are excluded from prediction inputs.

### 3.2 Models and information controls

Models and operating thresholds were frozen before Generator C labels were opened. The semantic hybrid combines deterministic semantic checks with a calibrated learned score. Generator C was not used to retrain, calibrate, select a model, or alter a threshold. The post-unblinding reconciliation recomputed metrics and verified that aggregate values match the original frozen evaluation.

Registered XGBoost arms could not be replayed because the offline runtime lacked `xgboost==3.0.5`. They are recorded as unavailable; no substitute is reported under the XGBoost label.

### 3.3 Metrics and uncertainty

Critical recall is detected critical records divided by critical-record support. The registered C1/C3/C5 endpoint is false alerts divided by legitimate records in those three scenarios. Overall legitimate-record FPR uses all labeled legitimate records. Case review workload is the proportion of cases with at least one flagged record. The evaluation reports 500 scenario-stratified customer-group bootstrap percentile intervals. These intervals are conditional on the synthetic generator, labels, frozen models, and thresholds. Exact group-level binomial bounds are reported separately where relevant.

## 4. Results

The semantic hybrid achieved 520/520 critical recall (100%), 120/120 C4 stale-as-current recall (100%), 0/2,927 C1/C3/C5 legitimate false positives, and 120/120 C7 critical recall. Overall, it flagged 400/6,271 legitimate records (6.38%) and 520/1,680 cases (30.95%). Material-defect AP was 0.565 (95% cluster bootstrap interval 0.562–0.569), Brier score was 0.0339 (0.0319–0.0358), and log loss was 0.0939 (0.0884–0.0992). The 95% bootstrap intervals for critical recall and C4 recall were both 100%–100%; the workload interval was 29.5%–32.4%.

The 400 false alerts consisted of 160 legitimate peers in C2, 120 in C6, and 120 in C7. The pair-level comparator raises review for both sides of a true comparable conflict when it cannot identify which item is corrupted. Frozen CS V2, Logistic Regression, and Deep Sets also reached 100% critical recall but flagged approximately all legitimate records and routed nearly every case to review. Semantic rules alone reached the same point recall with a 10.38% overall legitimate FPR and 37.08% workload.

The full semantic Logistic Regression had 4.8% critical recall and 0% C4 recall. Its no-temporal ablation also had 0% C4 recall. Removing comparability features increased logistic critical recall to 34.4% while increasing overall legitimate FPR to 21.5% and case workload to 63.0%. Because the D1.1 temporal-label audit found missing critical labels in development partitions, these ablations are descriptive and cannot support causal feature-effect claims.

Generator C was independently implemented, but its gold criteria are not independent of the deterministic rules at the construct level. C2/C6/C7 generate conflicts at 2.1-4.2 times the same field tolerances used by the comparator, which treats differences of at least two times tolerance as critical. C4 uses a 180-day critical-staleness criterion also used by the semantic time rule (the generated stale record is 432 days old). The canonical gold and corruption identifiers are not model inputs, so this is target-construct overlap rather than direct hidden-label leakage. It limits the 100% recall result as evidence of external or independently adjudicated generalization.

Four of the five registered acceptance point-estimate criteria were met. The complete comparison against the best frozen baseline is unassessable because the XGBoost baseline is unavailable, so the full criterion package remains incomplete.

## 5. Discussion

The measured synthetic result illustrates why detection and review burden should be reported together. The frozen V3 baselines attained full critical recall on this challenge by flagging almost all evidence, while the hybrid retained full observed recall with a smaller alert and case-review fraction. The hybrid's zero observed alerts on C1/C3/C5 is specific to the registered endpoint and sample. The separate group-level analysis found 0/360 groups with any endpoint false positive; the one-sided 95% exact upper bound for that group event is 0.83%. A conservative equal-group-weighted FPR upper bound was 6.45%. Neither bound covers generator misspecification.

The paired rule flags legitimate peers in same-period contradiction scenarios, showing that semantic comparability alone does not identify the faulty member. Independent adjudication or additional source reliability evidence would be needed to resolve that ambiguity. Further, hybrid recall includes deterministic rules and should not be attributed to learned representations.

## 6. Limitations

All records, labels, and metadata are synthetic. The evaluation supplies structured evidence semantics and does not measure OCR or extraction errors. The finite scenario set and one held-out source pair cannot represent the breadth of financial products and document workflows. Generator C is independent in implementation path, seed, and templates, but its monetary and stale-evidence gold constructs share key criteria with deterministic rules; this target-construct overlap means the 100% recall is not fully independent semantic-criterion validation. It is not direct hidden-label leakage because canonical gold and corruption identifiers are absent from prediction inputs. Separately, 100 D1.1 records identified as stale-as-current by the temporal rule lacked critical labels across training, validation, calibration, and locked development test. This weakens learned temporal feature evidence and makes feature attribution exploratory. The XGBoost runtime blocker prevents complete registered baseline comparison. Bootstrap intervals are conditional on the synthetic process and do not provide real-world uncertainty guarantees.

## 7. Conclusion

On the registered synthetic Generator C data, the frozen semantic hybrid detected all labeled critical records while avoiding alerts on the registered C1/C3/C5 endpoint, with 6.38% overall legitimate-record FPR and 30.95% case review workload. These results are exploratory, not bank validation. A corrected and independently audited development labeling process, successful replay of all registered baselines, and a new independent challenge are required before claims of general improvement. No operational routing or lending authorization follows from these results.

## Data and software availability

Frozen predictions, manifests, evaluation results, reconciled metrics, protocol, model availability status, and presentation tables are in this repository under `reports/evidence-v4.1/`. Prediction, labels, and manifest checksums are captured in the release manifests. Checkout does not consume these research outputs.
