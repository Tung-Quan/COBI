# COBI V2 scientific evidence for AI4Biz 2026

**Presentation claim.** COBI demonstrates a synthetic, human-reviewed checkout workflow and a reproducible public credit-risk benchmark. The repository supports technical feasibility. Evidence on checkout default and realized bank impact remains unavailable.

| Question | Verified finding |
|---|---|
| What trained? | A constant baseline, three logistic regressions, four boosted-tree configurations and three PyTorch MLPs on UCI 350. The winning checkpoint is XGBoost depth 2, rate 0.10, validation log loss 0.432396. |
| Which model runs? | Early stopping observed 230 trees. The exported model and API use exactly 210. Raw and calibrated predictions matched saved outputs on all 4,500 test rows through the local model, and on 100 test rows through the API. Maximum observed difference was 0. |
| What did the locked test show? | ROC-AUC 0.785289, average precision 0.573823, Brier 0.132663 and log loss 0.424694 after sigmoid calibration. All published intervals reproduced from frozen arrays. |
| Did calibration help? | Log loss rose by 0.00043148 (paired 95% CI 0.00002409 to 0.00083681). The no-train-vector subset still shows higher point loss, with an interval spanning zero. The chosen release remains unchanged. |
| What limits validity? | 817 excess identical vectors overall. 127/4,500 test records share a train vector. The population is Taiwan credit-card customers with 2005 histories. No application chronology, customer grouping or bank checkout outcomes are available. |
| What can judges see? | The fresh DEMO-001 uses VND 5m principal and VND 1.25m monthly payment. The workbench logs reasons, version IDs and input digest, requires human confirmation and rejects benchmark scoring on checkout inputs. |
| What impact was measured? | Decision time, cost, conversion, credit losses and officer workload are all `NOT_MEASURED`. The HLBVN case figures and pilot targets come from the supplied deck. |

The original `AI4Biz_Adudu_2026.pdf` was available and read. Its ten-slide narrative is retained. Page 11 is the concept poster. The slide 7 PD thresholds and slide 8 illustrative payment and evidence values describe the older concept. Use the V2 policy and screenshot in the current slides. PDF SHA-256 `22c59d9b9b27eda23da78202f50fdff947e5d4f6b58d56cbd84526da22e41c41`. [Original PDF](<C:/Users/tungq/Downloads/AI4Biz_Adudu_2026.pdf>).

## Navigation

- [Dataset and preprocessing](02_DATASET_AND_PREPROCESSING.md) · [Training and selection](03_TRAINING_AND_MODEL_SELECTION.md) · [Test evaluation](04_TEST_EVALUATION.md)
- [Calibration](05_CALIBRATION_ANALYSIS.md) · [Duplicate and validity audit](06_DUPLICATE_AND_VALIDITY_AUDIT.md) · [Explainability](07_EXPLAINABILITY.md)
- [DEMO-001 mathematical trace](08_MVP_MATHEMATICAL_TRACE.md) · [Business impact and pilot](09_BUSINESS_IMPACT_AND_LIMITATIONS.md) · [Literature](10_LITERATURE_REVIEW.md)
- [Slide-ready English copy](11_SLIDE_READY_CONTENT.md) · [Vietnamese scripts and judge Q&A](12_SPEAKER_SCRIPT_AND_QA.md) · [Slide evidence matrix](13_SLIDE_EVIDENCE_MATRIX.csv)

## Verification and reproducibility

No candidate was retrained. The audit verifies source hashes, checkpoint hashes, scaler moments, regenerated split membership, 11 validation predictions, archived test prediction arrays, all original intervals, 210-tree inference and API rejection of incompatible inputs. Bootstrap replays use the already frozen outputs. New paired comparisons and subset sensitivity analyses are descriptive and leave the original test and selection artifacts untouched. Raw rows and test predictions stay in the repository’s local data locations. [Machine-readable audit](audit_summary.json) · [Execution log](audit.log) · [Original result](../final/RESULTS.md).

Run from the repository root with the existing backend/ML environment and original local input files.

```powershell
backend/.venv/Scripts/python.exe -m reports.presentation_evidence_v2.verify_evidence
```

The verification run passed 36 automated tests, the Chrome workbench/research E2E, and the frontend build. Screenshots came from a disposable synthetic database. The existing Docker package-install stall was outside this evidence audit. [Tests](test_verification.log) · [Browser](browser_verification.log) · [Build](frontend_verification.log) · [Screenshots](screenshot.log).
