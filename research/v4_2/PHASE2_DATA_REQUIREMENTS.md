# Phase 2 Data Requirements

Phase 2 remains blocked. No Generator D experiment is authorized by this Phase 1 package.

## Population, permission and sampling

- Name the target institution/workflow, population, period, evidence types and policy versions.
- Obtain documented legal basis, data-owner permission, privacy/security review, retention/deletion rules and publication/redistribution terms before any real evidence is ingested.
- Define sampling frame, inclusion/exclusion, prevalence, unit of sampling and independent customer/economic-group identifier.
- Include representative ordinary cases and challenge cases without letting challenge prevalence masquerade as target prevalence.

## Labels and provenance

- Keep world-state or generator truth separate from observable evidence and reviewer-adjudicated labels.
- Use at least two independent qualified annotators per primary target, a documented disagreement process and an adjudicator; preserve raw ratings and rationale.
- Provide independent source evidence for document attribution. Pair conflict alone is insufficient.
- Capture source/document/version identifiers, source permission, cryptographic hash, span/page, extraction transformations, source issue time, event/valid/recorded time, request as-of period and policy version.
- Report agreement by endpoint and class, unresolved rate, source quality, label coverage and adjudication provenance.

## Splits and leakage control

- Split by customer/economic group; keep all related cases, duplicate records, documents, generated variants and claim groups together.
- Independently hold out source, template, time, policy and generator families; document which shift axes are crossed or confounded.
- Create train, validation, calibration and sealed locked test with independent manifests/hashes and role-based label access.
- Generator C is post-unblinding exploratory only and excluded from confirmatory model selection, calibration, feature selection and threshold choice.
- D1.1 corrected labels are unavailable until independent adjudication and a new immutable version is approved.
