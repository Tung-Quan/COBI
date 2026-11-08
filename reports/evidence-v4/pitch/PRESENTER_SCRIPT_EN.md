# Presenter Script (English, ~4 minutes)

**Slide 1.** Our research question is whether document evidence-quality models that perform well on one synthetic process remain useful when the process changes. This is not a model of credit default or loan approval.

**Slide 2.** We froze four systems, their input features, calibration, and operating thresholds. E1 replays a V3 synthetic test that had already been inspected, so it is retrospective. E2 uses a separately implemented event-ledger generator with 1,920 cases, 960 customer groups, and 7,744 compatible documents across six scenarios. We did not retrain or tune on the challenge data.

**Slide 3.** On E1, critical recall ranges from 88 to 91 percent. Review workload ranges from 71 to 82 percent of cases. These numbers describe that one known synthetic dataset; they are not a bank performance estimate.

**Slide 4.** On E2, critical recall falls to roughly 63 to 87 percent, and average precision is much lower. The clearest failure is evidence freshness: three learned models miss all 80 critical stale-as-current cases at the frozen operating point. This is a warning that the apparent V3 performance does not transfer consistently.

**Slide 5.** We also tested legitimate discrepancies. Between 95 and 100 percent of legitimate documents were flagged by the four systems. That is a substantial false-positive problem and would make a simple “high recall” story incomplete.

**Slide 6.** We built an explicit cost sensitivity model. Under one illustrative scenario at 10,000 applications, learned models appear less costly than the rules baseline. However, those numbers use assumed costs and E1 event rates; they are not bank quotations, observed savings, or evidence of deployability. The E2 failures make them especially unsuitable as a business case.

**Slide 7.** Our conclusion is a negative but useful research result: one synthetic test is not enough. The next step is a privacy-governed benchmark with human-reviewed labels and a pre-registered external evaluation. For now, the model remains research-only. The bank-validation status is `EVIDENCE_AI_VALIDATION_BLOCKED`, and the interface has no routing or approval authority.
