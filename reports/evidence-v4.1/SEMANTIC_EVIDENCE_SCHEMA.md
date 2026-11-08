# V4.1 Semantic Evidence Schema and Decision Rules

**Scope:** synthetic research only. This specification does not authorize affordability, eligibility, routing, approval, or checkout decisions. `EVIDENCE_AI_VALIDATION_BLOCKED` remains in force.

## Record schema

Each observed record is a normalized financial fact. Its value remains linked to source provenance and its applicable time window.

| Field | Meaning | Validation rule |
|---|---|---|
| `record_id` | Opaque evidence record identifier | Required; never treated as a label or corruption code |
| `subject_ref`, `account_ref` | Entity and account the fact concerns | Missing reference yields comparability `UNKNOWN` |
| `field_type`, `financial_meaning` | E.g. income / salary, debt / recurring debt | Must match across facts; unknown meaning yields `UNKNOWN` |
| `effective_period.start/end` | Dates the fact applies to | ISO dates; both needed for a positive overlap decision |
| `source_type`, `provenance` | Statement/payroll/merchant and document/page/extractor trail | Kept in source-level audit explanations |
| `original_value`, `original_unit` | Amount as extracted and original unit (`VND`, `THOUSAND_VND`, `MILLION_VND`, `UNKNOWN`) | Preserved without replacing the source value |
| `normalized_value`, `normalized_unit` | Amount converted to VND for comparison | Unknown unit or inconsistent conversion prevents comparison |
| `gross_net_basis` | `GROSS`, `NET`, `UNSPECIFIED`, or `UNKNOWN` | Different known bases are not comparable; unknown basis gives `UNKNOWN` |
| `transaction_direction` | `INFLOW`, `OUTFLOW`, `NEUTRAL`, or `UNKNOWN` | Different known directions are not comparable |
| `correction_status`, `correction_of` | Correction lineage (`NONE`, `ORIGINAL`, `CORRECTED`, `SUPERSEDED`, `UNKNOWN`) | A linked superseded/corrected pair is not a contradiction |
| `verification_status` | `VERIFIED`, `UNVERIFIED`, or `UNKNOWN` | Unknown state gives `UNKNOWN`; unverified remains visible in the audit |
| `missingness`, `uncertainty` | Why a value is absent and extraction uncertainty from 0 to 1 | Missing normalized amounts or uncertainty ≥0.75 prevent numeric comparison |
| `asserted_as_current`, `observed_at`, `age_days` | How the evidence is represented to the request and when it was observed | Age alone never defines staleness |
| `ocr_quality`, `text` | Observable extraction quality and source text | Inputs for research features; text is not a canonical truth field |

## Three-valued comparability

For records (a,b), the comparator returns one state and a reason code. Source identity by itself is not a veto.

1. Return `UNKNOWN` if required facts are missing, invalid, have unknown financial meaning/basis/direction/correction/verification, have unnormalizable units, have uncertain extraction (≥0.75), or have incomplete periods.
2. Return `NOT_COMPARABLE` for different subject, account, field, financial meaning, known gross/net basis, known transaction direction, correction-linked versions, non-overlapping periods, or partially overlapping periods.
3. Return `COMPARABLE` only when subject, account, field, meaning, known basis, direction, correction state, normalized currency, and complete effective period match.

Partially overlapping periods return `UNKNOWN` because the supplied generator does not provide a valid aggregation formula for prorating them. Non-overlapping periods return `NOT_COMPARABLE`.

## Contradiction and materiality

Numeric contradiction is evaluated only for `COMPARABLE` pairs. Let (v_a,v_b) be normalized VND amounts and (T_f) be the registered synthetic tolerance for field (f):

\[
\Delta(a,b)=|v_a-v_b|,\quad
\text{material}(a,b)=\mathbb{1}[\Delta\ge T_f],\quad
\text{critical}(a,b)=\mathbb{1}[\Delta\ge 2T_f].
\]

The V4.1 fixture tolerances are income: 500,000 VND; debt: 250,000 VND; purchase: 500,000 VND. These are synthetic study parameters, not bank policy or validated materiality limits. A pair conflict is attached to both source records so a reviewer can inspect both sides; record labels in the challenge identify the corrupted record separately.

The code records the observed difference, tolerance, comparability state, peer record ID, and severity. A numeric difference across incompatible bases, periods, accounts, directions, or correction versions is not itself an alert.

## Time validity

Let (P_r) be the record's effective period, (P_q) the requested period, and (c_r) the observed assertion that the record is current.

- If (P_r=P_q) and `asserted_as_current=true`: `CURRENT_APPLICABLE`.
- If (P_r=P_q) and `asserted_as_current=false`: `HISTORICAL_APPLICABLE`; old age is not an error.
- If (P_r\cap P_q=\emptyset) and the record is asserted current: `STALE_AS_CURRENT`; material at any age mismatch, critical when `age_days >= 180` in this synthetic protocol.
- If periods cannot be compared: `UNKNOWN`.
- If non-overlapping evidence is explicitly historical: `HISTORICAL_NOT_APPLICABLE_TO_REQUEST`, with no defect conclusion by itself.

The 180-day critical-age threshold and numeric tolerances are generator choices. Their transfer to real financial evidence is unvalidated.

## Observable feature contract

`FEATURE_NAMES` in `evidence_ai/semantic_evidence.py` is the frozen 38-column contract. It contains numeric amount/missingness, uncertainty, OCR quality, age, one-hot field/meaning/basis/direction/source/correction state, verification, current assertion, period validity, request-relative dates, counts of comparable/non-comparable/unknown peers, largest comparable log-gap, comparable conflict indicator, and correction-lineage indicator.

Features are built only from observed requests and records. Gold labels, canonical values, group labels, generator event codes, and corruption identifiers are not passed to the feature encoder. Source explanations are emitted alongside predictions and remain read-only.

## Three-valued comparison examples

| Example | Comparator result | Reason | Alert? |
|---|---|---|---|
| Same account and income field, gross vs net | `NOT_COMPARABLE` | `GROSS_NET_BASIS_MISMATCH` | No contradiction |
| Same account and income field, disjoint months | `NOT_COMPARABLE` | `NON_OVERLAPPING_EFFECTIVE_PERIODS` | No contradiction |
| Same amount meaning, different account | `NOT_COMPARABLE` | `DIFFERENT_ACCOUNT` | No contradiction |
| Old record matches a request for that historical month | `COMPARABLE` | `SAME_EFFECTIVE_PERIOD` | No stale alert |
| Old record is claimed current for a later request | Time status `STALE_AS_CURRENT` | `EFFECTIVE_PERIOD_MISMATCH_ASSERTED_CURRENT` | Yes, based on time validity |
| Same-period normalized amount differs ≥ field tolerance | `COMPARABLE` | `SAME_EFFECTIVE_PERIOD` | Pair contradiction; severity uses the registered threshold |
| Missing period, basis, or normalized amount | `UNKNOWN` | Specific missingness reason | No numeric contradiction |

## Known limits

The schema covers the synthetic fields and currencies in this study. It does not model tax treatment, household aggregation, recurring versus one-time income beyond the `financial_meaning` field, exchange rates, reversals across multiple transaction IDs, business ownership changes, legal document validity, or human review policy. Those require additional observed fields and independently labeled evidence.
