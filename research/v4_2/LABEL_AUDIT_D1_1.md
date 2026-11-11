# D1.1 Stale-as-Current Label Audit

**Disposition:** source-supported label-generation inconsistency; candidate changes are **not approved gold**.  
**Status:** `PENDING_ADJUDICATION` for all 100 candidate rows.  
**Scope:** D1.1 only. Generator C predictions, labels and metrics remain frozen and untouched.

## Finding

The archived D1.1 dataset contains 200 records for which the registered semantic rule returns `STALE_AS_CURRENT`. Of those, 100 have `critical_defect=0` in programmatic gold even though the rule marks them critical. The count independently reproduced from the raw `observed.json`, `gold_labels.json` and split files is:

| Split | Stale-as-current records | Candidate critical omissions |
|---|---:|---:|
| Train | 120 | 60 |
| Validation | 30 | 15 |
| Calibration | 30 | 15 |
| Locked test | 20 | 10 |
| **Total** | **200** | **100** |

The 100 proposals are the **first** stale record in each of 100 D4 stale cases. The second record is the deliberately altered item and is labeled critical by the generator. Both records have a non-overlapping effective period, are represented as current, and have ages above the synthetic 180-day critical rule. This is a specific generator-label construction defect, not an OCR/parsing failure.

## Source trace and root cause

1. `evidence_ai/v4_1_generator_dev.py:97-112` constructs D4. On the stale branch it creates two records using an old period and `asserted_current=True`; `critical_idx` is assigned only to the altered second record.
2. `evidence_ai/v4_1_generator_dev.py:135-141` derives `critical_defect` from `i == critical_idx`. The other stale-as-current record therefore receives a zero label.
3. `evidence_ai/semantic_evidence.py:143-157` compares evidence period to requested period, returns `STALE_AS_CURRENT` when the record asserts current despite a disjoint period, and marks it critical at age ≥180 days.
4. `reports/evidence-v4.1/data/development-d1.1/dataset_manifest.json` identifies the D1.1 dataset and provides raw-file hashes. The four `split_*.json` files assign the affected case groups.
5. The V4.1 audit output `D1.1_LABEL_SEMANTIC_AUDIT.csv/.json` records the same 200/100 finding and split distribution. The V4.2 audit independently recomputes the rule result without editing those outputs.

### Cause classification

| Candidate explanation | Evidence-based conclusion |
|---|---|
| Omitted/wrong generated annotation | **Supported.** Gold is programmatically generated from a single corruption index; the first record is omitted despite being stale-as-current under the registered rule. |
| Inconsistent semantic policy | **Supported.** Generator gold follows “which record was deliberately corrupted”; semantic temporal validation follows “which record asserts current for a disjoint period.” Those targets differ. |
| Extraction/parsing error | **Not supported by inspected evidence.** The input periods, current assertion and age are explicit structured fields. This does not rule out uninspected ingestion faults. |
| Legitimate ambiguity | **Possible at policy/real-world level.** A synthetic rule is not independent adjudication, and 180 days is not a bank-approved freshness policy. This uncertainty blocks acceptance of proposed labels. |
| Reporting error | **Not supported.** The raw-case recount, old audit artifact and V4.2 audit agree. |

## Intended label semantics for future adjudication

A `stale-as-current` label should depend on the **request's as-of period**, evidence intent, source/record validity, version lineage and a named, versioned policy. Age alone does not define invalidity. An old document can be valid evidence for a historical request. A candidate stale-as-current defect requires, at minimum, that the evidence is asserted for a current request while its supported valid/effective interval does not cover that request, and that the source/policy makes that mismatch material. No universal 180-day cut-off is adopted by this audit.

## Proposed versioned changes

`tools/audit_d1_1.py` writes `D1_1_PROPOSED_CHANGELOG.csv` and `D1_1_AUDIT_SUMMARY.json` under this directory. The CSV preserves old labels, records a candidate label and rationale code, captures requested/effective intervals and evidence pointers, and marks the 100 label changes `PENDING_ADJUDICATION`. Every proposed row has `approved_gold=NO`. These outputs are an audit ledger, not a corrected training set. No diff against or replacement of `gold_labels.json` is produced.

To promote any row later, require a named policy owner and independent reviewer, explicit review of source validity and intended use, retained raw ratings, adjudication rationale, and a new immutable dataset version with its own manifest and hashes. Keep the original D1.1 dataset intact.

## Scientific consequences

- Development training, validation, calibration and locked-test results involving temporal features are label-inconsistent.
- This defect does not change the frozen Generator C prediction file or its reported measurements.
- Generator C is already unblinded, and its synthetic labels/rules share temporal constructs. C remains `POST_UNBLINDING_EXPLORATORY`; do not repair labels, retrain, recalibrate, change thresholds, or describe a new score on C as confirmatory.
- Independent human adjudication is absent. V4.2 remains `EVIDENCE_AI_VALIDATION_BLOCKED` for real-world validity.
