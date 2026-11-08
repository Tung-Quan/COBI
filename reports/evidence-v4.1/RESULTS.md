# COBI V4.1 Results

## Disposition

V4.1 has a completed frozen-output reconciliation on the already opened synthetic Generator C labels. It is a **partial, post-unblinding exploratory evaluation**, not a fresh blind confirmatory test. All research outputs remain read-only and `EVIDENCE_AI_VALIDATION_BLOCKED`.

## Main observed C measurements

Semantic Hybrid: 520/520 critical recall (100%); 0/2,927 C1/C3/C5 legitimate-document false positives (0%); 400/6,271 overall legitimate-document false positives (6.38%); 520/1,680 case review workload (30.95%); material-defect AP 0.5652; Brier 0.03387; Log Loss 0.09390. C4 stale-as-current recall is 120/120 (100%). See [`GENERATOR_C_RESULTS.md`](GENERATOR_C_RESULTS.md) for all denominators, scenario results, CIs and delayed baseline comparisons.

## Interpretation controls

The D1.1 development split has 100 critical temporal-label omissions across train, validation, calibration and locked test. The Hybrid's full recall is materially supported by deterministic rules; C's label constructs share thresholds and stale semantics with those rules. Therefore the observed results do not demonstrate a causal learned-feature improvement. The controlled Logistic ablations show no C4 stale recall in either the full Logistic model or its no-temporal variant.

Replayable frozen non-XGBoost baselines all record 100% critical recall at extremely high legitimate FPR/workload; XGBoost is `NOT_EVALUATED`. This is an incomplete registered baseline comparison, so no all-baseline superiority claim is made. No real banking evidence, measured operational savings, or regulatory validation is available.

The scientific answer is **suggestive but inconclusive**: semantic-aware rules and representations align with strong C outcomes on the registered synthetic constructs, but label inconsistency, rule-target overlap, and incomplete baseline replay prevent a confirmatory generalization claim. Maintain `EVIDENCE_AI_VALIDATION_BLOCKED`.
