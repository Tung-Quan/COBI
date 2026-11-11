# Phase 2 Acceptance Criteria

These criteria are a proposed approval checklist, not current pass results.

1. **Data legality and relevance:** approved population, documented rights/privacy/security, independent source sample, documented source/time/policy distribution and target prevalence.
2. **Gold quality:** dual independent labels, adjudication, preserved disagreement, independently supported document attribution, and reported agreement/coverage by target.
3. **Leakage:** group-safe split; duplicate/customer/template/source/generator marker audits; train/validation/calibration/test non-overlap; locked labels access controlled.
4. **Interface:** versioned schemas validate all records; tri-state comparability is preserved; unresolved contradictions do not create document error attribution; actions do not imply lending decisions.
5. **Statistics:** endpoints and denominators frozen; sample design/power inputs approved; paired group intervals and multiplicity specified; risk tolerance approved; no zero-event overclaim.
6. **Model selection:** all model families/features/search spaces/calibration methods frozen; validation and calibration are separate; Generator C and unapproved D1.1 labels excluded.
7. **Risk:** selected action policy meets the approved one-sided upper bound on the defined critical-miss risk in the locked population; OOD guarantee scope is explicit. If it fails, acceptance fails and fallback actions are reported.
8. **Reproducibility:** immutable data/model/analysis manifests, exact environment/commands/seeds, complete output hashes and independent reproduction.
9. **Communication:** all negative results, uncertainties, exclusions, shift limitations and deviation logs are published; no bank-validation, savings, fraud or regulatory claims beyond evidence.
