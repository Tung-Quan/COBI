# Data dictionary

All values are synthetic. Currency amounts are Vietnamese dong (VND).

| Field | Type | Meaning / provenance |
|---|---|---|
| `application_id` | string | Synthetic case identifier, primary key |
| `borrower_label` | string | Synthetic display label; no real identity |
| `merchant`, `purchase_description` | string | Synthetic merchant and item description |
| `purchase_amount_vnd` | number | Synthetic checkout total |
| `loan_amount_vnd` | number | Demonstration requested amount |
| `proposed_installment_vnd` | number | Proposed monthly payment used for affordability |
| `term_months`, `annual_interest_rate` | number or null | Inputs for the PMT example; PMT is omitted if either is missing |
| `submitted_at` | ISO date string | Synthetic application timestamp |
| `consent` | boolean | Mandatory synthetic borrower consent gate |
| `identity_verified` | boolean | Mandatory simulated identity check; not a real KYC result |
| `source_permission` | boolean | Mandatory permission gate for synthetic financial sources |
| `funding_reconciled` | boolean | Mandatory synthetic checkout funding reconciliation status |
| `monthly_income_vnd` | number array | Synthetic monthly income sequence used for mean, standard deviation, CV and P25 |
| `existing_monthly_debt_vnd` | number | Synthetic existing monthly debt payment |
| `essential_monthly_expenses_vnd` | number | Synthetic monthly expense estimate used for residual income |
| `evidence.reconciliation_fields_consistent` | integer | Reconciliation fields that agree in the synthetic fixture |
| `evidence.reconciliation_fields_total` | integer | Total compared fields in the synthetic fixture |
| `evidence.verified_sources` | integer | Synthetic evidence sources marked verified |
| `evidence.available_sources` | integer | Synthetic evidence sources expected in the fixture |
| `evidence.age_days` | number | Demonstration age for recency decay; frozen per fixture for reproducibility |
| `evidence.sources[]` | object array | Source name, type, coverage months, synthetic verification, and permission provenance |
| `assessment.features` | object | Derived mean, population standard deviation, CV, P25, DTI, residual income and history coverage |
| `assessment.confidence` | object | CS score, four subscores, weights, weighted contributions, and traced input counts |
| `assessment.risk` | object or null | Uncalibrated demo PD, formula, slopes, intercept, linear terms and status |
| `assessment.affordability` | object or null | Residual income, capacity, installment buffer, PMT if available, and DTI assumption |
| `assessment.expected_loss` | object or null | Demo PD × LGD assumption × EAD assumption |
| `calculation_results` row | SQLite record | Latest reproducible assessment and route with computation timestamp; what-if runs are excluded |
| `routing.eligible_routes` | string array | Feasible review routes after hard validation and illustrative policy constraints |
| `routing.recommended_route` | string | Lowest estimated cost eligible review path; requires officer confirmation |
| `routing.estimated_route_costs_vnd` | object | Explicit illustrative route cost assumptions |
| `review_history[]` | object array | Append-only officer action, route, reason, actor, timestamp and calculation context |

## Route values

- `HOLD_FOR_HUMAN_HANDLING`
- `FAST_TRACK_CANDIDATE`
- `STANDARD_REVIEW`
- `ENHANCED_REVIEW`

`FAST_TRACK_CANDIDATE` is a review queue label. It never denotes approval or automatic loan creation.
