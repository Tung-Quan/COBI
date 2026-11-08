# COBI V4 Baseline Audit

**Audit date:** 2026-11-08  
**Scope:** local COBI repository and frozen COBI V3 Evidence AI artifacts  
**Status:** Phase 0 audit prepared; Generator B has not been evaluated.

## Repository state

The repository root is `C:/disk D/COBI`. The current `main` branch tracks `origin/main`, but the worktree contains numerous modified and untracked files, including changes to the V2 workbench, V3 evidence research, frontend, data, and reports. These existing changes are treated as user work and are preserved. No cleanup, reset, or overwrite of existing files is part of this V4 work.

## V2 and V3 boundaries

- The checkout Credit Review Workbench continues to use CS_V2 and its existing mandatory validation and human decision flow.
- Evidence AI outputs are research-only. The V3 model manifest says `policy_authorized: false` and `bank_validated: false`.
- The UCI 350 credit-default benchmark is separate from evidence-defect detection. V4 does not use its data, labels, model, or results as evidence-model inputs or outcomes.
- Bank validation remains `EVIDENCE_AI_VALIDATION_BLOCKED`.

## Frozen V3 evidence artifacts

The repository contains the V3 protocol, synthetic generator, feature encoder, training implementation, prediction replay, saved selection lock, model manifest, report, and frozen test split. The V3 report and split manifest state:

| Partition | Cases | Customer groups |
|---|---:|---:|
| Train | 704 | 352 |
| Validation | 192 | 96 |
| Calibration | 192 | 96 |
| Test | 192 | 96 |

The locked test has 753 documents, 293 material defects, and 200 critical defects. The existing model thresholds are loaded from `reports/evidence-v3/synthetic/selection_lock.json`; no V4 threshold is selected or recalibrated from test data.

| Model | Critical recall | AP | Brier | Log loss | Case workload |
|---|---:|---:|---:|---:|---:|
| CS_V2 | 0.880 | 0.495749 | 0.230755 | 0.652882 | 0.817708 |
| Logistic Regression | 0.910 | 0.906316 | 0.083968 | 0.276320 | 0.791667 |
| XGBoost | 0.905 | 0.982773 | 0.035013 | 0.130040 | 0.708333 |
| Deep Sets | 0.910 | 0.926875 | 0.074021 | 0.235615 | 0.765625 |

These are synthetic-only test results from the previously inspected V3 study. They are retrospective inputs to E1, not new confirmatory evidence. The V3 report's cluster-bootstrap intervals condition on the fitted models and calibration thresholds.

## Existing distribution challenge

`evidence_ai/shift.py` calls the V3 `generate` function and then modifies generated text formatting and OCR confidence. It evaluates the frozen models, but reusing Generator A means it is a formatting perturbation, not an independently implemented financial-document generator. V4 will retain it as the old V3 challenge and will not describe it as Generator B.

## Reproducibility and compatibility

- `evidence_ai/replay.py` reloads frozen V3 models, preprocessing, calibration, and thresholds for local replay.
- The frozen model feature contract has 32 input features, a six-document capacity, and three source categories (`statement`, `payroll`, `merchant`). IDs, timestamps, template fields, and labels are not model features.
- The V3 test export is not already stored as a row-level prediction table. E1 must reconstruct prediction-level rows by deterministic replay. If replay or alignment fails, E1 is marked blocked; aggregate report values must not be used to invent curves or paired intervals.
- Existing `reports/evidence-v3/verification.log` records 41 passing tests. V3's report records its frontend and replay verification. These are historical records; V4 verification will be run and logged separately.

## V2 release identity

The current V2/UCI model manifest and report are present at `reports/final/uci350-v2.0/`. Their current SHA-256 values are recorded in `ARTIFACT_MANIFEST.json`. V4 must leave those files and their registered model artifacts unchanged. The manifest/report file digests alone are not treated as proof that every nested model file is unchanged; the V4 manifest also records nested artifact digests.

## Phase 0 conclusion

The repository has enough frozen V3 artifacts to attempt deterministic E1 replay and to evaluate a strictly schema-compatible, independently generated B challenge. The experiment protocol is registered in `EXPERIMENT_PROTOCOL.md` and `experiment_protocol.json` before any Generator B evaluation. The V3 test remains retrospective, and no result from Generator B may be used to alter its scenarios, hypotheses, model set, thresholds, metrics, or cost assumptions.
