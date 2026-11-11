# Metric Specification — Draft 1.0

This contract defines future endpoints, populations and denominators. It reports no V4.2 results. All metrics require a frozen policy/schema version and a group-level split; unresolved labels are retained and reported.

## Evaluation populations

- **Pair population:** all unique claim pairs sampled under the frozen protocol. Comparability can be assessed on all eligible pairs. Relation metrics use adjudicated relations; `UNRESOLVED` is a named class where adjudicated as such, not silently a negative.
- **Attribution population:** individual claims/documents with independent, adjudicated correctness evidence. Exclude attribution-unknown items from correctness metrics; report their count and coverage.
- **Case population:** all sampled cases with an adjudicated criticality/action reference. Keep unknown criticality and missing-source cases visible; do not impute.
- **Shift population:** same frozen task definition, reported by ID/OOD stratum for generator, source, template, period/time, policy, extraction, provenance, entity and prevalence.

## Pair-level endpoints

1. **Comparability:** confusion matrix over `COMPARABLE`, `NOT_COMPARABLE`, `UNKNOWN`; macro-F1 over all three adjudicated classes and per-class precision/recall. Also report coverage: fraction for which the system returns something other than `UNKNOWN`.
2. **Full-pipeline contradiction:** on each eligible pair, positive means adjudicated `CONTRADICTORY`. Report TP/FP/FN/TN, precision, recall, F1 and PR-AUC when a probability target/score is frozen. Denominator is the eligible pair set with adjudicated relationship.
3. **False contradiction by incompatibility:** report contradiction alerts on `NOT_COMPARABLE` pairs / all adjudicated `NOT_COMPARABLE` pairs, and separately on `UNKNOWN` pairs / all adjudicated `UNKNOWN` pairs. A system that emits contradiction while the comparability state is not `COMPARABLE` fails the interface contract; include this rate independently of learned metrics.
4. **Comparable-pair relation:** confusion matrix among comparable pairs for `CONSISTENT`, `CONTRADICTORY`, `SUPERSEDES`, `UNRESOLVED`; report directional supersession accuracy only on adjudicated directed edges.

## Document attribution and probabilities

- Score attribution only for claims/documents independently adjudicated as `VERIFIED_CORRECT` or `VERIFIED_INCORRECT`. Report support, confusion matrix, precision/recall/F1, and abstention/coverage. Separate `UNRESOLVED` and all non-eligible records.
- Any AP, Brier score or log loss must name the exact probability target. The primary attribution target is `Y_doc=1` iff the individually referenced claim/document is independently verified incorrect among attribution-eligible claims; it is not pair contradiction or case criticality.
- If probability of pair contradiction or case criticality is also evaluated, report a separate metric set and target definition for each. Use only probabilities with a calibration/threshold provenance; a score is not a calibrated probability by naming convention.
- Report calibration plot/ECE with fixed predeclared bins as descriptive adjuncts, with group bootstrap intervals; ECE is bin-sensitive and not a standalone criterion.

## Case-level selective-review endpoints

Let `A_c ∈ {NO_FLAG, HUMAN_REVIEW, REQUEST_MORE_EVIDENCE}` be the system's frozen action; let `Y_c=1` denote an adjudicated critical case. Let `N` be the eligible adjudicated case set.

- **Critical-miss risk among cleared cases:** `# {c∈N: A_c=NO_FLAG and Y_c=1} / # {c∈N: A_c=NO_FLAG}`. This is the fraction of cleared cases that are critical. If no cases are cleared, report undefined, not zero.
- **Critical-case miss rate:** `# {c∈N: A_c=NO_FLAG and Y_c=1} / # {c∈N: Y_c=1}`. This is the fraction of critical cases missed.
- **Action workload:** `# {c∈N: A_c != NO_FLAG} / #N`. Report review and evidence-request workload separately as well as combined.
- **Legitimate-case false-review rate:** `# {c∈N: Y_c=0 and A_c != NO_FLAG} / # {c∈N: Y_c=0}`. Also report `REQUEST_MORE_EVIDENCE` separately because it is not equivalent to a defect finding.
- **Risk–coverage curve:** plot critical-miss risk among accepted/cleared cases against coverage `#NO_FLAG / #N`, with workload on a linked axis; show confidence bands and the frozen operating point. Report risk across the full curve, not only one selected threshold.
- **Case precision/recall:** label positive action as a review/evidence request according to the frozen reference action, and state the combined or separate action mapping before opening labels.

The constrained objective is prospective: minimize action workload subject to `UCB_95%(critical-miss risk among cleared cases) <= epsilon`. `epsilon` is `RISK_THRESHOLD_PENDING_DOMAIN_APPROVAL`; no operating threshold is selected in this Phase 1.

## Generalization, robustness and trace

- Report each primary endpoint ID and OOD, absolute gap, relative gap only when denominator is meaningful, worst-group endpoint, and group sizes.
- Stratify by source/template, time, policy, extraction quality, provenance completeness, entity match and prevalence as specified in the preregistration. Do not combine strata that change endpoint meaning.
- **Trace correctness:** fraction of required cited spans/documents whose source ID, hash/version and span resolve to the input and support the stated normalized field; assess transformations independently. Report missing/incorrect traces, not only successful traces.
- **Abstention correctness:** fraction of genuinely unknown/missing cases returning `UNKNOWN`, `UNRESOLVED` or `REQUEST_MORE_EVIDENCE` as policy specifies; separately report unnecessary abstention on resolvable cases.
- **Annotation agreement:** raw agreement and declared chance-corrected statistic by endpoint, plus unresolved/disagreement prevalence.
- **Prevalence sensitivity:** recompute predictive values/workload at predeclared prevalence strata or under transparent reweighting; do not imply population PPV from an artificially balanced challenge.

## Denominator rules

Every table must include positive/negative/unknown support, number of groups, excluded records and exclusion reasons. Document-level, pair-level and case-level denominators never share a label or a denominator column. When a denominator is zero or an interval is undefined, report `NA` with reason.
## Executable denominator contract

`tools/metric_contracts.py` implements denominator helpers that keep pair, document and case units separate. For cases it returns both (a) critical misses divided by all critical cases and (b) critical cases among `NO_FLAG` cases; these answer different questions and must never share one label. Workload counts both `HUMAN_REVIEW` and `REQUEST_MORE_EVIDENCE` as actions, while reporting each cost-bearing action separately. An empty denominator yields `None`/`NA`, never zero. Unresolved document attribution is excluded from correctness denominators and counted as excluded support. Unit tests exercise each distinction.
