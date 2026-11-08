# Formula changelog · V1 → V2

Policy `cobi-checkout-policy-v2.0`, synthetic score `synthetic-logistic-v2.0`, new fixture `demo-001-v2.0`. Historical code, original seeds and V1 calculation tests remain in `backend/app/calculations_v1.py`, `backend/data/seed_applications.json` and `backend/tests/test_calculations_v1.py`.

| Step | V1 executable baseline | V2 policy and DEMO-001 |
|---|---|---|
| P1 | Truthiness of four seed flags | Strict consent, simulated identity, source permission and funding. Require principal ≤ purchase, and reconciliation within 1 VND when own funds are stated. For the fresh fixture, 6m = 5m + 1m VND. Explicit material failures and invalid or post-decision dates stop scoring. |
| P2 | Synthetic source list and counts | Distinct extraction confidence, synthetic source verification, material failure flag and feature-event/snapshot timestamps. Unreported dates are marked unknown. |
| P3 | Lower-order-statistic P25 = 11m VND | Linear interpolation at `0.25 × (n−1)` (Hyndman–Fan type 7) gives 11.25m VND. Mean = 12m VND, population SD ≈ 1.477m VND and DTI ≈ 10.78125%. |
| P4 | CS = 0.820938 with 11/12 history coverage | Same convex weights and inputs for this fixture. Coverage is `min(months/12,1)`. The original slide’s eight months would yield 8/12 coverage. Reconciliation/source gaps are separate. Missing denominators contribute zero. CS is an unvalidated quality index. |
| P5 | DTI capacity 2,906,250 VND, stated 2.4m VND and V1 PMT 2.4m VND | `A_DTI=max(0,0.35×I−D)` = 2,906,250. `A_residual=max(0,(P25−E−D)×(1−0.25))` = 4,842,187.50. Usable capacity is the minimum. Contract PMT at 0% over four months is 1,250,000. Headroom 1,656,250. Use nominal annual rate / 12 and standard amortization when rate > 0. Excludes fees and insurance. A material stated/PMT mismatch blocks fast-track. A manual what-if payment is explicitly tagged. |
| P6 | Anchored intercept forced 0.039675, with `1−CS` as a term | Fixed illustrative score `sigmoid(−3.5+3×DTI+1.5×CV)` ≈ 0.047792. The intercept is an illustrative engineering choice. Actual checkout PD is null. Public benchmark probabilities stay in Research Lab. |
| P7 | Synthetic score × 0.45 × 6,666,600 = 119,023.81 VND | `SCENARIO_EL_USING_DEMO_SCORE` ≈ 107,532 VND using original principal 5m VND as scenario EAD. Report 3×3 sensitivity over LGD 25/45/65% and principal fractions 25/50/100%. Actual loss is `EL_NOT_ESTIMABLE`. |
| P8 | Fast-track required demo score ≤ 10%. Score > 25% forced enhanced | Filter on mandatory gates, CS, affordability and payment reconciliation. CS < 0.50 forces enhanced; fast-track requires CS ≥ 0.75. Choose least assumed process cost with a stable tie-break. The synthetic score and research predictions have no route input. The fixture remains fast-track at 42,000 VND. |
| P9 | Officer reason, action and timestamp | Append input digest, fixture, model, policy version and risk source. Consent withdrawal is audited and sticky. A route is an officer work item. |
| P10 | Fixed baseline could assign standard to a case requiring enhanced | Compare the fixed order standard, enhanced, hold within feasible routes against minimum eligible cost. Report `SIMULATED_ROUTE_COMPARISON`. |

The V2 fixture adopts slide 8's funding amounts and the protocol's explicit zero-rate term. It retains the V1 income history and evidence counts as versioned engineering inputs. Existing SQLite application records keep their financial inputs and are assessed with V2 policy on the next read. Only a fresh database gets the new demo fixture.
