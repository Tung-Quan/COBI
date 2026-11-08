# Experimental Evidence — Semantic-Aware Financial Validation

## From fixed scoring to context-aware evidence checks

Frozen models evaluated on independent synthetic Generator B missed all 80 B4 stale-as-current critical records in the learned branches and flagged 1,145–1,198 of 1,199 legitimate B5 records. This motivated explicit semantic comparability and time-validity checks.

## Generator C — measured frozen-output results

After prediction freeze and subsequent label opening, the Semantic Hybrid recorded **520/520 critical detections (100%)**, **0/2,927 C1/C3/C5 legitimate false alerts**, **400/6,271 overall legitimate false alerts (6.38%)**, **520/1,680 cases flagged (31.0%)**, AP **0.5652**, Brier **0.0339**, and Log Loss **0.0939**. C4 stale-as-current recall was 120/120. These are synthetic observed results with grouped uncertainty; they do not imply zero population risk.

## Scientific qualification

The labels are open, so this is post-unblinding exploratory analysis. A development audit found 100 missing critical stale labels across training, validation, calibration and locked-test partitions. The full Logistic model and no-temporal ablation both had 0% C4 recall; the Hybrid combines rules and Logistic Regression. Therefore temporal-feature causality is not established. Comparability ablation results also combine separate frozen thresholds and a different model family from Hybrid.

Frozen XGBoost branches remain **NOT_EVALUATED** because the exact dependency was unavailable offline. The full baseline comparison is incomplete. All results are synthetic; real financial-document validation, bank performance, regulatory readiness and measured operational savings remain unvalidated.

**Status:** `EVIDENCE_AI_VALIDATION_BLOCKED`.
