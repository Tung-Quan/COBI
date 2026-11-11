# COBI V4.2 Phase 1 — Repository Baseline Audit

**Audit date:** 2026-11-11 (Asia/Saigon)  
**Checkout:** `main`, HEAD `7f5eff1e46a8f0c03a36a11d6892231bf4927182`  
**Scope:** read-only inventory and source-backed reconciliation; no Generator C scoring or training.

## Executive disposition

The repository contains the frozen V4.1 release files and the actual Generator C prediction CSV. Its SHA-256 verifies as `03d1a2a6aa3d52eae483cca2d538e8cf71777eea17aa32215160bc5be3dc7523`. V4.1 data and metrics are present and internally documented. This audit does not recompute or re-score C because its labels are already open and the Phase 1 boundary forbids a fresh C evaluation.

At the start of this task, before any V4.2 files were created, `git status --short` contained **49 entries: 42 modified tracked paths and 7 untracked paths**. Existing work was retained. New artifacts from this task are confined to `research/v4_2/`. See `RUN_LOG.md` for commands and outcomes.

## Environment inventory

| Item | Observed state |
|---|---|
| Branch / commit | `main` / `7f5eff1e46a8f0c03a36a11d6892231bf4927182` |
| Global Python | 3.13.13 |
| Backend virtual-environment Python | 3.13.13 |
| Global pytest / jsonschema | pytest 8.3.4 / jsonschema 4.25.1; used for V4.2 schema tests |
| Backend virtual environment | Present; `jsonschema` is not installed there |
| Node.js | 24.16.0 |
| Frontend dependencies | `frontend/node_modules` present; package scripts include `build` |
| Research entrypoints | `evidence_ai/v4_1_generator_dev.py`, `evidence_ai/v4_1_generator_c.py`, `evidence_ai/v4_1_training.py`, `evidence_ai/v4_1_predict_c.py`, `evidence_ai/v4_1_reconcile_c.py`, `evidence_ai/v4_1_data_quality_audit.py` |
| Test locations | `evidence_ai/tests/`, `backend/tests/`, frontend Node tests |
| Research data | `reports/evidence-v4.1/data/development-d1.1/` and `reports/evidence-v4.1/data/generator-c-v1/` |

Python, Node and Git state are point-in-time observations, not claims about other machines or future runs.

## Claim-to-evidence ledger

`VERIFIED_IN_REPO` means the named primary artifact or source was located and its recorded value was checked in this checkout. It does not imply an independent rerun of the C evaluator. `REPORTED_ONLY` means the available basis is a checked-in report/log, not a new execution in this audit. `INCONSISTENT` marks a difference retained rather than reconciled by overwriting historical data.

| Claim | Status | Evidence and qualification |
|---|---|---|
| Generator `semantic-ledger-c-v1.0`, seed `2026110802`, protocol `cobi-evidence-v4.1-c1.0` | `VERIFIED_IN_REPO` | `reports/evidence-v4.1/data/generator-c-v1/dataset_manifest.json`, `C_PREDICTION_MANIFEST.json`, `experiment_protocol_c.json` |
| 840 groups, 1,680 cases, 6,791 documents | `VERIFIED_IN_REPO` | Dataset and prediction manifests agree on all three counts. |
| Frozen C prediction digest | `VERIFIED_IN_REPO` | `C_PREDICTIONS_FROZEN.csv` was hashed directly; digest matches both the prediction manifest and evaluation manifest. |
| Semantic Hybrid threshold `0.500031490427` | `VERIFIED_IN_REPO` | Exact stored value is `0.5000314904266389` in `GENERATOR_C_METRICS.json`; the prompt/report value is rounded. |
| Hybrid critical detections 520/520; legitimate false flags 400/6,271; C1/C3/C5 false flags 0/2,927; 520/1,680 cases flagged | `VERIFIED_IN_REPO` | Stored aggregate metrics in `GENERATOR_C_METRICS.json` agree with `GENERATOR_C_RESULTS.md` / `RESULTS.md`. These are released post-unblinding measurements; no fresh arithmetic evaluation was performed here. |
| Hybrid AP 0.5652, Brier 0.0339, log loss 0.0939 | `VERIFIED_IN_REPO` | Stored exact values are AP 0.5652173913, Brier 0.0338677990, log loss 0.0939039663. The probability target is the synthetic material-defect label. These are not bank calibration results. |
| Semantic XGBoost is `NOT_EVALUATED` | `VERIFIED_IN_REPO` | Model availability in `GENERATOR_C_METRICS.json` and V4.1 release reports; no artifact is substituted. |
| D1.1 stale-label omissions are 60/15/15/10 by split | `VERIFIED_IN_REPO` | Existing audit JSON/CSV and an independent read-only pass in `research/v4_2/tools/audit_d1_1.py`; see `LABEL_AUDIT_D1_1.md`. Proposed labels remain unapproved. |
| Protected V4 manifest check is 95/96 | `INCONSISTENT` | `reports/evidence-v4/final_manifest.json` records the mismatch at `frontend/src/EvidenceResearch.tsx`: expected `b3f7b74e…eff0947`, actual `54da9de3…d18db9`. The actual file hash matches the blob in HEAD, so this is not a change made by this task. No repair was attempted. |
| V4.1 package manifest counts | `RECOMPUTED` | Historical `VERIFICATION_LOG.md` claims 100/100; current separate `FINAL_MANIFEST.json` is 100/101 and current worktree `RELEASE_MANIFEST.json` is 14/14 source, 51/52 artifacts. This is distinct from V4's 95/96 and counts are not interchangeable. |
| Prior V4.1 checks: 37 backend tests, 7 semantic tests, 2 Evidence API tests, build, desktop/mobile E2E | `REPORTED_ONLY` | Historical results are logged in `reports/evidence-v4.1/VERIFICATION_LOG.md`. Phase 1 re-runs scoped relevant tests; see `RUN_LOG.md`. |
| Real-bank validity, measured savings, fraud attribution, regulatory readiness | `NOT_FOUND` | No independent bank evidence or adjudicated labels were found. Keep `EVIDENCE_AI_VALIDATION_BLOCKED`. |

## Frozen prediction and protected-manifest checks

| Artifact | Expected / recorded SHA-256 | Observed SHA-256 | Result |
|---|---|---|---|
| `reports/evidence-v4.1/data/generator-c-v1/C_PREDICTIONS_FROZEN.csv` | `03d1a2a6aa3d52eae483cca2d538e8cf71777eea17aa32215160bc5be3dc7523` | `03d1a2a6aa3d52eae483cca2d538e8cf71777eea17aa32215160bc5be3dc7523` | Match |
| `frontend/src/EvidenceResearch.tsx` (protected V4 manifest item) | `b3f7b74ec8ab8d1c773c970f5f31d3f2181c1f539fb968d37ab0fb4d7eff0947` | `54da9de3afae412a20a58e47578fd9ca89276f0f85c87c72bf02d9f21dd18db9` | Existing mismatch; same as HEAD; preserved |

The discrepancy is described by the checked-in V4.1 recovery audit as present before that continuation. This task independently confirms the current hash and its match to HEAD, but does not infer a more specific historical origin.

## Scope and safety boundary

- Research writes: `research/v4_2/` only.
- Protected: V4.1 predictions, labels, manifests, model checkpoints, thresholds and archived outputs; V2/UCI artifacts; product decision gates and CS_V2 logic; Evidence Research routing and approval controls.
- Prohibited in Phase 1: Generator D experiments, new model training, C re-scoring, C label changes, threshold selection from C, deployment or push.
- External validity: synthetic evidence is not banking validation. No credit approval/denial action is represented in the V4.2 research schemas.

## Audit limitations

This audit verifies that source artifacts and prior results exist and that named hashes/counts are consistent. It is not a complete reproduction of V4.1, does not independently review prior literature full texts, and cannot supply missing human adjudication or institutional policy. All Phase 2 blockers are listed in `RESEARCH_READINESS_GATE.md`.
