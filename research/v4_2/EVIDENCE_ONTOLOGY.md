# Evidence Ontology and Validation Contracts — Draft 1.0

**Status:** proposed versioned research contract; not a production policy or bank standard.  
**Source status:** informed by the supplied V4.2 protocol and reviewed prior art; no V4.2 outcomes are claimed.

## Design rules

1. Missingness and uncertainty are explicit values (`MISSING`, `UNKNOWN`, `UNRESOLVED`), never converted silently to zero, false, a clean result, or a high-confidence negative.
2. The object being compared and the unit used for the metric are explicit: a pair, a document/claim, or a case are different prediction units.
3. A contradictory pair does not determine which document is wrong, whether either source is fraudulent, or the creditworthiness of a customer.
4. Event time, valid time, recorded time, document issue time and request as-of period are distinct.
5. Synthetic world-state truth and what an independent reviewer can infer from visible evidence are stored separately.
6. Every rule, policy, extraction and transformation is versioned; every claim has a source trace or a declared provenance gap.

## Entity model

| Entity | Required meaning |
|---|---|
| **Case** | A bounded evidence packet for a request with an explicit requested/as-of period and policy version. It is not a credit decision. |
| **Atomic claim** | A normalized assertion attributed to a subject/account, financial metric/basis and period, linked to one document/source/version and extraction span. |
| **Document version** | A source document, its version, source validity/verification state, hash when available, issue/event time, and optional directional supersession link. |
| **Pair annotation** | Two claim IDs; comparability; relation; rationale; and separate attribution states for each claim. |
| **Case reference action** | `NO_FLAG`, `HUMAN_REVIEW`, or `REQUEST_MORE_EVIDENCE`. It is an annotation/evaluation endpoint only. |
| **Annotation record** | Rater, independent evidence references, policy version, rationale, ambiguity and disagreement/adjudication state. |

## Atomic claim contract

`schemas/atomic_evidence_claim.schema.json` requires: claim/case IDs; subject and account identity (nullable when unavailable); financial metric and basis; value and separate value/currency/unit states; economic period; event time; valid-time interval; recorded-at timestamp; intended use (`CURRENT`, `HISTORICAL`, `UNKNOWN`); source and verification state; document ID/version/superseded document; provenance hash/span/transformation IDs; extraction confidence/method/uncertainty; and policy version.

`event_time` means when the underlying event occurred. `valid_time` is when the assertion is modeled as true in the represented world. `recorded_at` is when the system received or recorded the assertion. `period` is the economic period to which the amount applies. A value may be known while currency is missing; that amount is not normalized or compared until a documented conversion makes it comparable.

`source_issued_at` records the source's stated publication/issue time, separately from `recorded_at`; `source_timestamp_state` says whether that time is known, missing, or unknown. Conflicting source timestamps remain visible and do not themselves prove recency, authority, or supersession. Optional `claim_group_id` links multiple records that refer to a normalized financial claim while preserving every record's own source/document/provenance.

## Pair label hierarchy

### Comparability

- `COMPARABLE`: identity, financial metric/basis, period, amount units/currency, source/version context and policy permit the intended comparison.
- `NOT_COMPARABLE`: evidence is known to concern different subjects/accounts/bases/periods or a superseded version under the applicable policy.
- `UNKNOWN`: missing or uncertain facts prevent a defensible determination.

Comparability is evaluated under a named policy. A gross salary and net deposit are not contradictory solely because the numbers differ. Unknown currency, subject or period does not become a negative match.

### Relationship

- `CONSISTENT`: comparable assertions agree within a registered and justified tolerance or accounting transformation.
- `CONTRADICTORY`: comparable assertions disagree materially under the pre-specified policy.
- `SUPERSEDES`: one directed claim/document version replaces an earlier one for an identified validity interval.
- `UNRESOLVED`: current evidence does not support a stronger relationship.

For `NOT_COMPARABLE` or `UNKNOWN`, the validation contract requires `UNRESOLVED`. `SUPERSEDES` requires explicit `superseded_claim_id` and `superseding_claim_id`; ordering is directional.

### Claim/document attribution

Each claim may separately be `VERIFIED_CORRECT`, `VERIFIED_INCORRECT`, or `UNRESOLVED`. A verified attribution requires independent supporting evidence references. Pair contradiction alone must leave both attributions `UNRESOLVED`. The ontology contains no fraud label.

## Case action and truth layers

`case_action` records a reviewer reference action only. It has no `APPROVE`, `DENY`, `ROUTE`, or automated lending action. Its `critical_status` can be `CRITICAL`, `NONCRITICAL`, or `UNKNOWN`.

`truth_status.world_state` (`NOT_AVAILABLE`, `SYNTHETIC_GENERATOR_ONLY`, `INDEPENDENTLY_VERIFIED`) is separate from `truth_status.observable_adjudication` (`UNADJUDICATED`, `INDEPENDENT`, `ADJUDICATED`). A generated canonical value can support a synthetic world-state check but cannot masquerade as what a human reviewer could infer from visible evidence. Preserve both labels and their provenance when both exist.

## Validation sequence and error handling

1. Validate JSON against Draft 2020-12 schemas and examples.
2. Check bundle/case/claim IDs cross-reference consistently; pair endpoints must be claims in the same case; attribution targets must be pair endpoints; supersession endpoints must be distinct pair endpoints.
3. Check that known amounts have numeric values and that currency/unit have their own knownness states; `MISSING`/`UNKNOWN` stays explicit.
4. Check periods and timestamps parse and that an accepted conversion has a transformation ID and reproducible operands.
5. Check policy/rule version, annotation state, provenance references and unresolved reasons.
6. Preserve raw rater labels and disagreement. Do not replace them with a majority label without adjudication policy.

The schemas and eleven example bundles in `schemas/` and `examples/` are illustrative and fully synthetic. They validate interface boundaries; they are not a verified dataset, data policy, bank standard or scientific finding.
