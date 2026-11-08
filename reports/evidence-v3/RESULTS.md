# COBI V3 evidence research results

**Bank status** · `EVIDENCE_AI_VALIDATION_BLOCKED`. Controlled corruptions verify training, evaluation and artifact interfaces. CORD measures a separate receipt field-tagging task. Workbench CS and P1–P10 policy retain their V2 execution path. The UCI 350 report and model hashes still match the published V2 release.

## Controlled synthetic defects

The frozen generator made 1,280 cases across 640 customer groups. Cases contain two to six documents, each with observed amounts, source metadata, confidence and text. Programmatic gold derives from known canonical values and independently generated document and extraction values. It does not derive from CS or predicted scores. The observed and label payloads have separate hashes. No bank data, empirical defect rates or human labels were used. [Protocol](../../docs/EVIDENCE_LEARNING_PROTOCOL_V3.md) · [Split manifest](synthetic/split_manifest.json)

| Partition | Cases | Customer groups | Role |
|---|---:|---:|---|
| Train | 704 | 352 | Fit preprocessing and candidates |
| Validation | 192 | 96 | Pick hyperparameters and epochs |
| Calibration | 192 | 96 | Fit sigmoid and lock 90% critical recall threshold |
| Test | 192 | 96 | Score frozen releases |

The locked test contains 753 documents, 293 material defects and 200 critical defects. The table reports calibrated predictions and the threshold from calibration. Workload is the fraction of cases with at least one document flagged. The operating point can differ on test.

| Model | Critical recall | FNR | AP | Brier | Log loss | Case workload |
|---|---:|---:|---:|---:|---:|---:|
| M0 · CS V2 | 0.880 | 0.120 | 0.4957 | 0.2308 | 0.6529 | 0.8177 |
| M1 · Logistic Regression | 0.910 | 0.090 | 0.9063 | 0.0840 | 0.2763 | 0.7917 |
| M2 · XGBoost | 0.905 | 0.095 | 0.9828 | 0.0350 | 0.1300 | 0.7083 |
| M3 · Deep Sets | 0.910 | 0.090 | 0.9269 | 0.0740 | 0.2356 | 0.7656 |

M3 recall 95% CI was [0.8651, 0.9479], M2 [0.8520, 0.9519]. Paired M3 minus M2 recall CI [−0.0377, 0.0521] spans zero. The AP difference was −0.0559 with paired CI [−0.0770, −0.0357]. Case workload was higher for M3 by 0.0573, with paired CI [0.0104, 0.1042]. These intervals use 300 shared customer-cluster bootstrap draws and condition on the fitted models and calibration thresholds. Within this generator, XGBoost had better probability metrics than Deep Sets. [Full metrics and CIs](synthetic/report.json) · [Comparison figure](figures/synthetic_comparison.svg)

## Optimization and calibration

Four Deep Sets hyperparameter combinations varied batch size, learning rate, hidden width and weight decay. Each used seeds 13, 29 and 43. The selected configuration used batch 32, hidden width 32, AdamW learning rate 0.001 and weight decay 0.0001. Its mean validation document log loss was 0.187597. The three seed-specific calibrated test AP values were 0.9205, 0.9311 and 0.9143, with recalls 0.895, 0.855 and 0.925. The primary row uses the mean raw prediction across seeds, then its separately fitted sigmoid and calibration threshold.

M0 uses `1−CS_V2` as a ranking score and fits a separate calibration map for probability metrics. For M3, sigmoid changes Brier from 0.07462 to 0.07402 and log loss from 0.24250 to 0.23562. The output includes reliability bins with counts, paired intervals, raw and calibrated metrics, and one validation example showing per-field probabilities and leave-one-document-mask sensitivity. The latter measures model sensitivity with other encoded inputs fixed. [Training history and gradients](synthetic/training_history.json) · [Frozen selection](synthetic/selection_lock.json) · [Calibration plot](figures/synthetic_calibration.svg) · [Registry manifest](synthetic/model/manifest.json)

The field extraction heads achieved test AP 0.712 for income, 0.618 for debt and 0.729 for purchase, with 97, 90 and 96 positive labels respectively. These field labels reflect differences between generated document contents and extracted values. Material defects are measured against the independent generated facts. The benchmark reports no bank authenticity accuracy.

## Ablations and distribution checks

| Deep Sets features | AP | Log loss | Critical recall | Case workload |
|---|---:|---:|---:|---:|
| Full | 0.9269 | 0.2356 | 0.910 | 0.7656 |
| Remove metadata | 0.9324 | 0.2254 | 0.895 | 0.7500 |
| Remove cross-source relationships | 0.9049 | 0.3004 | 0.900 | 0.7917 |
| Remove CS components | 0.9210 | 0.2388 | 0.930 | 0.7917 |
| Remove text hashing | 0.9483 | 0.2160 | 0.935 | 0.7448 |

The simple embeddings are 12-dimensional character-trigram hashes of observed text. Removing them improved the selected technical model's test log loss. Removing relationship features had the largest observed adverse loss change. These ablations were fixed before test access. They did not change selection. Test subgroups include seen versus held-out synthetic template tags and the earlier/later generated date bands. The held-out tag itself does not introduce a document layout shift. An additional frozen model challenge used 120 independently generated groups with revised formatting and lower observed OCR confidence. XGBoost AP was 0.978 and Deep Sets AP 0.891 on that challenge. It measures a specified synthetic perturbation. [Ablations](figures/synthetic_ablations.svg) · [Format challenge](synthetic-format-challenge/report.json)

## CORD v2 · public receipt extraction pilot

Downloaded all six pinned official parquet shards and verified the published 800/100/100 split totals. The data contain images and JSON with OCR words, quadrilaterals, hierarchy and field labels for Indonesian receipts. CORD is CC BY 4.0. The Microsoft LayoutLMv3 base and derivative adapter are CC BY-NC-SA 4.0 and restricted to noncommercial research here. DocILE supplies KILE and line-item recognition labels on business documents. Its owner access form requires noncommercial research use and prohibits redistribution, with a token required for download. No request or download was performed for DocILE. [CORD card](https://huggingface.co/datasets/naver-clova-ix/cord-v2) · [Model card](https://huggingface.co/microsoft/layoutlmv3-base) · [DocILE access terms](https://forms.gle/poJqGXrxoftWrUsc8)

The extraction pilot selected 128/40/60 examples inside the published splits using a fixed seed. The source's numeric image IDs repeat across splits, so the pre-fit audit moved to byte digests to verify disjoint image identity. The initial failed check preceded fitting and test access. LayoutLMv3 fine-tuned the last text-layout encoder block and token head for five epochs. The model received annotated OCR word boxes and text, without pixels, full OCR detection or unannotated background words. It decoded BIO spans and scored exact field category and word-span boundaries.

| Receipt test metric | Result |
|---|---:|
| Exact field micro F1 | **0.625745** |
| 95% receipt bootstrap CI | [0.565333, 0.682618] |
| Precision | 0.616921 |
| Recall | 0.634825 |
| Exact span TP / FP / FN | 525 / 326 / 302 |
| Words covered | 1,491 / 1,491 |

This is one seed and a small subset. The bootstrap conditions on the frozen adapter, sampled receipts and split. It does not quantify optimizer variation, unknown merchant group dependence or accuracy on bank documents. No end-to-end OCR, document authenticity, or independent bank error claim follows from it. [CORD provenance and hashes](cord-extraction/provenance.json) · [Full field results](cord-extraction/report.json) · [Checkpoint and license](cord-extraction/model_manifest.json) · [Replay and uncertainty](cord-extraction/replay_uncertainty.json)

## Reproduction and integration

From the repository root, use the existing Python environment with `backend/requirements.txt` and `evidence_ai/requirements-cord.txt`. Explicit replay verifies the released artifacts. A new fit writes to a new directory. Run training against an untouched cohort for a new selection decision.

```powershell
python -m evidence_ai.synthetic
python -m evidence_ai.replay
python -m evidence_ai.train --out data/processed/evidence-v3/reproduction-run
python -m evidence_ai.acquire_cord --research-only
python -m evidence_ai.cord --out data/processed/evidence-v3/cord-reproduction
python -m evidence_ai.cord_replay
python -m evidence_ai.figures
python -m scripts.validate_evidence_annotations --schema
```

The CORD adapter is retained locally at `reports/evidence-v3/cord-extraction/adapter.safetensors`. It is excluded from Git alongside downloaded data and the base checkpoint. To create it from a clean checkout, run the CORD training command into a fresh output directory. For a restricted annotation batch, the CLI validates a local JSONL and outputs counts only. See the [annotation schema](annotation.schema.json). The workflow requires independent reviewed labels and authorization before training on bank documents.

Run the existing API and frontend commands in the README. Open **Evidence AI Research** to see datasets, comparisons, calibration, examples and the CORD report. The Workbench **shadow only** panel returns null outputs for checkout cases, including null outputs after any failed mandatory gate. It cannot write decisions or replace CS.

Verification passed 41 automated tests, the TypeScript/Vite build, the desktop and mobile browser journey, and both model replays. Compose configuration validation passed. [API regression](verification.log) · [Frontend build](frontend.log) · [Browser E2E](e2e.log) · [Model replay](replay.log) · [Paper outline](PAPER_OUTLINE.md) · [Slide evidence](SLIDE_EVIDENCE.md)
