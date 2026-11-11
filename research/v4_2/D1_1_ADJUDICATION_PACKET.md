# D1.1 Independent Adjudication Packet

**Dataset:** `semantic-evidence-development-d1.1`  
**Purpose:** review candidate label disagreement only; this packet is not approved training gold.  
**Status:** `PENDING_ADJUDICATION`

## Question for reviewers

For each evidence record, determine whether the record is a critical stale-as-current defect **for the specific request and policy version**, using source meaning and as-of semantics. Do not use record age alone as the decision rule. The registered V4.1 rule is shown as evidence about the existing implementation, not as an independent answer key.

## What the audit found

The audit-only replay found 200 `STALE_AS_CURRENT` records. For 100 records, the current temporal rule returns `critical=true` while programmatic gold has `critical_defect=0`. Those candidates are split train 60, validation 15, calibration 15, locked test 10. The candidate rows are in `D1_1_LABEL_REVIEW.csv`; each row retains synthetic input/context, old label, candidate, generator/rule provenance, evidence pointers, and empty reviewer fields.

## Evidence layers to keep separate

1. **Generator intent:** D4 `HISTORICAL_VALIDITY` selected the deliberately altered record using `critical_idx`. This is a construction trace, not world-state truth.
2. **Rule assessment:** `evidence_ai/semantic_evidence.py::time_validity` evaluates current assertion versus effective/request periods and the synthetic 180-day critical threshold. This is the result of a versioned program rule.
3. **Independent target:** whether this evidence is materially invalid for the request under an approved source/freshness policy. This is not established until reviewers adjudicate.

## Required review procedure

- Reviewers should be independent of the generator and model authors where feasible, and qualified to interpret the agreed evidence policy.
- Review the cited observed record and its request context; consult available source/version lineage. Do not view model outputs or use the candidate correction as a hint beyond the documented rule disagreement.
- Record one decision: `ACCEPT_CORRECTION`, `REJECT_CORRECTION`, `UNRESOLVED`, or `POLICY_CLARIFICATION_REQUIRED`.
- Record a concise rationale, reviewer identity, date, policy version and supporting independent evidence. Preserve each individual rating before adjudication.
- Escalate policy-dependent cases to the designated policy owner. Two agreeing reviewers do not substitute for missing policy authority.
- Keep locked-test labels blinded from model developers. If the locked test was already exposed through prior analysis, classify it exploratory and make a new sealed test for confirmation.

## Review form

`D1_1_LABEL_REVIEW.csv` contains 100 rows. `reviewer_decision`, `reviewer_justification`, `reviewer_name`, and `review_date` are intentionally blank. Every row says `PENDING_ADJUDICATION` and `approved_gold=NO`. Allowed decisions are the four values above. Do not fill these fields by automation or copy the temporal-rule output into reviewer decision.

## Gate

`GOLD_CORRECTION` remains **BLOCKED** until a qualified independent review is completed, policy owner signs the semantic definition, disagreement is resolved or retained as unresolved, and a new immutable dataset version plus manifest is approved. The original gold file and all current splits remain unchanged.
