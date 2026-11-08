# Slide-ready evidence

## Semantic-aware financial evidence checks — synthetic study

**Generator C · frozen predictions · labels now open · exploratory**

| Measure | Observed result |
|---|---:|
| Critical recall | 520 / 520 · 100% |
| C1/C3/C5 legitimate-discrepancy false alerts | 0 / 2,927 · 0% |
| Overall legitimate-document FPR | 400 / 6,271 · 6.38% |
| Case review workload | 520 / 1,680 · 31.0% |
| Material-defect AP | 0.565 |
| Brier / Log Loss | 0.0339 / 0.0939 |

**Ablation caveat:** the full Logistic Regression and no-temporal variant both had 0/120 stale recall; the Hybrid's 120/120 result includes deterministic rules. No causal feature effect is established.

**Validation:** synthetic only. XGBoost baselines not evaluated. Development stale-label inconsistency found. No real-bank validation or measured operational savings. `EVIDENCE_AI_VALIDATION_BLOCKED`.

*Method note: document metrics use frozen thresholds and customer-group bootstrap; workload is case-level. Generator C differs from V3 and V4 challenge distributions.*
