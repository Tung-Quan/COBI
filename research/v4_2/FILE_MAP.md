# COBI V4.2 Phase 1 — File and Evidence Lineage Map

This map records the inspected V4.1 source-to-artifact path and separates historical/product files from the V4.2 research write area. It is a compact lineage description, not a claim that every stage was re-executed during this audit.

## Data and model lineage

| Stage | Source / artifact | Role and evidence |
|---|---|---|
| D1.1 generator | `evidence_ai/v4_1_generator_dev.py` | Creates development synthetic cases and programmatic gold; D4 sets `critical_idx` only for the altered second record, then derives labels from that index. |
| D1.1 data and split | `reports/evidence-v4.1/data/development-d1.1/{observed.json,gold_labels.json,canonical_truth.json,split_*.json,dataset_manifest.json}` | 1,200 cases / 600 economic groups / 3,600 documents; four group-preserving splits. Hashes are captured in the immutable manifest and the new audit summary. |
| Semantic interpretation | `evidence_ai/semantic_evidence.py` | Three-state pair comparability plus temporal validity. `time_validity()` returns stale-as-current for a disjoint requested/effective period when asserted current; it marks the record critical at age ≥180 days. |
| Existing D1.1 audit | `evidence_ai/v4_1_data_quality_audit.py` | Produces the historical V4.1 audit CSV/JSON. Its output is corroborated, not overwritten. |
| V4.2 audit-only proposal | `research/v4_2/tools/audit_d1_1.py` | Reads D1.1 source artifacts, records input hashes, emits proposed rows with evidence pointers and `PENDING_ADJUDICATION`; writes only under `research/v4_2/`. |
| C generator | `evidence_ai/v4_1_generator_c.py` | Produces the seven-scenario synthetic challenge. C's registered source pair and rules are not independent of all development constructs. |
| C observed/gold inputs | `reports/evidence-v4.1/data/generator-c-v1/{observed.json,gold_labels.json,canonical_truth.json,dataset_manifest.json}` | 840 groups, 1,680 cases, 6,791 documents. Gold is already open; all C outcomes remain `POST_UNBLINDING_EXPLORATORY`. |
| Frozen C predictions | `reports/evidence-v4.1/data/generator-c-v1/C_PREDICTIONS_FROZEN.csv` | 67,910 rows, SHA-256 verified in `REPO_BASELINE_AUDIT.md`. Do not edit or rescore in Phase 1. |
| Prediction and evaluation manifests | `reports/evidence-v4.1/data/generator-c-v1/{C_PREDICTION_MANIFEST.json,C_EVALUATION_MANIFEST.json}` | Bind the C generator, observed data, frozen model release, predictions, threshold/status, and evaluation artifacts. |
| Frozen models / thresholds | `reports/evidence-v4.1/models/frozen-v1/` and `evidence_ai/v4_1_training.py` | Training/release provenance and calibration threshold selection. Historical artifacts stay protected; no V4.2 model is fitted in Phase 1. |
| C metrics and reports | `reports/evidence-v4.1/{GENERATOR_C_METRICS.json,GENERATOR_C_RESULTS.md,RESULTS.md,STATISTICAL_AUDIT.md}` | Released summaries of document, case, scenario, calibration, and uncertainty measurements; not independent real-world evidence. |
| C reconciliation / replay | `evidence_ai/v4_1_reconcile_c.py`, `evidence_ai/v4_1_replay.py` | Historical tools. A C reconciliation re-reads open labels and is not run as part of this Phase 1 audit. |
| Backend research API | `backend/app/evidence_research_v41.py` | Read-only V4.1 research endpoints; reports blocked validation and no routing/approval authority. |
| Research UI | `frontend/src/EvidenceResearch.tsx` | Read-only research presentation. Its hash is the one existing V4-manifest mismatch; this task leaves it untouched. |

## Simplified dependency graph

```text
synthetic D1.1 generator -> observed records + programmatic labels + group splits
                         -> semantic_evidence rules -> frozen development models/rules
synthetic Generator C -> observed records + opened gold -> frozen C predictions -> released metrics/reports
                                                                          -> read-only Evidence Research API/UI

V4.2 Phase 1:
D1.1 observed + gold + splits + semantic temporal rule -> audit-only proposals (PENDING_ADJUDICATION)
V4.2 JSON Schema contracts + illustrative fixtures -> scoped validation tests
```

## Write-path classification

| Class | Paths | Rule for this work |
|---|---|---|
| V4.2 research-writeable | `research/v4_2/**` | Only new output location for Phase 1 reports, schemas, fixtures, audit script/results, and tests. |
| Historical evidence protected | `reports/evidence-v4/**`, `reports/evidence-v4.1/**`, `reports/final/**`, `reports/evidence-v3/**`, `data/**`, `evidence_ai/**` | Read-only for this task; no edits to prior data, labels, metrics, model files, thresholds, or manifests. |
| Product protected | `backend/**`, `frontend/**`, `ml/**`, existing `docs/**` | Read-only for this task. No credit gate, checkout, affordability, route, approval, audit, or UI changes. |
| Pre-existing worktree changes | All paths shown by the initial `git status --short` | Preserve as found. Baseline count and commit are in `REPO_BASELINE_AUDIT.md`. |

## Relevant V4.1 artifacts and immutability checks

- C prediction SHA-256: `03d1a2a6aa3d52eae483cca2d538e8cf71777eea17aa32215160bc5be3dc7523`.
- D1.1 observed/gold/split SHA-256 values: `research/v4_2/D1_1_AUDIT_SUMMARY.json`.
- Protected V4 manifest result: 95/96, with the existing mismatch documented in `reports/evidence-v4/final_manifest.json`.
- No dataset regeneration or mutation is part of Phase 1. The audit script's generated CSV and JSON are new proposal artifacts, never replacements for historical labels.
