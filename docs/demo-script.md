# Three-minute walkthrough · COBI V2

## 0:00–0:45 · Workbench

Open a fresh synthetic database and select DEMO-001. The purchase is VND 6m with VND 1m own funds and VND 5m principal. The four-month payment at 0% is VND 1.25m. Open AI Assessment, check the original income observations, evidence subscores and the two affordability constraints.

## 0:45–1:25 · Officer review

Show the scenario score and loss sensitivity. Actual checkout PD and expected loss are unavailable. Open Decision Routing to compare only eligible routes, then Officer Review to record an action with a reason. Inspect the audit trail. On a disposable case, withdrawing consent stops scoring.

## 1:25–2:00 · What-if

Change income or debt and rerun. Compare affordability and eligible routes with the original case. Check UCI compatibility and point out `PD_UNAVAILABLE_SCHEMA_MISMATCH`. The original case retains its inputs.

## 2:00–3:00 · Research Lab

Show the Taiwan credit-card population and next-month label, four locked cohorts and the validation comparison. Select an MLP trace to show its real epoch history. Compare raw and calibrated XGBoost results and reliability bins. The sigmoid raised test log loss slightly. Download the manifest and review its benchmark-only scope and component hashes.
