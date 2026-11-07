# Three minute demo script

## 0:00–0:25 — Queue overview

Open the dashboard. Explain that all six cases are synthetic and the metrics are a local scenario snapshot. Point out the route distribution, scoreable count and held cases. Open the case inbox.

## 0:25–0:55 — DEMO-001 evidence

Select `DEMO-001`. Show the synthetic purchase summary, income records and source provenance. Open AI Assessment and call out the mean income of 12m VND and confidence score near 0.820938. Expand the confidence subscores and show that CS is an evidence quality index, not a probability.

## 0:55–1:25 — Transparent calculations

Review the demo PD near 0.039675. Read its warning: the score is not trained or calibrated and its parity with the missing prototype has not been verified. Show stressed payment capacity of 2,906,250 VND per month, the payment buffer, and illustrative expected loss near 119,024 VND with its LGD/EAD inputs.

## 1:25–1:50 — Routing

Open Decision Routing. Walk through the four mandatory gates, eligible route list and illustrative cost comparison. Emphasize that fast-track is only a review candidate and the lowest cost route cannot bypass an eligibility gate.

## 1:50–2:20 — Human review

Open Officer Review. Choose “Confirm review path,” enter a reason, and record the action. Show the timestamped event in the audit history. Explain that the API has no loan approval action.

## 2:20–2:45 — What-if simulator

Raise existing debt or lower evidence quality, then run the scenario. Point out how capacity, CS, demo PD or route eligibility changes, and that the calculation includes an input trace and is not saved to the case. Toggle consent off and rerun to show scoring stops.

## 2:45–3:00 — Monitoring and export

Open Monitoring & export. Show the per-case evaluation log and the explicitly hypothetical baseline comparison. Download the JSON export with calculations and audit history.
