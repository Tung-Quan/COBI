# Slide-Ready Research Pitch (English)

### Slide 1 — Question
**Can frozen document-evidence models transfer beyond one synthetic data process?** We evaluate evidence-quality triage, not credit risk or loan approval.

### Slide 2 — Locked evaluation
Four frozen systems; unchanged V3 thresholds and 32-feature contract. E1 is a retrospective replay. E2 is a separately implemented event-ledger challenge: 1,920 cases, 960 customer groups, 7,744 documents, six scenarios. No retraining or threshold tuning.

### Slide 3 — The apparent V3 result
Critical recall was 88.0%–91.0%; case review workload was 70.8%–81.8%. Because the test had been inspected, these are descriptive results.

### Slide 4 — Independent synthetic challenge
Critical recall fell to 62.8%–86.6%. Average precision fell to 0.110–0.287. At the frozen threshold, logistic regression, XGBoost and Deep Sets missed all 80 critical B4 stale-as-current cases.

### Slide 5 — False-positive stress test
On B5 legitimate discrepancies, 95.5%–99.9% of legitimate documents were flagged. High critical recall alone does not establish a usable or safe review policy.

### Slide 6 — Cost is assumption-dependent
At 10,000 applications under illustrative medium costs, simulated totals were VND 1.216B–1.273B vs VND 1.443B for CS V2. These are scenario calculations using E1 rates, not observed bank costs or realized savings.

### Slide 7 — Conclusion and next evidence
The independent challenge exposed major generalization and false-positive failures. Keep the release research-only. Next: a governed, human-reviewed external benchmark, pre-registered evaluation, and independent replication. **Status: `EVIDENCE_AI_VALIDATION_BLOCKED`.**

**Footer for every results slide:** Synthetic programmatic gold; no human-reviewed bank truth. E1 is retrospective. Bootstrap intervals condition on frozen models and sampled synthetic groups. No routing or approval authority.
