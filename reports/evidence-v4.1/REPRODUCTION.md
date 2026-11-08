# Reproduction and Artifact Replay

## Scope

This package reconciles an existing frozen Generator C run. It does not retrain, recalibrate, alter rule conditions, or choose thresholds. Generator C labels are already open, so reproductions are post-unblinding and exploratory.

## Reconcile metrics

From project root using the existing COBI Python environment:

```powershell
python -m evidence_ai.v4_1_reconcile_c
```

The reconciliation verifies frozen prediction hashes, recalculates all observed model predictions, grouped intervals and paired descriptive contrasts, and checks prior aggregate metrics. Do not run the one-time evaluator `python -m evidence_ai.v4_1_evaluate_c` again; its guard records the existing label access. Do not run training, calibration or model selection to update this release.

## Verify frozen model replay

```powershell
python -m evidence_ai.v4_1_replay
```

The replay checks exact released artifact hashes and compares predictions on the locked development partition. It does not consume C labels.

## Rebuild documents and charts

```powershell
python -m evidence_ai.v4_1_finalize
```

This writes the scientific reports, CSV/SVG/PNG pitch charts and a read-only research release manifest from reconciled outputs. It does not fit or select a model. The final integrity manifest is written after verification commands; see `FINAL_MANIFEST.json`.

## Known blockers

- `xgboost==3.0.5` and compatible frozen XGBoost artifacts cannot be replayed offline; those model arms remain `NOT_EVALUATED`.
- D1.1 contains 100 missing critical labels among records flagged as critical stale by the temporal rule. Do not repair labels after viewing C and call the result confirmatory.
- HTTP TestClient may be blocked by the Windows sandbox asyncio socketpair restriction; report that as `BLOCKED` if it occurs. A direct route call is not an HTTP test.
- Real-document validation is unavailable. Keep `EVIDENCE_AI_VALIDATION_BLOCKED`.

Exact environment versions, test commands, exit codes, hashes and any blockers are recorded in `VERIFICATION_LOG.md`.
