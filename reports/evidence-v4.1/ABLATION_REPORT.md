# Semantic-Aware Ablation Audit

All C values below come from already frozen predictions and thresholds. This is a post-unblinding descriptive audit. The three registered ablations are Logistic Regression variants; the complete Semantic Hybrid combines deterministic semantic rules with the full Logistic Regression arm. It is not a like-for-like ablation comparator.

| Frozen configuration | Registration | Critical recall | C4 stale recall | Legitimate FPR | C1/C3/C5 FPR | Case workload | AP |
|---|---|---:|---:|---:|---:|---:|---:|
| SEMANTIC_LOGISTIC | 25/520 (4.81%) | 0/120 (0.00%) | 56/6271 (0.89%) | 0/2927 (0.00%) | 81/1680 (4.82%) | 0.3731 |
| ABLATION_NO_TEMPORAL | 29/520 (5.58%) | 0/120 (0.00%) | 65/6271 (1.04%) | 0/2927 (0.00%) | 94/1680 (5.60%) | 0.1558 |
| ABLATION_NO_COMPARABILITY | 179/520 (34.42%) | 120/120 (100.00%) | 1349/6271 (21.51%) | 494/2927 (16.88%) | 1058/1680 (62.98%) | 0.3337 |
| ABLATION_NO_SOURCE_PROVENANCE | 78/520 (15.00%) | 0/120 (0.00%) | 619/6271 (9.87%) | 260/2927 (8.88%) | 581/1680 (34.58%) | 0.0876 |
| Semantic Hybrid (rules + full LR) | Registered hybrid | 520/520 (100.00%) | 120/120 (100.00%) | 400/6271 (6.38%) | 0/2927 (0.00%) | 520/1680 (30.95%) | 0.5652 |

## Interpretation by feature family

- **Temporal validity:** The complete semantic Logistic arm and `ABLATION_NO_TEMPORAL` both detected 0/120 C4 stale critical records. The Hybrid detected 120/120 because it includes deterministic temporal rules. Thus the statement “removing temporal features reduced stale recall to 0%” is false for the controlled Logistic-vs-Logistic comparison: recall was already 0% in the full LR arm. The Hybrid result cannot isolate temporal feature value from its deterministic rule path.
- **Comparability:** Removing comparability increased LR critical recall from 25/520 (4.81%) to 179/520 (34.42%) at the frozen arm thresholds, while legitimate FPR rose from 56/6,271 (0.89%) to 1,349/6,271 (21.51%) and workload from 81/1,680 (4.82%) to 1,058/1,680 (62.98%). This is a threshold/ranking trade-off, not evidence of improvement from removing semantics.
- **Source/provenance:** Removing source/provenance yields 78/520 critical recall (15.0%), 619/6,271 legitimate FPs (9.87%), and 581/1,680 flagged cases (34.58%). The observed degradation is descriptive and also inherits development-label and calibration limitations.
- **All learned ablations:** D1.1 temporal labels are inconsistent in all model-development partitions: 100 critical stale labels are missing (60 train, 15 validation, 15 calibration, 10 locked test). The selected model and threshold are unchanged; their attribution claims are weakened.

## Feature leakage and rule-target overlap

The observable encoder reads only each record and request context. Code inspection found no reads of canonical truth, gold-label files, scenario labels, customer group IDs as features, event/corruption IDs, or generator-only corruption markers in feature construction. The challenge predictor consumes the frozen observed records and writes predictions before labels open.

However, observable semantic flags include `has_comparable_conflict` and `stale_as_current`, and the deterministic rule thresholds/logic align with the label constructor: both use income/debt/purchase tolerances of VND 500k/250k/500k; the generator creates controlled conflicts around these thresholds; both define critical stale age at 180 days. This is not direct access to hidden gold, but it is construct and rule overlap. C is independent in implementation path, seed, templates, and held-out source pair; it is not independent of the semantic criteria encoded in the rule and labels. That is a generator-dependent shortcut risk and limits external validity.

The C4 rule also evaluates temporal validity on all records, including side-field documents. The semantic rule alone has elevated C4 false positives/workload as shown in the scenario table; the frozen Hybrid's calibrated learned layer changes its operating point. This scoping behavior deserves a new, independently registered test rather than a C-informed code change.
