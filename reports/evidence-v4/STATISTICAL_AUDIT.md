# Statistical and Integrity Audit

**Disposition:** `EVIDENCE_AI_VALIDATION_BLOCKED`. This audit verifies artifact integrity and the registered analysis; it does not validate bank use.

## Baseline and protocol

- Protected V2/V3 manifest: `3ef9c5d33eb33e0879ccb628213dbd5d27300c52d72166781335221751599585`.
- Protected files checked: 109; mismatches: 0.
- Original registered protocol SHA-256: `f1eb2df747451e18a511d18c9679eb6685d2640056d3eb9054566468789d9a65`.
- Pre-confirmatory generator amendment SHA-256: `f6651efee06938c6203cfc44e0ef8009ba438838fa0dd4034ce9e2181ecada69`.
- The initial generator pilot remains archived as invalidated because observed text disclosed event meaning. Its outputs are not used in confirmatory results.

## Split integrity and replay

| V3 partition | Customer groups |
|---|---:|
| train | 352 |
| validation | 96 |
| calibration | 96 |
| test | 96 |

No customer group overlaps across V3 partitions. The V3 locked test replay resolved 192 cases and reproduced frozen report metrics for all four models. Thresholds, calibration, and model weights remain frozen.

## Generator B and feature contract

- Cases / customer groups / documents: 1920 / 960 / 7744.
- Schema compatibility: 7744 compatible; 0 incompatible.
- Frozen features: 32; customer/case/document identifiers, scenario labels, and generator-event fields are excluded.
- Observed documents, canonical facts and labels are separate files with SHA-256 values in `generator_b_manifest.json`.
- Labels are programmatic synthetic gold; no human-reviewed bank truth is present.

## Statistical analysis

The registered bootstrap used 300 customer-group resamples with seed 20261109. E1 model comparisons are paired. E2 is stratified by scenario. Generalization gaps independently resample the two synthetic datasets. Intervals are conditional on frozen systems and the generated samples; 300 draws have finite Monte Carlo quantile precision and do not guarantee future performance.

Metric denominators are explicit in E1/E2 JSON and prediction-level CSVs. Critical recall is document-level. Review workload is case-level (at least one flagged evidence document). AP is prevalence-sensitive; do not compare it without base-rate context.

## E3 unit and arithmetic audit

E3 has 84 rows. It charges review costs by flagged case and missed-error costs by false-negative critical document. Costs, volumes, inference charges, and fixed costs are assumptions from `config/cost_scenarios.yaml`; the result is not a bank quote or measured saving.

## Training disclosure

V4 performed no training. There are no V4 epochs, gradients, optimization traces, or V4 training losses to report. The compared learned model weights are frozen V3 artifacts and protected by the baseline manifest.
