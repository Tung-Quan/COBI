# V4.2 Pre-Registration Draft

**Protocol:** `cobi-v4.2-phase1-draft-v0.1`  
**Status:** `DRAFT_NOT_SEALED`  
**Date:** 2026-11-11  
**Current evaluation status:** no V4.2 experiment run; Generator C remains `POST_UNBLINDING_EXPLORATORY`.

This document is a preregistration template, not a completed registration. It has not been independently frozen or timestamped before test-label access. Generator D is not initiated in Phase 1.

## Questions and outcomes to lock

1. RQ1 comparability versus false contradiction: pair comparability macro-F1; full-pipeline contradiction precision/recall/F1; false contradiction on known non-comparable and unknown pairs; case false-review at matched recall/budget.
2. RQ2 provenance/time: critical stale/cross-source endpoints and frozen ablations for recorded/valid time, provenance, supersession and comparability.
3. RQ3 independent generation and shift: ID-to-OOD gaps, worst-group endpoints and prevalence sensitivity for source/template/time/policy/extraction/provenance/entity strata.
4. RQ4 selective review: critical-miss risk among cleared cases, critical-case miss rate, action workload, legitimate-case false-review, risk–coverage curve and operating-point feasibility.
5. RQ5 granularity: side-by-side pair, individually verifiable document attribution, and case action endpoints; unresolved attribution remains explicit.

Primary endpoint order, meaningful effect sizes, one-sided/two-sided alternatives, and multiplicity family remain to be approved and completed before a confirmatory data lock.

## Population, unit and labels

- Target population: `NOT_SPECIFIED`; requires a named permitted institution/workflow, policy version, date range and sampling frame.
- Sampling unit and split unit: customer/economic group; all linked cases, documents and counterfactuals remain in the same partition.
- Pair labels: `COMPARABLE / NOT_COMPARABLE / UNKNOWN`; relation `CONSISTENT / CONTRADICTORY / SUPERSEDES / UNRESOLVED`.
- Document attribution: `VERIFIED_CORRECT / VERIFIED_INCORRECT / UNRESOLVED` only with independent evidence.
- Case reference action: `NO_FLAG / HUMAN_REVIEW / REQUEST_MORE_EVIDENCE`; no automated credit decision.
- Separate synthetic world-state labels from independent observable/adjudicated labels. Minimum independent rater count: two, with a third-rater adjudication process.

## Candidate and control arms

Historical controls available in the repository include CS_V2 and frozen V3/V4.1 baseline artifacts as listed in `FILE_MAP.md`. Their compatibility, runtime dependencies, licenses and capability across the new ontology must be audited before a candidate-family freeze. V4.1 Semantic XGBoost is `NOT_EVALUATED`; it must not be silently filled in with another model. The new provenance/temporal system is a proposed intervention only. Freeze model candidates and ablation family before collecting/opening independent test labels.

## Data and leakage controls

- Independent benchmark construction from event/world-state ledgers without using evaluated model rules or thresholds to create labels.
- Independent annotation blinded to predictions and generator/corruption codes.
- Hidden test groups/templates/sources and hash-locked manifests; no group/counterfactual overlap.
- Marker and permutation controls, nearest-neighbor/duplicate audit, label access log, and strict audit of every field passed to inference.
- Keep Generator C and D1.1 out of confirmatory tuning; C is already unblinded and D1.1 contains unresolved temporal label omissions.

## Thresholds, analysis and stopping

- Approved risk epsilon: **pending** (`RISK_THRESHOLD_PENDING_DOMAIN_APPROVAL`).
- Calibration split, confidence procedure and operating-point selection code: **pending** an independent dataset/policy and a valid cluster-risk procedure.
- Statistical plan: use `STATISTICAL_ANALYSIS_PLAN.md`, including paired group bootstrap with ≥2,000 resamples, exact interval caveats, Holm correction and power determined from a blinded pilot and approved minimum effect.
- Stopping rule, sample size and minimum practically meaningful changes: **pending domain-owner input**; not selected in this draft.

## Freeze checklist before confirmatory run

Do not run a confirmatory test until each item is completed and independently checked:

- [ ] Named target institution/workflow, approvals, privacy/access conditions and population.
- [ ] Independent labels, source authority, guideline/policy version, rater qualifications and adjudication plan.
- [ ] Resolved D1.1 lesson: new immutable data version, no in-place label correction.
- [ ] Full-text comparison of FinBalance, FinAuditing, FinED-Bench, FinDVer, HC-RAG/Multi-Doc-2025, FinFIRST, EvidenceLens, FinAgent and adjacent reconciliation systems; precise novelty statement.
- [ ] Final schema, transformations, endpoints/denominators and unresolved-label handling.
- [ ] Frozen candidate family, features, calibration method, thresholds and ablations.
- [ ] Group/template/source split manifest, hashes, environment, power/sample-size assumptions and analysis code.
- [ ] Epsilon and risk owner approval; shift assumptions and confidence procedure.
- [ ] Independent timestamped protocol and sealed-test label access controls.

## Registration state

`NOT_REGISTERED_NOT_SEALED`. Any future public registration must link the immutable protocol/version/hash and be timestamped before confirmatory label access. Deviations must be listed rather than silently incorporated.
## Review status and approval dependencies

This draft is not signed, registered, or sealed. Phase 2 must not start until the independent data, adjudication policy, primary endpoint/effect size, epsilon, candidate family, calibration protocol, and sealed-test controls are approved. The implementation-ready supporting protocol is decomposed across `PHASE2_DATA_REQUIREMENTS.md`, `PHASE2_EXPERIMENT_DESIGN.md`, `PHASE2_ACCEPTANCE_CRITERIA.md` and `PHASE2_READINESS_CHECKLIST.md`.
