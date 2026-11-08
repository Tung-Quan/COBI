# Recovery Audit — COBI V4.1

**Project root:** `C:\disk D\COBI`. Root exists and is accessible. Existing uncommitted work was preserved; no reset, clean, checkout, or destructive command was used.

## Workspace state

The Git worktree was already dirty before this continuation, including changes across backend, frontend, docs, data and reports. These changes were retained. V4.1 research source and generated artifacts remain under `evidence_ai/` and `reports/evidence-v4.1/`.

## Protected artifacts

- The immutable V2/V3 baseline manifest contains 109 artifacts; final check: **109/109**. Manifest digest: `3ef9c5d33eb33e0879ccb628213dbd5d27300c52d72166781335221751599585`.
- V4 final release manifest lists 96 artifacts; final check: **95/96**. Manifest digest: `6ae215ce991df13546201fdb0fc61b5a385aef68fdbf04d682fac62727f7f688`. A discrepancy was present at the start of this continuation; it was preserved and not restored or overwritten:
- `frontend/src/EvidenceResearch.tsx`: expected `b3f7b74ec8ab8d1c773c970f5f31d3f2181c1f539fb968d37ab0fb4d7eff0947`, current `54da9de3afae412a20a58e47578fd9ca89276f0f85c87c72bf02d9f21dd18db9`.
- V4 B4/B5/B6 counts were recomputed against 7,744 prediction rows and agree with the pre-change audit; no protected V2-V4 artifact was rewritten.

## Generator C release record

- Generator C groups/cases/documents: 840/1680/6791.
- Prediction file SHA-256: `03d1a2a6aa3d52eae483cca2d538e8cf71777eea17aa32215160bc5be3dc7523`; prediction manifest records the same digest before label access.
- Frozen model manifest SHA-256: `9e960f45b0b4607f243de7429cd329e8317dea0a2020cf0ebe859e4641a78c1a`.
- Semantic Hybrid threshold: `0.500031490427`; no post-C changes.
- Label-access manifest states labels were opened after frozen predictions. This evaluation is therefore post-unblinding, not a fresh blind test.
- Semantic Hybrid aggregate recomputation matches the prior report: `True`.

## Baseline availability

CS_V2, frozen V4 Logistic and Deep Sets and semantic non-XGBoost arms have output artifacts and are included in delayed frozen-output evaluation. XGBoost `xgboost==3.0.5` was absent from the active Python, known local project environments checked, and pip's local wheel cache; no compatible local wheel was found. Offline package installation was not attempted. Both XGBoost arms remain `NOT_EVALUATED`; no substitute was used.

## Post-evaluation data-quality finding

The D1.1 audit identified 100 stale-as-current records missing a critical gold label across development partitions (train 60; validation 15; calibration 15; locked test 10). Generator C labels, predictions, thresholds and source artifacts have not been changed. This finding makes temporal feature attribution exploratory and weakens confirmatory claims.

## Artifact disposition

No V2, V3, or V4 baseline artifact was replaced. A stale unverified XGBoost joblib was isolated under `archive/unavailable-artifacts/` and was not used. Current detailed reconciliation is in `GENERATOR_C_RESULTS.md`; final checksums and command results are in `FINAL_MANIFEST.json` and `VERIFICATION_LOG.md`.
