# Ontology and Fixture Consistency Audit

## Contract checked

Draft schema release is `cobi-evidence-bundle-1.0`; atomic claim, pair, annotation, case-action and bundle JSON Schemas use JSON Schema Draft 2020-12. Claims retain observed value and provenance; `claim_group_id` optionally links multiple records about a normalized claim without collapsing record identity. Source-issued timestamp is distinct from record capture time and has an explicit `KNOWN/MISSING/UNKNOWN` state.

Pair comparability is three-state. A pair with `NOT_COMPARABLE` or `UNKNOWN` must have `UNRESOLVED` relation. `SUPERSEDES` requires a directional old/new claim reference. Contradiction does not identify an incorrect document; verified attribution requires independent evidence references. Case action is research-only and contains no lending authorization.

## Fixtures

All JSON examples under `examples/` are schema-validated. The 7 original fixtures plus 4 added edge cases cover gross/net difference, same-period conflict with unresolved attribution, supersession, historical-valid evidence, stale-as-current, different subjects, unknown currency, missing applicable period, a third-source reference, conflicting source timestamps, and multiple document records linked to one claim. Every example is illustrative, not a gold label. The third-source example deliberately keeps attribution unresolved until source authority and adjudication are independently established.

## Deterministic checks

`tests/test_contracts_and_audit.py` validates schema shape, every fixture, cross-case and pair-to-claim references, supersession direction, unknown-state invariants and attribution evidence. The audit also verifies that every `claim_group_id` is local to a case and that timestamp state is not silently inferred from a missing timestamp. D1.1 review rows are separate from evidence bundle gold and all remain pending.

## Findings and limitations

- The current JSON Schema can enforce structure and selected invariants but cannot establish semantic truth, source authority, reviewer qualification, or that a cited hash/span matches a source document.
- `claim_group_id` is optional to preserve the draft fixture schema; Phase 2 governance must decide its canonicalization rules.
- External `independent_evidence_refs` may refer to source IDs outside the bundle; referential validation therefore cannot prove their independence.
- Schema validity must not be reported as annotation validity.

**Final closeout scoped suite:** 13 passed, including the V4 manifest path-case audit regression check; the command and full verification context are recorded in `FINAL_VERIFICATION_REPORT.md`.

