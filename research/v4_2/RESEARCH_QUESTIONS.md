# Research Questions and Testable Hypotheses — Draft

All questions are prospective. Generator C is already unblinded and is descriptive/exploratory only. No V4.2 model is trained and no results are stated here.

## RQ1 — Comparability and false contradiction

**Question:** Does an explicit comparability stage reduce false contradiction alerts on legitimate differences, including gross/net, different periods/accounts, and incomplete values, without unacceptable critical conflict misses under distribution shift?

**H1:** Compared with frozen controls at matched operating conditions, explicit `COMPARABLE / NOT_COMPARABLE / UNKNOWN` predictions reduce pair false-contradiction rate on adjudicated non-conflict pairs and reduce case false-review rate at matched critical recall or approved review budget. Estimate paired differences with group-cluster intervals. If effects fail the predeclared useful-difference criterion, reject H1.

## RQ2 — Provenance and temporal semantics

**Question:** Do source provenance, valid/recorded time, version lineage and as-of semantics improve detection of critical stale-as-current or cross-source conflict beyond values and baseline rules?

**H2:** Removing each pre-registered component from an otherwise fixed candidate family worsens its targeted endpoint under an independent test, while leaving legitimate historical evidence valid. This is an ablation hypothesis, not a causal claim based on non-equivalent V4.1 systems. If ablations show no effect or marker controls fail, reject H2.

## RQ3 — Generator independence and distribution shift

**Question:** How do endpoints change across independent generators, source/template combinations, time, policy, extraction quality, entities and prevalence?

**H3:** Report ID-to-OOD changes and worst-group values; do not pre-assert robustness. “Robust” is permitted only if the lower confidence bound passes a criterion approved by the domain risk owner before test labels are opened. A single synthetic generator cannot establish independent-generator generalization.

## RQ4 — Risk-constrained selective review

**Question:** Can a frozen system reduce the fraction of cases needing action while meeting an approved upper bound on critical misses?

**H4:** A separately calibrated operating point will meet the pre-approved risk constraint and workload objective on a sealed independent test. If no operating point qualifies, report `NO_CERTIFIED_OPERATING_POINT`. Do not choose epsilon for a bank; current state is `RISK_THRESHOLD_PENDING_DOMAIN_APPROVAL`.

## RQ5 — Pair, document and case evaluation

**Question:** How do conclusions differ when relation detection, independently verifiable document attribution and case action are evaluated separately, especially when attribution is unresolved?

**H5:** System rankings or uncertainty may differ across pair/document/case units; report all three and the fraction with unresolved attribution. If conclusions do not differ, report that negative finding. Never assign a document error or fraud label from pair contradiction alone.

## Populations and blocking assumptions

- Primary future population: permitted evidence cases from a defined institution/workflow, policy version and date range, with independently adjudicated reference labels. That population is not yet available.
- Synthetic benchmark population: cases generated under each declared generator/configuration. Inference is conditional on those generators and sampling strata only.
- Unit of partition/resampling: customer/economic group, including all cases, documents and counterfactual variants for that group.
- Unknown/unresolved items are reported and excluded only from endpoints whose target cannot be assigned; coverage and exclusion reasons are always given.
- Domain risk owner, independent annotators, source permissions, target workflow, policy version, and pre-test epsilon are prerequisites, not assumed facts.
