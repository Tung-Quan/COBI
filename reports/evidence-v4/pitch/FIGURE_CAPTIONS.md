# Figure Captions and Method Footnotes

1. **Generator shift performance** (`figures/generator_shift_performance.png`). Frozen V3 thresholds applied to V3 test A and independent synthetic generator B; critical recall, average precision, and case-level workload. Customer-cluster bootstrap intervals are conditional on fixed systems and synthetic groups. A was previously inspected; B uses programmatic gold.
2. **Scenario failure matrix** (`figures/scenario_failure_matrix.png`). Scenario-specific critical recall and case review workload for B1–B6. Each scenario contains 320 synthetic cases from 160 customer groups. These designed scenarios are not estimates of real-world prevalence.
3. **Generalization gap** (`figures/generalization_gap.png`). Descriptive A−B gaps for AP and critical recall, and B−A log-loss difference. A/B prevalence differs; AP is prevalence-sensitive. Independent customer-group bootstrap intervals are not population guarantees.
4. **Cost sensitivity** (`figures/business_cost_sensitivity.png`). Simulated difference versus CS V2 at 10,000 applications over the assumed review and missed-document costs. Positive values denote lower simulated cost. All monetary inputs are illustrative assumptions; no measured saving is shown.
5. **Break-even frontier** (`figures/business_break_even.png`). Analytic break-even missed-document cost under fixed E1 synthetic rates and assumed review costs. The frontier is a conditional sensitivity illustration, not a bank business case.

**Required slide footnote:** Synthetic datasets and programmatic labels only; no human-reviewed bank truth. E1 is retrospective. E3 uses assumed costs and E1 rates. No model training or threshold changes in V4. Routing and approval authority are false.
