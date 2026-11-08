# Generator C — slide-ready evidence

## Slide 1 — Research question

**Can semantic-aware validation catch critical evidence defects without treating valid differences as contradictions?**

- Context is checked before comparing values: subject, account, field meaning, period, units, gross/net basis, direction, correction lineage, source and verification.
- Generator C is a preregistered, independent synthetic challenge. It is not a bank dataset.

## Slide 2 — Evaluation setup

- 840 customer groups · 1,680 cases · 6,791 structured evidence records.
- 7 registered scenarios, including stale-as-current evidence, true comparable conflicts and a held-out payroll+merchant pair.
- Prediction file, model release and threshold were frozen before C labels were opened.
- 500 scenario-stratified customer-group bootstrap draws; no C-based training or threshold change.
- **Construct-overlap caveat:** C2/C6/C7 generated corruption magnitudes use the same field tolerances as deterministic rules, and the C4 stale criterion shares the 180-day cutoff. This is target-construct overlap, not direct hidden-label leakage; 100% recall is not independent validation of those criteria.

## Slide 3 — Frozen semantic hybrid results

| Metric | Result |
|---|---:|
| Critical recall | **520/520 = 100%** (95% bootstrap: 100%–100%) |
| C4 stale-as-current recall | **120/120 = 100%** (95% bootstrap: 100%–100%) |
| C1/C3/C5 legitimate-discrepancy FPR | **0/2,927 = 0%** |
| Overall legitimate-record FPR | **400/6,271 = 6.38%** |
| Cases sent to review | **520/1,680 = 30.95%** (95% bootstrap: 29.5%–32.4%) |
| Material-defect AP | **0.565** (95% bootstrap: 0.562–0.569) |

Use `figures/generator_c_model_tradeoffs.svg` to compare detection and review burden. Use `figures/generator_c_ablation_tradeoffs.svg` to show the feature ablation outcomes.

## Slide 4 — What the false positives show

- All 400 hybrid false positives are valid peers in comparable-conflict scenarios: 160 in C2, 120 in C6 and 120 in C7.
- The pair-level rule flags both records because it cannot infer which side is corrupted without another adjudication signal.
- The semantic rule baseline also achieved 100% critical recall, with 10.38% overall legitimate FPR and 37.08% case workload.

## Slide 5 — Limits and honest conclusion

- D1.1 audit: 100 stale records were missing critical labels across training, validation, calibration and locked development test. Learned feature-effect claims are exploratory.
- Generator C's monetary and stale-evidence gold constructs overlap with deterministic rule criteria. Describe its 100% recall as performance on the generated constructs, not independent semantic-criterion generalization.
- XGBoost replay was blocked by unavailable `xgboost==3.0.5`; the complete registered baseline criterion is unassessable.
- Structured synthetic metadata was supplied; OCR/extraction and real bank documents were not evaluated.
- **Conclusion:** promising performance on this registered synthetic challenge, with unresolved data-label and runtime blockers. `EVIDENCE_AI_VALIDATION_BLOCKED`; no routing or approval use.

## 30-second talk track

"We froze the semantic hybrid before scoring a synthetic challenge with 840 groups and 6,791 evidence records. It detected 520 of 520 labeled critical defects, including 120 of 120 stale-as-current records, with no alerts on 2,927 valid differences in the registered C1/C3/C5 endpoint. Overall it still flagged 400 valid peer records in true-conflict cases and sent 31% of cases to review. One key limit is that some generated gold criteria share monetary tolerances and stale-age logic with deterministic rules, so the result is not an independent test of those criteria. Our development audit also found 100 missing temporal critical labels, and the frozen XGBoost baseline could not run. This is not real-bank validation or authorization for credit decisions."
