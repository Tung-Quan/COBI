# Business evidence and future validation

The supplied HLBVN case describes **1.8–4.6 business days** to decision, **VND 380,000 per application**, repeated review and disconnected financial evidence. The deck compares the reported processing cost with a VND 1.6m small loan (23.75%). This ratio is arithmetic on case inputs. The project does not contain the bank’s transaction-level cost, timestamps or a current external benchmark. The intended owners are bank lending and risk teams, with officers as primary users and merchants as checkout partners. [Original presentation, pp. 2–4](<C:/Users/tungq/Downloads/AI4Biz_Adudu_2026.pdf>).

| Case pain | Implemented MVP mechanism | Evidence status |
|---|---|---|
| Fragmented financial evidence | Case record, data provenance fields, synthetic verification and reconciliation | Software behavior verified on fixtures |
| Repeated manual review | Explicit gates, evidence gaps and feasible review paths | Officer workflow demonstrated in browser |
| Poor visibility into affordability | Reproducible PMT, two capacity constraints and sensitivity grid | Deterministic trace verified |
| Friction at merchant checkout | A structured workbench can support a later checkout handoff | Integration and adoption unmeasured |
| Need for risk validation | Isolated public benchmark and schema contract | Internal UCI evidence only |

| Operational outcome | Status | Pilot measurement and denominator |
|---|---|---|
| Processing cost reduction | `NOT_MEASURED` | Fully loaded staff minutes × cost rate, rework, service fees and implementation costs, divided by eligible applications. Use the same scope in both arms. |
| Decision-time reduction | `NOT_MEASURED` | Business-time from complete submission to decision for all eligible cases. Report median, p90, open cases and SLA attainment. |
| Checkout conversion uplift | `NOT_MEASURED` | Completed purchases per assigned eligible checkout. Report absolute percentage-point lift and relative lift with denominators. |
| Credit-loss reduction | `NOT_MEASURED` | Realized net losses over a common mature horizon per unit of booked exposure. Track delinquency, approval selection, loss emergence and recovery. |
| Officer workload reduction | `NOT_MEASURED` | Active minutes per case, total queue minutes, reviews and escalations per 100 cases, with rework tracked separately. |

The original slide 9 lists **50%** cost reduction, **50%** time reduction, **20–30%** conversion uplift and **40–50%** later-phase automation. These are original targets. For the pitch, present them as hypotheses with clear denominators, or leave them in speaker notes. V2 has no automated approval. [Original presentation, p. 9](<C:/Users/tungq/Downloads/AI4Biz_Adudu_2026.pdf>) · [Scope and limitations](../../docs/LIMITATIONS.md).

## Pilot design

1. Agree on eligible product, geography, consent, data provenance, lawful access, operational ownership, outcome horizon and audit retention with the bank. Establish a baseline before intervention. Include a pilot rollback and escalation owner.
2. Run a blinded shadow review first. Freeze cutoff dates, feature availability and outcome maturation. Use customer-disjoint cohorts, monitor missingness and drift, and compare decisions against independent review. Identify which outcomes are unobservable after rejection and prespecify how they constrain inference.
3. With approval, randomize workbench access at an appropriate unit such as officer team or store to reduce spillover. Compare with usual review. Use intention-to-treat, report sample size and cluster-aware intervals, and require independent measurement of reviewer corrections, complaints, unfair disparities and decision quality. Keep lending authority with bank officers.
4. Evaluate cost, time and conversion once matured operational observations are available. Report loss only after the agreed repayment and recovery windows. Compare risk and fairness guardrails before expanding the pilot.

E5 is a scenario arithmetic check. Six synthetic cases under 18 cost/policy combinations produced a VND 68,000 aggregate assumed difference in nine settings and zero in nine. The implementation prices feasible review actions with configured constants. It provides no realized savings or pricing evidence. [Route sensitivity](../final/route-sensitivity.json) · [Pilot visual](figures/pilot_measurement.svg).
