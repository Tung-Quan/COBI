# Annotation Guidelines — Draft 1.0

**Purpose:** define a reproducible, evidence-grounded annotation process for future V4.2 data. No human annotation or reviewer agreement is claimed by this draft.

## Before annotation

- Freeze the study protocol, schema version, policy versions, target populations, sampling frame, annotation budget and adjudication plan before showing raters evaluation items.
- Recruit at least two independent raters for benchmark gold. Keep rater identity in a controlled key separate from public research exports.
- Provide source documents, claim spans, request context, effective period, document version and the policy in force. Hide model predictions, scores, system decisions and generator/corruption IDs.
- Train raters on a separate practice set and record guideline changes; do not use the final sealed test to revise the rubric.
- Restrict access to personal/financial source data; use permitted synthetic or de-identified evidence when real source authority is unavailable.

## Per-item procedure

1. **Establish scope and identity.** Record what subject/account the claim concerns. If identity cannot be established, mark the relevant field unknown and do not compare the values.
2. **Normalize with a trace.** Record the source amount, unit, currency, metric and gross/net/basis. Apply only policy-authorized transformations. Store the transformation ID, inputs, exchange rate/source and rounding rule. Otherwise preserve the amount but mark comparability unknown.
3. **Establish time.** Record the event time, valid/effective interval, document issue/version time, system recorded time and request as-of period separately. Ask whether the source supports the use for which it is presented. Old age alone is not a defect.
4. **Judge comparability first.** Choose `COMPARABLE`, `NOT_COMPARABLE` or `UNKNOWN` and cite the decisive fields. If not comparable or unknown, set relation to `UNRESOLVED`.
5. **Judge relation.** For comparable items only, choose `CONSISTENT`, `CONTRADICTORY`, `SUPERSEDES` (with direction) or `UNRESOLVED`; cite the applicable policy/tolerance and evidence spans.
6. **Judge each claim separately.** Assign `VERIFIED_CORRECT` or `VERIFIED_INCORRECT` only when independent evidence supports that attribution. Otherwise use `UNRESOLVED`. Never attribute fraud from a pair conflict.
7. **Judge case action.** Select a reference action from `NO_FLAG`, `HUMAN_REVIEW`, or `REQUEST_MORE_EVIDENCE`. Record criticality separately. An unresolved field can justify requesting evidence; it is not evidence of a defect.
8. **Record uncertainty.** Preserve rationale, ambiguity, source gaps, evidence refs, policy version and any unresolved reason. Do not force uncertain labels into binary classes.

## Required edge-case treatment

| Situation | Annotation rule |
|---|---|
| Gross payroll vs net deposit | Mark `NOT_COMPARABLE` unless a complete, authorized netting/reconciliation rule and required data are available. A numeric difference alone is not a contradiction. |
| Same-period values conflict | Mark pair `CONTRADICTORY` only if identity, metric/basis, period, currency/unit and version context are comparable. Keep both document attributions `UNRESOLVED` unless independent evidence identifies an error. |
| Corrected/amended version | Use directional `SUPERSEDES` only with a traceable version relationship and validity scope; retain both versions. |
| Old document supports a historical request | Do not label stale-as-current. Record historical intent and matched valid period. |
| Old document is asserted current | Compare its valid interval with the request as-of period and source validity under a named policy. If the policy is absent/unclear, use `UNKNOWN` / `UNRESOLVED` and request adjudication. |
| Different subject/account | `NOT_COMPARABLE` if the difference is established; `UNKNOWN` if identity is missing. Do not carry a conflict across unrelated entities. |
| Missing currency/period/source validity | Keep the field state missing/unknown, avoid normalization and numeric contradiction, and consider `REQUEST_MORE_EVIDENCE`. |

## Adjudication and agreement

- Store each rater's raw annotation independently. Do not expose another rater's answer before their submission is locked.
- Report raw agreement and a chance-corrected statistic suited to the label/prevalence (Krippendorff's alpha for the selected scale; Gwet AC1 as a sensitivity where rare-label prevalence makes kappa unstable). Specify handling of `UNKNOWN` and missing ratings.
- A third qualified adjudicator resolves disagreements using the same frozen evidence and policy. Retain original disagreements, third-rater decision, rationale and evidence refs.
- Report agreement separately for comparability, relation, document attribution, criticality and case action. A single aggregate agreement score is insufficient.
- If experts cannot determine an answer from available evidence, preserve `UNRESOLVED`; do not convert it to consensus by majority vote.

## Synthetic and observable truth

For synthetic cases, store generator/world-state labels separately from reviewer-observable labels. Keep generator event/corruption IDs out of model inputs. Agreement with a hidden synthetic ledger does not show that a reviewer could determine the answer or that the relation occurs in banking. For real data, document authority, permissions, de-identification and independent evidence sources before annotation begins.

## Version changes

Any material guideline, policy, schema or label change creates a new version and changelog. Re-annotate or formally bridge affected items; never rewrite a released gold file in place. The D1.1 proposals in this release are pending and are not annotations accepted under this guide.
## Record-level and source-time edge cases

- Use a missing applicable period when the document does not specify the period; do not infer that it covers the request period. Comparability is `UNKNOWN` until policy permits an inference.
- Store source issue time and system record time separately. If sources disagree, retain both timestamps, cite the source fields, and mark ordering or relation `UNKNOWN/UNRESOLVED` unless a versioned authority rule resolves it.
- A third source can corroborate one claim only when its independence and authority are established under the annotation policy. Mere agreement among values or a metadata tag is not independent adjudication.
- Several documents may describe one normalized financial claim. Use a shared `claim_group_id` where justified, but keep separate atomic records and provenance; do not deduplicate away source conflicts.
- For every disputed pair, annotate comparability first, relation second, and each document's correctness independently. A contradictory pair with no independent authority leaves both documents `UNRESOLVED`.
