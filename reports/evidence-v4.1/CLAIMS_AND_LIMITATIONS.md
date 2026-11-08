# Claims and Limitations

## Supported by the current artifacts

- V4's frozen Generator B results document severe synthetic failures in stale evidence (B4), legitimate differences (B5), and source-pair transfer (B6).
- On the already unblinded, registered synthetic Generator C labels, the frozen Semantic Hybrid recorded 520/520 critical detections, 0/2,927 false alerts in C1/C3/C5, 400/6,271 overall legitimate false alerts, 520/1,680 cases flagged, AP 0.5652, Brier 0.03387, and Log Loss 0.09390.
- Group bootstrap intervals and cluster-aware boundary uncertainty are conditional descriptive uncertainty summaries.
- The C1/C3/C5 and C4 result patterns are consistent with semantic and temporal checks being useful in this generator. They do not isolate causal effects.
- Paired, delayed, frozen-output comparisons are available for CS_V2, frozen V4 Logistic and Deep Sets, semantic rule, semantic Logistic and semantic Deep Sets.

## Not supported

- “Guaranteed 100% recall,” zero population risk, statistical assurance of no false positives, or safe automated evidence decisions.
- Superiority to all registered baselines; both XGBoost arms are NOT_EVALUATED and the full baseline acceptance rule is incomplete.
- A causal statement that learned temporal or comparability features produced the Hybrid's results. The D1.1 label mismatch and non-like-for-like hybrid/ablation design prevent it.
- Real financial document accuracy, bank authenticity validation, approval eligibility, regulatory readiness, or generalization to institutions not represented by the generator.
- Measured workload reduction or operational cost savings. Review workload is a synthetic case flag rate, not a time-and-motion study.

## Why the result remains exploratory

Generator C was frozen and scored before label unblinding, and no C-informed tuning was done. However, an after-training audit found that 100 D1.1 stale-as-current critical labels were missing across train, validation, calibration and locked test. Additionally, C's synthetic gold and semantic deterministic checks share financial tolerance and temporal constructs. These issues do not change the frozen C metrics, but weaken attribution and construct independence. The labels and outputs must not be represented as a blind confirmation of the final learned system.

## Required validation before any external claim

Correct and independently audit development labels; pre-register a new challenge with independently specified label adjudication and criteria; evaluate all frozen model families under exact environments; collect privacy-governed, independently reviewed real-document evidence; measure extraction quality, subgroup error, calibration and operational review time; complete legal, security, model-risk and regulatory review. Until then maintain **`EVIDENCE_AI_VALIDATION_BLOCKED`** and keep all research outputs read-only and out of checkout decisions.
