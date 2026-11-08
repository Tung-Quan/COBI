# Pitch Evidence Summary

## One-sentence finding

Four frozen models looked strong on one inspected synthetic test, but performance dropped on an independently generated challenge; several severe failures mean there is no basis for a deployment or bank-savings claim.

## What the study did

- Replayed four frozen systems at unchanged V3 thresholds.
- Tested on a second event-ledger generator: 1,920 cases, 960 groups, 7,744 documents, six scenarios.
- Preserved customer groups in 300-draw bootstrap intervals.
- Simulated costs under explicit assumptions, without calling them measured savings.
- Kept the workbench read-only; routing and approval authority are false.

## Evidence to show

- E1 critical recall: 0.880–0.910; case review workload: 0.708–0.818.
- E2 critical recall: 0.628–0.866; case workload: 0.546–0.652.
- B4: three learned models missed all 80 critical stale-as-current cases.
- B5 false-positive rate on legitimate documents: 95.5%–99.9%.
- E3 medium assumptions at 10,000 applications: illustrative totals VND 1.216B–1.273B, versus VND 1.443B baseline. This is not a bank quote or realized saving.

## Claim boundary

Say “synthetic stress test” and “research-only.” Do not say “validated for banks,” “safe,” “reduces real review workload,” or “saves VND X.” The release remains `EVIDENCE_AI_VALIDATION_BLOCKED`.

## Suggested visuals

- `figures/generator_shift_performance.png` — show the drop from A to B.
- `figures/scenario_failure_matrix.png` — show scenario-level recall and workload.
- `figures/business_cost_sensitivity.png` — show assumption sensitivity, with the “illustrative only” footnote.

All captions and limitations are in `FIGURE_CAPTIONS.md`.
