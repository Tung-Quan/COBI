# Mathematical methodology · historical V1

The formulas and anchor values below are the V1 record. See the [V2 formula changelog](FORMULA_CHANGELOG_V1_TO_V2.md) for the current workbench.

V3 evaluates learned document-error probabilities in a separate research lane. CS_V2 remains the workbench evidence index. For the learned formulation, calibration, thresholds and authorization boundary, see the [V3 evidence protocol](EVIDENCE_LEARNING_PROTOCOL_V3.md).

This document describes the running implementation. The four reference files named in the original brief were not supplied, so formulas and numeric anchors below are separated from unverified prototype assumptions. No bank thresholds, training results, repayment outcomes or measured business improvements are asserted.

## P1 — Mandatory input checks

The current hard gates are consent, simulated identity success, source permission and funding reconciliation. A failed gate stops automated scoring. The returned assessment has `scoring_performed=false` and null features, CS, PD and expected loss. Routing exposes only `HOLD_FOR_HUMAN_HANDLING`.

These flags describe synthetic fixtures. They do not replace real consent management, identity verification, source permissions, or payment ledger reconciliation.

## P2 and P3 — Evidence and financial features

Monthly income observations are treated as synthetic VND amounts. The deterministic engine computes:

- Mean: arithmetic mean of the supplied monthly values.
- Standard deviation: population standard deviation.
- Income coefficient of variation: population standard deviation divided by mean income.
- P25: the lower observation selected at the 25th percentile index of the sorted history.
- Existing DTI: existing monthly debt divided by mean monthly income.
- History coverage: observed months divided by 12, capped at 1.
- Residual income: mean income less existing monthly debt and essential monthly expenses.

`evidence.sources` describes the synthetic input provenance. Counts for reconciliation and verification are included in the response. No live financial data connectors are configured.

## P4 — Evidence Confidence Score

The configured weights are validated to be non-negative, individually at most one, and sum to one:

```text
CS = 0.30 × Coverage
   + 0.30 × Consistency
   + 0.20 × Recency
   + 0.20 × Verification
```

- Coverage = observed income history months / 12, capped at 1.
- Consistency = consistent reconciliation fields / total reconciliation fields.
- Recency = `exp(-age_days / 40)`; 40 days is a configurable demonstration assumption.
- Verification = verified evidence sources / available evidence sources.

CS is an evidence quality index, not a probability. Mandatory gates remain separate and cannot be offset by a high CS.

## P5 — Affordability

```text
Income residual = mean monthly income − existing monthly debt − essential expenses
Stressed payment capacity = max(0, mean monthly income × illustrative max DTI − existing monthly debt)
Repayment buffer = stressed payment capacity − proposed installment
```

The default maximum DTI is 35%, an explicitly illustrative assumption. Installment eligibility requires positive residual income, a positive installment, and non-negative repayment buffer. It is not a bank affordability policy.

When both annual interest rate and term are supplied, the engine also calculates a standard amortizing PMT; with a zero rate it calculates principal / term. DEMO-001 uses a zero-rate, four-month arithmetic example to make its 2.4m VND payment transparent.

## P6 — Risk demonstration

The score is a logistic transformation:

```text
PD_demo = sigmoid(intercept + 3.00 × existing DTI + 1.50 × income CV + 0.80 × evidence gap)
sigmoid(x) = 1 / (1 + exp(−x))
evidence gap = 1 − CS
```

The intercept is anchored to the expected DEMO-001 PD (`0.039675`) supplied in the implementation brief at its seeded feature values. Slopes are demonstration parameters, not the unavailable prototype's coefficients. The label is `DEMO_RISK_SCORE_NOT_CALIBRATED`; it has no trained data, calibration evidence, or validated predictive meaning. Replace this module through the `demo_risk_score` function boundary when a trained and independently validated bank model is available.

## P7 — Expected loss

```text
EL = PD_demo × LGD_assumption × EAD_assumption
```

The fixture uses illustrative LGD `0.45` and EAD `6,666,600 VND` to reproduce the prompt's approximate DEMO-001 expected loss. Neither is a validated loss-given-default or exposure assumption.

## P8 — Review routing objective

Hard gate failures yield only `HOLD_FOR_HUMAN_HANDLING`. With gates passed, the policy filters route eligibility using illustrative conditions: fast-track requires CS at least 0.75, PD at most 0.10 and affordability eligibility; low evidence (CS below 0.50) or high demo PD (above 0.25) allows only enhanced review. Otherwise standard and enhanced remain available. The lowest estimated route cost among eligible options is selected. Ties use a stable route order. All four thresholds are exposed by `GET /api/assumptions`.

Default demo cost assumptions (VND):

| Route | Cost |
|---|---:|
| `HOLD_FOR_HUMAN_HANDLING` | 95,000 |
| `FAST_TRACK_CANDIDATE` | 42,000 |
| `STANDARD_REVIEW` | 110,000 |
| `ENHANCED_REVIEW` | 180,000 |

These costs and eligibility thresholds are visible and editable in the simulator. They are not values recovered from the missing prototype and are not bank-validated. Changing the cheapest route does not change eligibility.

## P9 and P10 — Human actions and evaluation

Review actions are confirm route, request evidence, escalate, or change to another eligible route. Every action requires a non-empty reason. Events are timestamped and stored append-only; no approval endpoint exists. Evaluation counts and route costs are calculated only over synthetic seed cases and are labelled as simulated, not measured.
